from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

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
        self.assertEqual(checkout_response.data['status'], 'submitted')


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        }
    }
)
class AdminAnalyticsViewTests(TestCase):
    def test_admin_analytics_summary(self):
        admin_user = User.objects.create_superuser(
            username='admin',
            password='strongpassword',
            email='admin@example.com',
        )
        buyer = User.objects.create_user(username='buyer', password='strongpassword')
        product = Product.objects.create(
            name='Mug',
            description='Ceramic mug',
            price=Decimal('5.00'),
            stock=10,
        )
        submitted_order = Order.objects.create(
            user=buyer,
            status=Order.STATUS_SUBMITTED,
            checked_out_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=submitted_order,
            product=product,
            quantity=2,
            unit_price=Decimal('5.00'),
        )
        Order.objects.create(user=buyer, status=Order.STATUS_CART)

        self.client.force_login(admin_user)
        response = self.client.get(reverse('admin:analytics'))
        self.assertEqual(response.status_code, 200)

        analytics = response.context['analytics']
        self.assertEqual(analytics['total_orders'], 1)
        self.assertEqual(analytics['active_carts'], 1)
        self.assertEqual(analytics['total_items_sold'], 2)
        self.assertEqual(analytics['total_revenue'], Decimal('10.00'))
        self.assertEqual(analytics['average_order_value'], Decimal('10.00'))
