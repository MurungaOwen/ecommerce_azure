from django.conf import settings
from django.db import models

from products.models import Product


class Order(models.Model):
    STATUS_CART = 'cart'
    STATUS_SUBMITTED = 'submitted'
    STATUS_CHOICES = [
        (STATUS_CART, 'Cart'),
        (STATUS_SUBMITTED, 'Submitted'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CART)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    checked_out_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Order {self.pk} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('order', 'product')

    def __str__(self):
        return f"{self.product} x{self.quantity}"

# Create your models here.
