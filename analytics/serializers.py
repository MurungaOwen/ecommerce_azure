from rest_framework import serializers

from .models import CheckoutEvent


class CheckoutEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckoutEvent
        fields = ('id', 'order', 'total', 'item_count', 'created_at')
