from django.http import FileResponse
from rest_framework.permissions import IsAdminUser
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView

from .generator import (
    build_invoice_workbook,
    calculate_invoice_totals,
    normalize_invoice_date,
)
from .models import Invoice
from .serializers import InvoiceGenerateSerializer, InvoiceSerializer


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
        workbook = build_invoice_workbook(data)
        invoice_number = data["invoice_number"]
        customer = data["customer"]
        subtotal, tax, total = calculate_invoice_totals(data)
        Invoice.objects.create(
            invoice_number=invoice_number,
            customer_id=data.get("customer_id", ""),
            customer_name=customer["name"],
            customer_location=customer.get("location", ""),
            customer_email=customer.get("email", ""),
            customer_phone=customer.get("phone", ""),
            invoice_date=normalize_invoice_date(data),
            due_date=data.get("due_date"),
            salesperson=data.get("salesperson", ""),
            job=data.get("job", ""),
            payment_terms=data.get("payment_terms", ""),
            tax_rate=data.get("tax_rate"),
            subtotal=subtotal,
            tax=tax,
            total=total,
            items=[
                {
                    "quantity": str(item["quantity"]),
                    "description": item["description"],
                    "unit_price": str(item["unit_price"]),
                }
                for item in data["items"]
            ],
            generated_by=request.user if request.user.is_authenticated else None,
        )
        filename = f"invoice-{invoice_number}.xlsx"

        return FileResponse(
            workbook,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
