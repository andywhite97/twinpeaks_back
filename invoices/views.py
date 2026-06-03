from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .generator import (
    build_invoice_workbook,
    calculate_invoice_totals,
    normalize_invoice_date,
)
from .models import Customer, Invoice, InvoiceItem
from .serializers import (
    CustomerSerializer,
    InvoiceGenerateSerializer,
    InvoiceSerializer,
    InvoiceStatusSerializer,
)


class CustomerListView(ListAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]


class CustomerDetailView(RetrieveAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]


class InvoiceListView(ListAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAdminUser]


class InvoiceDetailView(RetrieveAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAdminUser]


class InvoiceGenerateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = InvoiceGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        invoice_number = data["invoice_number"]
        customer_data = data["customer"]
        customer, _created = Customer.objects.update_or_create(
            email=customer_data["email"],
            defaults={
                "name": customer_data["name"],
                "location": customer_data.get("location", ""),
                "phone": customer_data.get("phone", ""),
            },
        )
        workbook_data = {
            **data,
            "customer": {
                "name": customer.name,
                "location": customer.location,
                "email": customer.email,
                "phone": customer.phone,
            },
            "customer_id": customer.customer_id,
            "items": [
                {
                    "quantity": item["quantity"],
                    "description": item["product"].name,
                    "unit_price": item["product"].price,
                }
                for item in data["items"]
            ],
        }
        workbook = build_invoice_workbook(workbook_data)
        subtotal, tax, total = calculate_invoice_totals(workbook_data)
        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            customer=customer,
            invoice_date=normalize_invoice_date(data),
            due_date=data.get("due_date"),
            salesperson=data.get("salesperson", ""),
            job=data.get("job", ""),
            payment_terms=data.get("payment_terms", ""),
            tax_rate=data.get("tax_rate"),
            subtotal=subtotal,
            tax=tax,
            total=total,
            generated_by=request.user if request.user.is_authenticated else None,
        )
        invoice_items = InvoiceItem.objects.bulk_create(
            [
                InvoiceItem(
                    product=item["product"],
                    product_name=item["product"].name,
                    product_description=item["product"].description,
                    quantity=item["quantity"],
                    unit_price=item["product"].price,
                    line_total=item["quantity"] * item["product"].price,
                )
                for item in data["items"]
            ]
        )
        invoice.items.add(*invoice_items)
        filename = f"invoice-{invoice_number}.xlsx"

        return FileResponse(
            workbook,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class InvoiceStatusUpdateView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        serializer = InvoiceStatusSerializer(invoice, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(InvoiceSerializer(invoice).data)
