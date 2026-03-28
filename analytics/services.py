from decimal import Decimal

from .models import CheckoutEvent


def calculate_order_totals(order):
    total = Decimal('0.00')
    item_count = 0
    for item in order.items.all():
        total += item.unit_price * item.quantity
        item_count += item.quantity
    return total, item_count


def record_checkout_event(order):
    total, item_count = calculate_order_totals(order)
    event, _ = CheckoutEvent.objects.update_or_create(
        order=order,
        defaults={
            'user': order.user,
            'total': total,
            'item_count': item_count,
        },
    )
    return event
