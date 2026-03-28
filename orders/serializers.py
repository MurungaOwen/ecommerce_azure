from decimal import Decimal

from rest_framework import serializers

from products.models import Product
from products.serializers import ProductSerializer

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'quantity', 'unit_price', 'line_total')

    def get_line_total(self, obj):
        return obj.unit_price * obj.quantity


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'status', 'items', 'total', 'created_at', 'updated_at', 'checked_out_at')

    def get_total(self, obj):
        total = Decimal('0.00')
        for item in obj.items.all():
            total += item.unit_price * item.quantity
        return total


class CartItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=0)

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError('Product not found.')
        return value
