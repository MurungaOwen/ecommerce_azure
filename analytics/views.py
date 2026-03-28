from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CheckoutEvent
from .serializers import CheckoutEventSerializer


class CheckoutAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        summary = CheckoutEvent.objects.aggregate(
            total_checkouts=Count('id'),
            total_revenue=Coalesce(Sum('total'), Decimal('0.00')),
            total_items=Coalesce(Sum('item_count'), 0),
        )
        recent_events = CheckoutEvent.objects.order_by('-created_at')[:10]
        serializer = CheckoutEventSerializer(recent_events, many=True)
        return Response(
            {
                'summary': summary,
                'recent_checkouts': serializer.data,
            }
        )
