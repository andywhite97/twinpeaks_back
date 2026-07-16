from rest_framework import serializers

from products.models import Product

from .models import Customer, Invoice, InvoiceItem


class InvoiceCustomerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate_email(self, value):
        return value.strip().lower()


class InvoiceItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True)
    )
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)

    def validate_product(self, value):
        if value.price is None:
            raise serializers.ValidationError("This product does not have a price.")
        return value


class InvoiceGenerateSerializer(serializers.Serializer):
    customer = InvoiceCustomerSerializer()
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


class InvoiceSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(read_only=True)
    customer_id = serializers.CharField(source="customer.customer_id", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_location = serializers.CharField(source="customer.location", read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    items = serializers.SerializerMethodField()
    line_items = serializers.SerializerMethodField()

    def get_items(self, invoice):
        return InvoiceLineItemSerializer(invoice.items.all(), many=True).data

    def get_line_items(self, invoice):
        return self.get_items(invoice)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "customer",
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
            "invoice_pdf",
            "invoice_workbook",
            "items",
            "line_items",
            "status",
            "generated_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = (
            "id",
            "product_id",
            "product_slug",
            "product_name",
            "product_description",
            "quantity",
            "unit_price",
            "line_total",
            "created_at",
        )
        read_only_fields = fields


class InvoiceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ("status",)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = (
            "email",
            "customer_id",
            "name",
            "location",
            "phone",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
