from rest_framework import serializers


class CheckoutItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=99)


class CheckoutSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.RegexField(r"^\d{8,15}$", max_length=15)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    meta_event_id = serializers.UUIDField(required=False)
    event_source_url = serializers.URLField(required=False, max_length=500)
    items = CheckoutItemSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        product_ids = [item["product_id"] for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("Each product may appear only once.")
        return items
