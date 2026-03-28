from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product

from .models import Order, OrderItem, Payment
from .services import (
    finalize_paid_order,
    initiate_paystack_payment,
    mark_payment_failed,
)
from .serializers import (
    CartItemCreateSerializer,
    OrderSerializer,
    PaystackInitializeSerializer,
    PaystackVerifySerializer,
)


def get_or_create_cart(user):
    cart, _ = Order.objects.get_or_create(user=user, status=Order.STATUS_CART)
    return cart


def get_payment_order(user, order_id):
    return get_object_or_404(
        Order,
        pk=order_id,
        user=user,
        status=Order.STATUS_PAYMENT_PENDING,
    )


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        serializer = OrderSerializer(cart)
        return Response(serializer.data)


class CartItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = get_object_or_404(Product, pk=serializer.validated_data['product_id'], is_active=True)
        quantity = serializer.validated_data['quantity']
        if quantity > product.stock:
            return Response(
                {'detail': 'Requested quantity exceeds available stock.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = get_or_create_cart(request.user)
        if quantity == 0:
            OrderItem.objects.filter(order=cart, product=product).delete()
            serializer = OrderSerializer(cart)
            return Response(serializer.data)

        item, created = OrderItem.objects.get_or_create(
            order=cart,
            product=product,
            defaults={'quantity': quantity, 'unit_price': product.price},
        )
        if not created:
            item.quantity = quantity
            item.unit_price = product.price
            item.save(update_fields=['quantity', 'unit_price'])
        serializer = OrderSerializer(cart)
        return Response(serializer.data)


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            cart = (
                Order.objects.select_for_update()
                .filter(user=request.user, status=Order.STATUS_CART)
                .first()
            )
            if not cart:
                return Response({'detail': 'No active cart found.'}, status=status.HTTP_400_BAD_REQUEST)

            items = list(cart.items.select_related('product'))
            if not items:
                return Response({'detail': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

            products = Product.objects.select_for_update().filter(
                id__in=[item.product_id for item in items]
            )
            product_map = {product.id: product for product in products}

            for item in items:
                product = product_map[item.product_id]
                if item.quantity > product.stock:
                    return Response(
                        {'detail': f'Insufficient stock for {product.name}.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            cart.status = Order.STATUS_PAYMENT_PENDING
            cart.payment_status = Order.PAYMENT_PENDING
            cart.save(update_fields=['status', 'payment_status'])

        serializer = OrderSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaystackInitializeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PaystackInitializeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = get_payment_order(request.user, serializer.validated_data['order_id'])

        payment = initiate_paystack_payment(order, request.user)
        return Response(
            {
                'order_id': order.id,
                'reference': payment.reference,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'authorization_url': payment.metadata.get('authorization_url'),
            },
            status=status.HTTP_200_OK,
        )


class PaystackVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PaystackVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = get_object_or_404(
            Payment,
            reference=serializer.validated_data['reference'],
            provider=Payment.PROVIDER_PAYSTACK,
            user=request.user,
        )

        verification_status = serializer.validated_data.get('status', 'success')
        if verification_status == 'failed':
            payment.status = Payment.STATUS_FAILED
            payment.save(update_fields=['status'])
            mark_payment_failed(payment.order)
            return Response({'detail': 'Payment failed.'}, status=status.HTTP_400_BAD_REQUEST)

        payment.status = Payment.STATUS_SUCCEEDED
        payment.save(update_fields=['status'])
        try:
            order = finalize_paid_order(payment.order)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Create your views here.
