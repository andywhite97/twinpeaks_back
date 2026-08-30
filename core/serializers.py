from rest_framework import serializers
from .models import CompanyProfile


class CompanyProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompanyProfile
        fields = ("id", "name", "tagline", "overview", "vision", "mission", "facebook", "twitter", "instagram", "linkedin", "email", "phone", "whatsapp", "address", "business_hours", "copyright_text")
