from django.urls import path

from .views import (
    CartItemView,
    CartView,
    CheckoutView,
    MpesaCallbackView,
    MpesaStkPushView,
    PaystackInitializeView,
    PaystackVerifyView,
)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/', CartItemView.as_view(), name='cart-items'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('payments/paystack/initialize/', PaystackInitializeView.as_view(), name='paystack-init'),
    path('payments/paystack/verify/', PaystackVerifyView.as_view(), name='paystack-verify'),
    path('payments/mpesa/stk-push/', MpesaStkPushView.as_view(), name='mpesa-stk-push'),
    path('payments/mpesa/callback/', MpesaCallbackView.as_view(), name='mpesa-callback'),
]
