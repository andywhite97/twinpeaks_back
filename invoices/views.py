from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from pathlib import Path
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .tasks import send_invoice_email

from .generator import (
    build_invoice_pdf,
    build_invoice_workbook,
    calculate_invoice_totals,
    convert_workbook_to_pdf,
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
    permission_classes = [AllowAny]


class InvoiceGenerateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InvoiceGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        customer_data = data["customer"]
        customer, _created = Customer.objects.update_or_create(
            email=customer_data["email"],
            defaults={
                "name": customer_data["name"],
                "location": customer_data.get("location", ""),
                "phone": customer_data.get("phone", ""),
            },
        )
        invoice_data = {
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
        subtotal, tax, total = calculate_invoice_totals(invoice_data)
        invoice_date = normalize_invoice_date(data)
        invoice = Invoice.objects.create(
            customer=customer,
            invoice_date=invoice_date,
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
        invoice_number = invoice.invoice_number
        invoice_data["date"] = invoice_date
        invoice_data["invoice_number"] = invoice_number
        saved_paths = []
        try:
            with transaction.atomic():
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
                workbook = build_invoice_workbook(invoice_data)
                workbook_filename = f"{invoice_number}.xlsx"
                workbook_bytes = workbook.getvalue()
                invoice.invoice_workbook = self._save_invoice_file(
                    "workbooks",
                    workbook_filename,
                    workbook_bytes,
                    saved_paths,
                )

                pdf = convert_workbook_to_pdf(workbook, workbook_filename)
                pdf_source = "invoice_design.xlsx"
                if pdf is None:
                    pdf = build_invoice_pdf(invoice_data)
                    pdf_source = "fallback-pdf"

                pdf_bytes = pdf.getvalue()
                filename = f"{invoice_number}.pdf"
                invoice.invoice_pdf = self._save_invoice_file(
                    "pdfs",
                    filename,
                    pdf_bytes,
                    saved_paths,
                )
                invoice.save(update_fields=["invoice_pdf", "invoice_workbook"])
                send_invoice_email.apply(args=(invoice.id, filename))
        except Exception:
            for path in saved_paths:
                try:
                    default_storage.delete(path)
                except Exception:
                    pass
            raise

        response = FileResponse(
            pdf,
            as_attachment=True,
            filename=filename,
            content_type="application/pdf",
        )
        response["X-Invoice-Pdf-Path"] = self._invoice_file_absolute_path(
            invoice.invoice_pdf
        )
        response["X-Invoice-Pdf-Url"] = self._invoice_file_url(
            invoice.invoice_pdf,
            request,
        )
        response["X-Invoice-Workbook-Path"] = self._invoice_file_absolute_path(
            invoice.invoice_workbook
        )
        response["X-Invoice-Template-Source"] = pdf_source
        return response

    def _save_invoice_file(self, folder, filename, file_bytes, saved_paths=None):
        relative_path = Path("invoices") / folder / filename
        relative_path_str = relative_path.as_posix()
        if default_storage.exists(relative_path_str):
            default_storage.delete(relative_path_str)
        default_storage.save(relative_path_str, ContentFile(file_bytes))
        if saved_paths is not None:
            saved_paths.append(relative_path_str)
        return relative_path_str

    def _invoice_file_absolute_path(self, relative_path):
        relative_path_str = (
            relative_path.as_posix()
            if isinstance(relative_path, Path)
            else str(relative_path)
        )
        if hasattr(default_storage, "path"):
            return default_storage.path(relative_path_str)
        return str(Path(settings.MEDIA_ROOT) / relative_path_str)

    def _invoice_file_url(self, relative_path, request):
        relative_path_str = (
            relative_path.as_posix()
            if isinstance(relative_path, Path)
            else str(relative_path)
        )
        if hasattr(default_storage, "url"):
            url = default_storage.url(relative_path_str)
            if url.startswith("http://") or url.startswith("https://"):
                return url
            return request.build_absolute_uri(url)
        return request.build_absolute_uri(f"{settings.MEDIA_URL}{relative_path_str}")


class InvoiceStatusUpdateView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        serializer = InvoiceStatusSerializer(invoice, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(InvoiceSerializer(invoice).data)
