import uuid
from decimal import Decimal
import json
from urllib import error, request

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from analytics.services import calculate_order_totals, record_checkout_event
from products.models import Product

from .models import Order, Payment


def generate_reference(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


class PaystackError(Exception):
    pass


def _paystack_request(path, method='GET', payload=None):
    secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
    if not secret_key:
        raise PaystackError('Paystack secret key is not configured.')

    api_base = getattr(settings, 'PAYSTACK_API_BASE_URL', 'https://api.paystack.co').rstrip('/')
    url = f"{api_base}{path}"
    body = None if payload is None else json.dumps(payload).encode('utf-8')

    req = request.Request(
        url=url,
        data=body,
        method=method,
        headers={
            'Authorization': f'Bearer {secret_key}',
            'Content-Type': 'application/json',
        },
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8') if exc.fp else ''
        raise PaystackError(f'Paystack request failed ({exc.code}): {detail}') from exc
    except error.URLError as exc:
        raise PaystackError(f'Could not reach Paystack: {exc.reason}') from exc


def initiate_paystack_payment(order, user):
    total, item_count = calculate_order_totals(order)
    reference = generate_reference('paystack')
    user_email = getattr(user, 'email', '') or f"user-{user.pk}@example.com"
    payload = {
        'email': user_email,
        'amount': int((total * Decimal('100')).quantize(Decimal('1'))),
        'reference': reference,
        'currency': getattr(settings, 'PAYSTACK_CURRENCY', 'KES'),
        'callback_url': getattr(settings, 'PAYSTACK_CALLBACK_URL', None),
    }
    response = _paystack_request('/transaction/initialize', method='POST', payload=payload)
    if not response.get('status'):
        raise PaystackError(response.get('message', 'Paystack initialization failed.'))
    data = response.get('data') or {}

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
            'authorization_url': data.get('authorization_url'),
            'access_code': data.get('access_code'),
            'paystack_response': response,
        },
    )
    return payment


def verify_paystack_payment(reference):
    response = _paystack_request(f'/transaction/verify/{reference}')
    if not response.get('status'):
        raise PaystackError(response.get('message', 'Paystack verification failed.'))
    return response.get('data') or {}


def initiate_mpesa_stk_push(order, user, phone_number):
    total, item_count = calculate_order_totals(order)
    reference = generate_reference('mpesa')
    checkout_request_id = generate_reference('checkout')
    merchant_request_id = generate_reference('merchant')
    payment = Payment.objects.create(
        order=order,
        user=user,
        provider=Payment.PROVIDER_MPESA,
        reference=reference,
        amount=total,
        currency=getattr(settings, 'MPESA_CURRENCY', 'KES'),
        provider_reference=checkout_request_id,
        metadata={
            'items': item_count,
            'phone_number': phone_number,
            'checkout_request_id': checkout_request_id,
            'merchant_request_id': merchant_request_id,
            'callback_url': getattr(settings, 'MPESA_CALLBACK_URL', None),
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
