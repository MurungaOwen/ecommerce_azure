from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from products.models import Product

from .models import CheckoutEvent
from .serializers import CheckoutEventSerializer

User = get_user_model()


class AnalyticsOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        summary = CheckoutEvent.objects.aggregate(
            total_checkouts=Count('id'),
            total_revenue=Coalesce(Sum('total'), Decimal('0.00')),
            total_items=Coalesce(Sum('item_count'), 0),
        )
        user_summary = User.objects.aggregate(
            total_users=Count('id'),
            active_users=Count('id', filter=Q(is_active=True)),
        )
        product_summary = Product.objects.aggregate(
            total_products=Count('id'),
            active_products=Count('id', filter=Q(is_active=True)),
            out_of_stock=Count('id', filter=Q(stock__lte=0)),
        )
        order_counts = Order.objects.aggregate(
            total_orders=Count('id'),
            status_cart=Count('id', filter=Q(status=Order.STATUS_CART)),
            status_payment_pending=Count(
                'id',
                filter=Q(status=Order.STATUS_PAYMENT_PENDING),
            ),
            status_submitted=Count('id', filter=Q(status=Order.STATUS_SUBMITTED)),
            payment_pending=Count('id', filter=Q(payment_status=Order.PAYMENT_PENDING)),
            payment_paid=Count('id', filter=Q(payment_status=Order.PAYMENT_PAID)),
            payment_failed=Count('id', filter=Q(payment_status=Order.PAYMENT_FAILED)),
            fulfillment_pending=Count(
                'id',
                filter=Q(fulfillment_status=Order.FULFILLMENT_PENDING),
            ),
            fulfillment_processing=Count(
                'id',
                filter=Q(fulfillment_status=Order.FULFILLMENT_PROCESSING),
            ),
            fulfillment_completed=Count(
                'id',
                filter=Q(fulfillment_status=Order.FULFILLMENT_COMPLETED),
            ),
            fulfillment_cancelled=Count(
                'id',
                filter=Q(fulfillment_status=Order.FULFILLMENT_CANCELLED),
            ),
        )
        recent_events = CheckoutEvent.objects.order_by('-created_at')[:10]
        serializer = CheckoutEventSerializer(recent_events, many=True)
        return Response(
            {
                'summary': summary,
                'recent_checkouts': serializer.data,
                'users': user_summary,
                'products': product_summary,
                'orders': {
                    'total_orders': order_counts['total_orders'],
                    'status': {
                        Order.STATUS_CART: order_counts['status_cart'],
                        Order.STATUS_PAYMENT_PENDING: order_counts['status_payment_pending'],
                        Order.STATUS_SUBMITTED: order_counts['status_submitted'],
                    },
                    'payment_status': {
                        Order.PAYMENT_PENDING: order_counts['payment_pending'],
                        Order.PAYMENT_PAID: order_counts['payment_paid'],
                        Order.PAYMENT_FAILED: order_counts['payment_failed'],
                    },
                    'fulfillment_status': {
                        Order.FULFILLMENT_PENDING: order_counts['fulfillment_pending'],
                        Order.FULFILLMENT_PROCESSING: order_counts['fulfillment_processing'],
                        Order.FULFILLMENT_COMPLETED: order_counts['fulfillment_completed'],
                        Order.FULFILLMENT_CANCELLED: order_counts['fulfillment_cancelled'],
                    },
                },
            }
        )
