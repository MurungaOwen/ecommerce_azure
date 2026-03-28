import hashlib
import hmac
import json
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product

from .models import Order, OrderItem, Payment
from .services import (
    finalize_paid_order,
    initiate_mpesa_stk_push,
    initiate_paystack_payment,
    mark_payment_failed,
    verify_paystack_payment,
    PaystackError,
)
from .serializers import (
    CartItemCreateSerializer,
    MpesaCallbackSerializer,
    MpesaStkPushSerializer,
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

        try:
            payment = initiate_paystack_payment(order, request.user)
        except PaystackError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
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

        try:
            verification = verify_paystack_payment(payment.reference)
        except PaystackError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        gateway_status = verification.get('status')
        gateway_amount = verification.get('amount')
        gateway_currency = (verification.get('currency') or '').upper()

        expected_amount = int((payment.amount * Decimal('100')).quantize(Decimal('1')))
        expected_currency = payment.currency.upper()
        if gateway_amount != expected_amount or gateway_currency != expected_currency:
            payment.status = Payment.STATUS_FAILED
            payment.metadata.update({'verification': verification, 'verification_error': 'Amount/currency mismatch'})
            payment.save(update_fields=['status', 'metadata'])
            mark_payment_failed(payment.order)
            return Response({'detail': 'Payment verification mismatch.'}, status=status.HTTP_400_BAD_REQUEST)

        if gateway_status != 'success':
            payment.metadata.update({'verification': verification})
            if gateway_status in {'failed', 'abandoned', 'reversed'}:
                payment.status = Payment.STATUS_FAILED
                payment.save(update_fields=['status', 'metadata'])
                mark_payment_failed(payment.order)
                return Response({'detail': 'Payment failed.'}, status=status.HTTP_400_BAD_REQUEST)
            payment.status = Payment.STATUS_PENDING
            payment.save(update_fields=['status', 'metadata'])
            return Response({'detail': f'Payment status: {gateway_status}.'}, status=status.HTTP_202_ACCEPTED)

        if payment.status == Payment.STATUS_SUCCEEDED:
            order = payment.order
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)

        payment.metadata.update({'verification': verification})
        payment.status = Payment.STATUS_SUCCEEDED
        payment.provider_reference = str(verification.get('id') or payment.provider_reference)
        payment.save(update_fields=['status', 'metadata', 'provider_reference'])
        try:
            order = finalize_paid_order(payment.order)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaystackWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
        if not secret_key:
            return Response({'detail': 'Paystack secret key is not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        provided_signature = request.headers.get('x-paystack-signature', '')
        computed_signature = hmac.new(
            secret_key.encode('utf-8'),
            request.body,
            hashlib.sha512,
        ).hexdigest()
        if not hmac.compare_digest(provided_signature, computed_signature):
            return Response({'detail': 'Invalid signature.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return Response({'detail': 'Invalid payload.'}, status=status.HTTP_400_BAD_REQUEST)

        if payload.get('event') != 'charge.success':
            return Response({'detail': 'Ignored.'}, status=status.HTTP_200_OK)

        data = payload.get('data') or {}
        reference = data.get('reference')
        if not reference:
            return Response({'detail': 'Missing reference.'}, status=status.HTTP_400_BAD_REQUEST)

        payment = get_object_or_404(
            Payment,
            reference=reference,
            provider=Payment.PROVIDER_PAYSTACK,
        )

        gateway_amount = data.get('amount')
        gateway_currency = (data.get('currency') or '').upper()
        expected_amount = int((payment.amount * Decimal('100')).quantize(Decimal('1')))
        expected_currency = payment.currency.upper()
        if gateway_amount != expected_amount or gateway_currency != expected_currency:
            payment.status = Payment.STATUS_FAILED
            payment.metadata.update({'webhook': data, 'verification_error': 'Amount/currency mismatch'})
            payment.save(update_fields=['status', 'metadata'])
            mark_payment_failed(payment.order)
            return Response({'detail': 'Payment verification mismatch.'}, status=status.HTTP_400_BAD_REQUEST)

        payment.metadata.update({'webhook': data})
        payment.status = Payment.STATUS_SUCCEEDED
        payment.provider_reference = str(data.get('id') or payment.provider_reference)
        payment.save(update_fields=['status', 'metadata', 'provider_reference'])
        try:
            order = finalize_paid_order(payment.order)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MpesaStkPushView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MpesaStkPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = get_payment_order(request.user, serializer.validated_data['order_id'])
        payment = initiate_mpesa_stk_push(order, request.user, serializer.validated_data['phone_number'])
        return Response(
            {
                'order_id': order.id,
                'reference': payment.reference,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'checkout_request_id': payment.metadata.get('checkout_request_id'),
                'merchant_request_id': payment.metadata.get('merchant_request_id'),
            },
            status=status.HTTP_200_OK,
        )


class MpesaCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MpesaCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = get_object_or_404(
            Payment,
            provider=Payment.PROVIDER_MPESA,
            provider_reference=serializer.validated_data['checkout_request_id'],
        )
        result_code = serializer.validated_data['result_code']
        payment.metadata.update(
            {
                'result_code': result_code,
                'result_desc': serializer.validated_data.get('result_desc'),
            }
        )
        if result_code == 0:
            payment.status = Payment.STATUS_SUCCEEDED
            payment.save(update_fields=['status', 'metadata'])
            try:
                order = finalize_paid_order(payment.order)
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)

        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=['status', 'metadata'])
        mark_payment_failed(payment.order)
        return Response({'detail': 'Payment failed.'}, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.
