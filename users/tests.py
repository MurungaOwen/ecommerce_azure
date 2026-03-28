from django.urls import reverse
from rest_framework.test import APITestCase


class UserEndpointTests(APITestCase):
    def test_register_and_get_token(self):
        register_response = self.client.post(
            reverse('user-register'),
            {
                'username': 'shopper',
                'email': 'shopper@example.com',
                'password': 'strongpassword',
            },
            format='json',
        )
        self.assertEqual(register_response.status_code, 201)

        token_response = self.client.post(
            reverse('user-token'),
            {'username': 'shopper', 'password': 'strongpassword'},
            format='json',
        )
        self.assertEqual(token_response.status_code, 200)
        self.assertIn('token', token_response.data)
