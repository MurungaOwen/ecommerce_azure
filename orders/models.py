from django.conf import settings
from django.db import models

from products.models import Product


class Order(models.Model):
    STATUS_CART = 'cart'
    STATUS_PAYMENT_PENDING = 'payment_pending'
    STATUS_SUBMITTED = 'submitted'
    STATUS_CHOICES = [
        (STATUS_CART, 'Cart'),
        (STATUS_PAYMENT_PENDING, 'Payment pending'),
        (STATUS_SUBMITTED, 'Submitted'),
    ]

    PAYMENT_PENDING = 'pending'
    PAYMENT_PAID = 'paid'
    PAYMENT_FAILED = 'failed'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Pending'),
        (PAYMENT_PAID, 'Paid'),
        (PAYMENT_FAILED, 'Failed'),
    ]

    FULFILLMENT_PENDING = 'pending'
    FULFILLMENT_PROCESSING = 'processing'
    FULFILLMENT_COMPLETED = 'completed'
    FULFILLMENT_CANCELLED = 'cancelled'
    FULFILLMENT_STATUS_CHOICES = [
        (FULFILLMENT_PENDING, 'Pending'),
        (FULFILLMENT_PROCESSING, 'Processing'),
        (FULFILLMENT_COMPLETED, 'Completed'),
        (FULFILLMENT_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CART)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING,
    )
    fulfillment_status = models.CharField(
        max_length=20,
        choices=FULFILLMENT_STATUS_CHOICES,
        default=FULFILLMENT_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    checked_out_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

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


class Payment(models.Model):
    PROVIDER_PAYSTACK = 'paystack'
    PROVIDER_MPESA = 'mpesa'
    PROVIDER_CHOICES = [
        (PROVIDER_PAYSTACK, 'Paystack'),
        (PROVIDER_MPESA, 'M-Pesa'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCEEDED, 'Succeeded'),
        (STATUS_FAILED, 'Failed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reference = models.CharField(max_length=120, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='KES')
    provider_reference = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.provider} {self.reference} ({self.status})"

# Create your models here.
