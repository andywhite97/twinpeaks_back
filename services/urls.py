from django.urls import path
from .views import SolutionListView

urlpatterns = [
    path('solutions/', SolutionListView.as_view(), name='solution-list'),
    path('services/', SolutionListView.as_view(), name='legacy-service-list'),
]
