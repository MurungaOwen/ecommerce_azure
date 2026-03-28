from django.urls import path

from .views import CheckoutAnalyticsView

urlpatterns = [
    path('checkout/', CheckoutAnalyticsView.as_view(), name='checkout-analytics'),
    path('overview/', CheckoutAnalyticsView.as_view(), name='analytics-overview'),
]
