from django.urls import path
from .views import BrandListView, HomepageView, ProjectListView, SolutionListView, StatisticListView, TestimonialListView

urlpatterns = [
    path("homepage/", HomepageView.as_view(), name="homepage"),
    path("solutions/", SolutionListView.as_view(), name="solution-list"),
    path("statistics/", StatisticListView.as_view(), name="statistics-list"),
    path("projects/", ProjectListView.as_view(), name="project-list"),
    path("brands/", BrandListView.as_view(), name="brand-list"),
    path("testimonials/", TestimonialListView.as_view(), name="testimonial-list"),
]
