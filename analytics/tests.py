from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from products.models import Product
from orders.models import Payment

User = get_user_model()


class CheckoutAnalyticsTests(APITestCase):
    @patch('orders.views.verify_paystack_payment')
    @patch('orders.views.initiate_paystack_payment')
    def test_checkout_analytics_summary(self, mock_initiate_paystack_payment, mock_verify_paystack_payment):
        def mocked_init(order, user):
            return Payment.objects.create(
                order=order,
                user=user,
                provider=Payment.PROVIDER_PAYSTACK,
                reference='paystack_analytics_reference',
                amount='16.00',
                currency='KES',
                metadata={'authorization_url': 'https://checkout.paystack.com/test'},
            )

        mock_initiate_paystack_payment.side_effect = mocked_init
        mock_verify_paystack_payment.return_value = {
            'status': 'success',
            'amount': 1600,
            'currency': 'KES',
            'id': 555001,
            'reference': 'paystack_analytics_reference',
        }

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
            {'reference': paystack_init.data['reference']},
            format='json',
        )

        analytics_response = self.client.get(reverse('checkout-analytics'))
        self.assertEqual(analytics_response.status_code, 200)
        summary = analytics_response.data['summary']
        self.assertEqual(summary['total_checkouts'], 1)
        self.assertEqual(Decimal(str(summary['total_revenue'])), Decimal('16.00'))
        self.assertEqual(summary['total_items'], 2)
        self.assertEqual(analytics_response.data['recent_checkouts'][0]['order'], order_id)
        self.assertEqual(analytics_response.data['users']['total_users'], 1)
        self.assertEqual(analytics_response.data['users']['active_users'], 1)
        self.assertEqual(analytics_response.data['products']['total_products'], 1)
        self.assertEqual(analytics_response.data['products']['active_products'], 1)
        self.assertEqual(analytics_response.data['products']['out_of_stock'], 0)
        self.assertEqual(analytics_response.data['orders']['total_orders'], 1)
        self.assertEqual(analytics_response.data['orders']['status']['cart'], 0)
        self.assertEqual(analytics_response.data['orders']['status']['payment_pending'], 0)
        self.assertEqual(analytics_response.data['orders']['status']['submitted'], 1)
        self.assertEqual(analytics_response.data['orders']['payment_status']['pending'], 0)
        self.assertEqual(analytics_response.data['orders']['payment_status']['paid'], 1)
        self.assertEqual(analytics_response.data['orders']['payment_status']['failed'], 0)
        self.assertEqual(analytics_response.data['orders']['fulfillment_status']['pending'], 1)
        self.assertEqual(analytics_response.data['orders']['fulfillment_status']['processing'], 0)
        self.assertEqual(analytics_response.data['orders']['fulfillment_status']['completed'], 0)
        self.assertEqual(analytics_response.data['orders']['fulfillment_status']['cancelled'], 0)
