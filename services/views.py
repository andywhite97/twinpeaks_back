from rest_framework.generics import ListAPIView
from .models import Solution
from .serializers import SolutionSerializer
from rest_framework.permissions import AllowAny


class SolutionListView(ListAPIView):
    queryset = Solution.objects.filter(is_active=True).order_by("pk")
    serializer_class = SolutionSerializer
    permission_classes = [AllowAny]
