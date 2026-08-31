from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from products.models import Product
from services.models import Service
from .models import ContactMessage, Quotation, QuotationItem


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ("id", "name", "email", "message", "created_at")
        read_only_fields = ("id", "created_at")


class QuotationRequestItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=False, min_value=1)
    service_id = serializers.IntegerField(required=False, min_value=1)
    description = serializers.CharField(required=False, allow_blank=False, max_length=2000)
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)

    def validate(self, attrs):
        if sum(key in attrs for key in ("product_id", "service_id", "description")) != 1:
            raise serializers.ValidationError("Each quote item must specify one product, service, or custom description.")
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
                if "product_id" in item:
                    product = Product.objects.filter(pk=item["product_id"], is_active=True).first()
                    if not product:
                        raise serializers.ValidationError({"items": "A selected product is no longer available."})
                    price = product.sale_price if product.sale_price is not None else product.price
                    if price is None:
                        price = Decimal("0.00")
                    QuotationItem.objects.create(quotation=quotation, product=product, title=product.name, description=product.description, quantity=quantity, unit_price=price, sort_order=position)
                elif "service_id" in item:
                    service = Service.objects.filter(pk=item["service_id"], is_active=True).first()
                    if not service:
                        raise serializers.ValidationError({"items": "A selected service is no longer available."})
                    QuotationItem.objects.create(quotation=quotation, service=service, title=service.title, description=service.description, quantity=quantity, sort_order=position)
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
