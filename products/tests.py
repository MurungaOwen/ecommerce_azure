from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Product


class ProductEndpointTests(APITestCase):
    def test_list_products(self):
        product = Product.objects.create(
            name='Coffee Beans',
            description='Fresh roasted.',
            price='12.50',
            stock=10,
        )
        response = self.client.get(reverse('product-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['id'], product.id)
        self.assertIn('image', response.data[0])
        self.assertIsNone(response.data[0]['image'])
