from rest_framework import serializers
from .models import Brand, HeroSlide, HomepageSettings, Project, Solution, Statistic, Testimonial


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
        )

    def get_trust_badges(self, obj):
        return [badge.strip() for badge in obj.trust_badges.splitlines() if badge.strip()]


class HeroSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroSlide
        fields = "__all__"


class SolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Solution
        fields = "__all__"


class StatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Statistic
        fields = "__all__"


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = "__all__"
