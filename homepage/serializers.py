from rest_framework import serializers
from .models import HomepageSettings, Project, ProjectImage


class HomepageSettingsSerializer(serializers.ModelSerializer):
    trust_badges = serializers.SerializerMethodField()

    class Meta:
        model = HomepageSettings
        fields = (
            "hero_heading",
            "hero_subheading",
            "hero_background_image",
            "hero_primary_cta_text",
            "hero_primary_cta_url",
            "hero_secondary_cta_text",
            "hero_secondary_cta_url",
            "trust_badges",
            "cta_heading",
            "cta_subheading",
            "cta_background_image",
            "cta_primary_button_text",
            "cta_primary_button_url",
            "cta_secondary_button_text",
            "cta_secondary_button_url",
        )

    def get_trust_badges(self, obj):
        return [badge.strip() for badge in obj.trust_badges.splitlines() if badge.strip()]


class ProjectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectImage
        fields = ("id", "image", "caption", "display_order")


class ProjectSerializer(serializers.ModelSerializer):
    images = ProjectImageSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ("id", "title", "slug", "short_description", "long_description", "location", "category", "image", "images", "completion_date", "link_url")
