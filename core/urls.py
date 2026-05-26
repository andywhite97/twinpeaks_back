from django.urls import path
from .views import CompanyProfileView

urlpatterns = [
    path('company/', CompanyProfileView.as_view()),
]
