from django.urls import path

from .views import AnalyticsOverviewView

urlpatterns = [
    path('checkout/', AnalyticsOverviewView.as_view(), name='checkout-analytics'),
    path('overview/', AnalyticsOverviewView.as_view(), name='analytics-overview'),
]
