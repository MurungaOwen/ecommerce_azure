from django.conf import settings
from django.db import models

class CheckoutEvent(models.Model):
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='checkout_event',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='checkout_events',
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    item_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Checkout {self.order_id} ({self.total})"
