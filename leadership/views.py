from rest_framework.generics import ListAPIView
from .models import Leader
from .serializers import LeaderSerializer
from rest_framework.permissions import AllowAny


class LeaderListView(ListAPIView):
    queryset = Leader.objects.filter(is_active=True)
    serializer_class = LeaderSerializer
    permission_classes = [AllowAny]
