from django.urls import path

from .views import CartItemView, CartView, CheckoutView, PaystackInitializeView, PaystackVerifyView

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/', CartItemView.as_view(), name='cart-items'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('payments/paystack/initialize/', PaystackInitializeView.as_view(), name='paystack-init'),
    path('payments/paystack/verify/', PaystackVerifyView.as_view(), name='paystack-verify'),
]
