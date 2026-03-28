import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from analytics.services import calculate_order_totals, record_checkout_event
from products.models import Product

from .models import Order, Payment


def generate_reference(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


def initiate_paystack_payment(order, user):
    total, item_count = calculate_order_totals(order)
    reference = generate_reference('paystack')
    auth_base = getattr(settings, 'PAYSTACK_AUTH_BASE_URL', 'https://checkout.paystack.com')
    authorization_url = f"{auth_base.rstrip('/')}/{reference}"
    payment = Payment.objects.create(
        order=order,
        user=user,
        provider=Payment.PROVIDER_PAYSTACK,
        reference=reference,
        amount=total,
        currency=getattr(settings, 'PAYSTACK_CURRENCY', 'KES'),
        metadata={
            'items': item_count,
            'callback_url': getattr(settings, 'PAYSTACK_CALLBACK_URL', None),
            'authorization_url': authorization_url,
        },
    )
    return payment


def finalize_paid_order(order):
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.status == Order.STATUS_SUBMITTED:
            return locked_order

        items = list(locked_order.items.select_related('product'))
        products = Product.objects.select_for_update().filter(
            id__in=[item.product_id for item in items]
        )
        product_map = {product.id: product for product in products}

        for item in items:
            product = product_map[item.product_id]
            if item.quantity > product.stock:
                raise ValueError(f'Insufficient stock for {product.name}.')

        for item in items:
            product = product_map[item.product_id]
            product.stock -= item.quantity
            product.save(update_fields=['stock'])

        now = timezone.now()
        locked_order.status = Order.STATUS_SUBMITTED
        locked_order.payment_status = Order.PAYMENT_PAID
        locked_order.checked_out_at = now
        locked_order.paid_at = now
        locked_order.save(
            update_fields=['status', 'payment_status', 'checked_out_at', 'paid_at']
        )

    record_checkout_event(locked_order)
    return locked_order


def mark_payment_failed(order):
    order.payment_status = Order.PAYMENT_FAILED
    order.save(update_fields=['payment_status'])
