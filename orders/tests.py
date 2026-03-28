from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from products.models import Product

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
