from django.db import transaction
from rest_framework import serializers

from services.models import Solution
from .models import ContactMessage, Quotation, QuotationItem


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ("id", "name", "email", "message", "created_at")
        read_only_fields = ("id", "created_at")


class QuotationRequestItemSerializer(serializers.Serializer):
    solution_id = serializers.IntegerField(required=False, min_value=1)
    service_id = serializers.IntegerField(required=False, min_value=1, write_only=True)
    description = serializers.CharField(required=False, allow_blank=False, max_length=2000)
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)

    def to_internal_value(self, data):
        if isinstance(data, dict) and "product_id" in data:
            raise serializers.ValidationError({"product_id": "Product catalog quotation requests have been retired."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        if "service_id" in attrs:
            if "solution_id" in attrs:
                raise serializers.ValidationError("Specify solution_id once; do not also supply service_id.")
            attrs["solution_id"] = attrs.pop("service_id")
        if sum(key in attrs for key in ("solution_id", "description")) != 1:
            raise serializers.ValidationError("Each quote item must specify one solution or custom description.")
        return attrs


class QuotationRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    company_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.RegexField(r"^\d{8,15}$", max_length=15)
    address = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    message = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    items = QuotationRequestItemSerializer(many=True, allow_empty=False)

    def create(self, validated_data):
        items = validated_data.pop("items")
        with transaction.atomic():
            quotation = Quotation.objects.create(**validated_data)
            for position, item in enumerate(items):
                quantity = item["quantity"]
                if "solution_id" in item:
                    solution = Solution.objects.filter(pk=item["solution_id"], is_active=True).first()
                    if not solution:
                        raise serializers.ValidationError({"items": "A selected solution is no longer available."})
                    QuotationItem.objects.create(quotation=quotation, solution=solution, title=solution.title, description=solution.description, quantity=quantity, sort_order=position)
                else:
                    QuotationItem.objects.create(quotation=quotation, title="Custom requirement", description=item["description"], quantity=quantity, sort_order=position)
            quotation.recalculate_totals()
            quotation.save(update_fields=["subtotal", "total", "updated_at"])
        return quotation


class PublicQuotationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationItem
        fields = ("title", "description", "quantity", "unit_price", "discount_amount", "tax_amount", "line_total")


class PublicQuotationSerializer(serializers.ModelSerializer):
    items = PublicQuotationItemSerializer(many=True, read_only=True)

    class Meta:
        model = Quotation
        fields = ("quote_number", "name", "company_name", "email", "phone_number", "address", "message", "status", "subtotal", "discount_amount", "tax_amount", "total", "currency", "terms", "valid_until", "created_at", "sent_at", "viewed_at", "accepted_at", "declined_at", "decline_reason", "items")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.status in {Quotation.Status.REQUESTED, Quotation.Status.UNDER_REVIEW, Quotation.Status.DRAFT}:
            for key in ("subtotal", "discount_amount", "tax_amount", "total", "currency", "terms", "valid_until", "items"):
                data.pop(key, None)
        return data
