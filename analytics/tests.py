from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from products.models import Product

User = get_user_model()


class CheckoutAnalyticsTests(APITestCase):
    def test_checkout_analytics_summary(self):
        user = User.objects.create_user(username='analytics-user', password='strongpassword')
        product = Product.objects.create(
            name='Green Tea',
            description='Organic',
            price='8.00',
            stock=5,
        )

        self.client.force_authenticate(user=user)
        self.client.post(
            reverse('cart-items'),
            {'product_id': product.id, 'quantity': 2},
            format='json',
        )
        checkout_response = self.client.post(reverse('checkout'), format='json')
        order_id = checkout_response.data['id']

        paystack_init = self.client.post(
            reverse('paystack-init'),
            {'order_id': order_id},
            format='json',
        )
        self.client.post(
            reverse('paystack-verify'),
            {'reference': paystack_init.data['reference'], 'status': 'success'},
            format='json',
        )

        analytics_response = self.client.get(reverse('checkout-analytics'))
        self.assertEqual(analytics_response.status_code, 200)
        summary = analytics_response.data['summary']
        self.assertEqual(summary['total_checkouts'], 1)
        self.assertEqual(Decimal(str(summary['total_revenue'])), Decimal('16.00'))
        self.assertEqual(summary['total_items'], 2)
        self.assertEqual(analytics_response.data['recent_checkouts'][0]['order'], order_id)
