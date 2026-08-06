from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Brand, HomepageSettings, Project, Solution, Statistic, Testimonial
from .serializers import (
    BrandSerializer,
    HomepageSettingsSerializer,
    ProjectSerializer,
    SolutionSerializer,
    StatisticSerializer,
    TestimonialSerializer,
)


class HomepageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        settings = HomepageSettings.objects.filter(is_active=True).first()
        hero = HomepageSettingsSerializer(settings).data if settings else {}
        return Response({
            "hero": hero,
            "statistics": StatisticSerializer(
                Statistic.objects.filter(is_active=True).order_by("display_order", "created_at"),
                many=True,
            ).data,
            "featured_products": [],
            "solutions": SolutionSerializer(
                Solution.objects.filter(is_active=True).order_by("display_order", "created_at"),
                many=True,
            ).data,
            "projects": ProjectSerializer(
                Project.objects.filter(is_active=True, is_featured=True).order_by("display_order", "created_at"),
                many=True,
            ).data,
            "brands": BrandSerializer(
                Brand.objects.filter(is_active=True, is_featured=True).order_by("display_order", "created_at"),
                many=True,
            ).data,
            "testimonials": TestimonialSerializer(
                Testimonial.objects.filter(is_active=True).order_by("display_order", "created_at"),
                many=True,
            ).data,
            "settings": hero,
        })


class SolutionListView(ListAPIView):
    queryset = Solution.objects.filter(is_active=True).order_by("display_order", "created_at")
    serializer_class = SolutionSerializer
    permission_classes = [AllowAny]


class StatisticListView(ListAPIView):
    queryset = Statistic.objects.filter(is_active=True).order_by("display_order", "created_at")
    serializer_class = StatisticSerializer
    permission_classes = [AllowAny]


class ProjectListView(ListAPIView):
    queryset = Project.objects.filter(is_active=True, is_featured=True).order_by("display_order", "created_at")
    serializer_class = ProjectSerializer
    permission_classes = [AllowAny]


class BrandListView(ListAPIView):
    queryset = Brand.objects.filter(is_active=True, is_featured=True).order_by("display_order", "created_at")
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]


class TestimonialListView(ListAPIView):
    queryset = Testimonial.objects.filter(is_active=True).order_by("display_order", "created_at")
    serializer_class = TestimonialSerializer
    permission_classes = [AllowAny]
