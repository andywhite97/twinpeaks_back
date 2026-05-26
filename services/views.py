from rest_framework.generics import ListAPIView
from .models import Service
from .serializers import ServiceSerializer
from rest_framework.permissions import AllowAny


class ServiceListView(ListAPIView):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]
