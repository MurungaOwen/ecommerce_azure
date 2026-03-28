from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from analytics.models import CheckoutEvent
from products.models import Product
from .models import Order, OrderItem

User = get_user_model()


class CheckoutFlowTests(APITestCase):
    def test_add_to_cart_and_checkout(self):
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
            {'reference': paystack_init.data['reference'], 'status': 'success'},
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
