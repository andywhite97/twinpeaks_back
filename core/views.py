from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from django.http import Http404
from .models import CompanyProfile
from .serializers import CompanyProfileSerializer


class CompanyProfileView(RetrieveAPIView):
    queryset = CompanyProfile.objects.all()
    serializer_class = CompanyProfileSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        profile = self.get_queryset().first()
        if profile is None:
            raise Http404("Company profile not found.")

        return profile
