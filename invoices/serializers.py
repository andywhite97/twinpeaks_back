from rest_framework import serializers

from .models import Invoice


class InvoiceCustomerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)


class InvoiceItemSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    description = serializers.CharField(max_length=300)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class InvoiceGenerateSerializer(serializers.Serializer):
    customer = InvoiceCustomerSerializer()
    invoice_number = serializers.CharField(max_length=50)
    customer_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    date = serializers.DateField(required=False)
    due_date = serializers.DateField(required=False)
    salesperson = serializers.CharField(max_length=120, required=False, allow_blank=True)
    job = serializers.CharField(max_length=120, required=False, allow_blank=True)
    payment_terms = serializers.CharField(max_length=120, required=False, allow_blank=True)
    tax_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=4,
        min_value=0,
        max_value=1,
        default="0.15",
    )
    items = InvoiceItemSerializer(many=True, min_length=1, max_length=10)

    def validate_invoice_number(self, value):
        if Invoice.objects.filter(invoice_number=value).exists():
            raise serializers.ValidationError("An invoice with this number already exists.")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "customer_id",
            "customer_name",
            "customer_location",
            "customer_email",
            "customer_phone",
            "invoice_date",
            "due_date",
            "salesperson",
            "job",
            "payment_terms",
            "tax_rate",
            "subtotal",
            "tax",
            "total",
            "items",
            "status",
            "generated_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
