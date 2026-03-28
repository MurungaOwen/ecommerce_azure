from django.urls import path

from .views import CartItemView, CartView, CheckoutView

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/', CartItemView.as_view(), name='cart-items'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
]
