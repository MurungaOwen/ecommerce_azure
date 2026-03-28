from rest_framework import permissions, viewsets

from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Product.objects.filter(is_active=True).order_by('name')

# Create your views here.
