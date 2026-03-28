from decimal import Decimal
import hashlib
import hmac
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from analytics.models import CheckoutEvent
from products.models import Product
from .models import Order, Payment

User = get_user_model()


class CheckoutFlowTests(APITestCase):
    @patch('orders.views.verify_paystack_payment')
    @patch('orders.views.initiate_paystack_payment')
    def test_add_to_cart_and_checkout(self, mock_initiate_paystack_payment, mock_verify_paystack_payment):
        def mocked_init(order, user):
            return Payment.objects.create(
                order=order,
                user=user,
                provider=Payment.PROVIDER_PAYSTACK,
                reference='paystack_test_reference',
                amount='16.00',
                currency='KES',
                metadata={'authorization_url': 'https://checkout.paystack.com/test'},
            )

        mock_initiate_paystack_payment.side_effect = mocked_init
        mock_verify_paystack_payment.return_value = {
            'status': 'success',
            'amount': 1600,
            'currency': 'KES',
            'id': 123456,
            'reference': 'paystack_test_reference',
        }

        user = User.objects.create_user(username='buyer', password='strongpassword')
        product = Product.objects.create(
            name='Tea',
            description='Green tea',
            price='8.00',
            stock=5,
        )

        self.client.force_authenticate(user=user)

        add_response = self.client.post(
            reverse('cart-items'),
            {'product_id': product.id, 'quantity': 2},
            format='json',
        )
        self.assertEqual(add_response.status_code, 200)
        self.assertEqual(add_response.data['status'], 'cart')
        self.assertEqual(add_response.data['items'][0]['quantity'], 2)

        cart_response = self.client.get(reverse('cart'))
        self.assertEqual(cart_response.status_code, 200)
        self.assertEqual(cart_response.data['total'], Decimal('16.00'))

        checkout_response = self.client.post(reverse('checkout'), format='json')
        self.assertEqual(checkout_response.status_code, 200)
        self.assertEqual(checkout_response.data['status'], 'payment_pending')
        self.assertEqual(checkout_response.data['payment_status'], 'pending')

        paystack_init = self.client.post(
            reverse('paystack-init'),
            {'order_id': checkout_response.data['id']},
            format='json',
        )
        self.assertEqual(paystack_init.status_code, 200)
        paystack_verify = self.client.post(
            reverse('paystack-verify'),
            {'reference': paystack_init.data['reference']},
            format='json',
        )
        self.assertEqual(paystack_verify.status_code, 200)
        self.assertEqual(paystack_verify.data['status'], 'submitted')
        self.assertEqual(paystack_verify.data['payment_status'], 'paid')
        product.refresh_from_db()
        self.assertEqual(product.stock, 3)
        self.assertTrue(CheckoutEvent.objects.filter(order_id=checkout_response.data['id']).exists())

    def test_mpesa_stk_push_flow(self):
        user = User.objects.create_user(username='mpesa-buyer', password='strongpassword')
        product = Product.objects.create(
            name='Sugar',
            description='Raw sugar',
            price='5.00',
            stock=4,
        )
        self.client.force_authenticate(user=user)
        self.client.post(
            reverse('cart-items'),
            {'product_id': product.id, 'quantity': 1},
            format='json',
        )
        checkout_response = self.client.post(reverse('checkout'), format='json')
        mpesa_init = self.client.post(
            reverse('mpesa-stk-push'),
            {'order_id': checkout_response.data['id'], 'phone_number': '254700000000'},
            format='json',
        )
        callback_response = self.client.post(
            reverse('mpesa-callback'),
            {'checkout_request_id': mpesa_init.data['checkout_request_id'], 'result_code': 0},
            format='json',
        )
        self.assertEqual(callback_response.status_code, 200)
        self.assertEqual(callback_response.data['payment_status'], 'paid')

    @override_settings(PAYSTACK_SECRET_KEY='test_secret')
    def test_paystack_webhook_marks_payment_paid(self):
        user = User.objects.create_user(
            username='paystack-webhook-user',
            email='buyer@example.com',
            password='strongpassword',
        )
        product = Product.objects.create(
            name='Coffee',
            description='Ground coffee',
            price='10.00',
            stock=10,
        )
        self.client.force_authenticate(user=user)
        self.client.post(
            reverse('cart-items'),
            {'product_id': product.id, 'quantity': 2},
            format='json',
        )
        checkout_response = self.client.post(reverse('checkout'), format='json')
        order = Order.objects.get(pk=checkout_response.data['id'])
        Payment.objects.create(
            order=order,
            user=user,
            provider=Payment.PROVIDER_PAYSTACK,
            reference='paystack_webhook_ref',
            amount='20.00',
            currency='KES',
            status=Payment.STATUS_PENDING,
        )

        payload = {
            'event': 'charge.success',
            'data': {
                'id': 88001,
                'reference': 'paystack_webhook_ref',
                'amount': 2000,
                'currency': 'KES',
            },
        }
        body = json.dumps(payload).encode('utf-8')
        signature = hmac.new(
            b'test_secret',
            body,
            hashlib.sha512,
        ).hexdigest()

        self.client.force_authenticate(user=None)
        response = self.client.post(
            reverse('paystack-webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PAYMENT_PAID)
        self.assertEqual(order.status, Order.STATUS_SUBMITTED)
        self.assertEqual(product.stock, 8)
