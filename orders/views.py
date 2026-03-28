from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product

from .models import Order, OrderItem
from .serializers import CartItemCreateSerializer, OrderSerializer


def get_or_create_cart(user):
    cart, _ = Order.objects.get_or_create(user=user, status=Order.STATUS_CART)
    return cart


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
        cart = Order.objects.filter(user=request.user, status=Order.STATUS_CART).first()
        if not cart:
            return Response({'detail': 'No active cart found.'}, status=status.HTTP_400_BAD_REQUEST)

        if not cart.items.exists():
            return Response({'detail': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        cart.status = Order.STATUS_SUBMITTED
        cart.checked_out_at = timezone.now()
        cart.save(update_fields=['status', 'checked_out_at', 'updated_at'])
        serializer = OrderSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Create your views here.
