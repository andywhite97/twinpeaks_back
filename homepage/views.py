from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import HomepageSettings, Project
from services.models import Solution
from services.serializers import SolutionSerializer
from .serializers import (
    HomepageSettingsSerializer,
    ProjectSerializer,
)


@method_decorator(cache_page(60 * 5), name="dispatch")
class HomepageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        settings = HomepageSettings.objects.filter(is_active=True).first()
        hero = HomepageSettingsSerializer(settings).data if settings else {}
        return Response({
            "hero": hero,
            "solutions": SolutionSerializer(
                Solution.objects.filter(is_active=True).order_by("pk"),
                many=True,
                context={"request": request},
            ).data,
            "projects": ProjectSerializer(
                Project.objects.filter(is_active=True, is_featured=True).prefetch_related("images").order_by("display_order", "created_at"),
                many=True,
            ).data,
            "settings": hero,
        })


class ProjectListView(ListAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Project.objects.filter(is_active=True).prefetch_related("images").order_by("display_order", "created_at")
        if self.request.query_params.get("featured") == "true":
            queryset = queryset.filter(is_featured=True)
        return queryset


class ProjectDetailView(RetrieveAPIView):
    queryset = Project.objects.filter(is_active=True).prefetch_related("images")
    serializer_class = ProjectSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
