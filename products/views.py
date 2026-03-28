from rest_framework import permissions, viewsets, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from .models import Product
from .serializers import ProductSerializer


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    category = django_filters.CharFilter(field_name="category", lookup_expr='icontains')

    class Meta:
        model = Product
        fields = ['category', 'min_price', 'max_price']


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'category']

    def get_queryset(self):
        return Product.objects.filter(is_active=True).order_by('name')

# Create your views here.
