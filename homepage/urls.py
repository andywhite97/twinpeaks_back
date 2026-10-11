from django.urls import path
from .views import HomepageView, ProjectDetailView, ProjectListView

urlpatterns = [
    path("homepage/", HomepageView.as_view(), name="homepage"),
    path("projects/", ProjectListView.as_view(), name="project-list"),
    path("projects/<slug:slug>/", ProjectDetailView.as_view(), name="project-detail"),
]
