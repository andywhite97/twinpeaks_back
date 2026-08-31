from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import ContactMessage, Quotation
from .serializers import ContactMessageSerializer, PublicQuotationSerializer, QuotationRequestSerializer
from .tasks import send_contact_message_notification, send_quotation_accepted_notification, send_quotation_request_notification

class ContactMessageCreateView(CreateAPIView):
    queryset = ContactMessage.objects.all(); serializer_class = ContactMessageSerializer; permission_classes = [AllowAny]; throttle_classes = [AnonRateThrottle]
    def perform_create(self, serializer):
        message = serializer.save(); send_contact_message_notification(message)

class ContactMessageListView(ListAPIView):
    queryset = ContactMessage.objects.all().order_by("-created_at"); serializer_class = ContactMessageSerializer; permission_classes = [IsAdminUser]

class QuotationRequestCreateView(APIView):
    permission_classes = [AllowAny]; throttle_classes = [AnonRateThrottle]
    def post(self, request):
        serializer = QuotationRequestSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        quotation = serializer.save()
        transaction.on_commit(lambda: send_quotation_request_notification(quotation.pk))
        return Response({"quote_number": quotation.quote_number, "public_access_token": str(quotation.public_access_token), "status": quotation.status}, status=status.HTTP_201_CREATED)

class PublicQuotationView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, token):
        try: quotation = Quotation.objects.prefetch_related("items").get(public_access_token=token)
        except Quotation.DoesNotExist: return Response({"detail": "Quotation not found."}, status=status.HTTP_404_NOT_FOUND)
        quotation.refresh_expiry()
        if quotation.status == Quotation.Status.SENT and quotation.viewed_at is None:
            quotation.status = Quotation.Status.VIEWED; quotation.viewed_at = timezone.now(); quotation.save(update_fields=["status", "viewed_at", "updated_at"])
        return Response(PublicQuotationSerializer(quotation).data, headers={"X-Robots-Tag": "noindex, nofollow"})

class PublicQuotationDecisionView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, token, decision):
        with transaction.atomic():
            try: quotation = Quotation.objects.select_for_update().get(public_access_token=token)
            except Quotation.DoesNotExist: return Response({"detail": "Quotation not found."}, status=status.HTTP_404_NOT_FOUND)
            quotation.refresh_expiry()
            if quotation.status not in {Quotation.Status.SENT, Quotation.Status.VIEWED}:
                return Response({"detail": "This quotation cannot be changed."}, status=status.HTTP_409_CONFLICT)
            if decision == "accept":
                quotation.status = Quotation.Status.ACCEPTED; quotation.accepted_at = timezone.now(); quotation.save(update_fields=["status", "accepted_at", "updated_at"])
                transaction.on_commit(lambda: send_quotation_accepted_notification(quotation.pk))
            else:
                quotation.status = Quotation.Status.DECLINED; quotation.declined_at = timezone.now(); quotation.decline_reason = request.data.get("reason", "")[:500]; quotation.save(update_fields=["status", "declined_at", "decline_reason", "updated_at"])
        return Response(PublicQuotationSerializer(quotation).data)

class PublicQuotationPdfView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, token):
        try: quotation = Quotation.objects.prefetch_related("items").get(public_access_token=token)
        except Quotation.DoesNotExist: return Response({"detail": "Quotation not found."}, status=status.HTTP_404_NOT_FOUND)
        quotation.refresh_expiry()
        if quotation.status not in {Quotation.Status.SENT, Quotation.Status.VIEWED, Quotation.Status.ACCEPTED, Quotation.Status.EXPIRED, Quotation.Status.CONVERTED_TO_ORDER}:
            return Response({"detail": "This quotation is not ready for download."}, status=status.HTTP_409_CONFLICT)
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        buffer = BytesIO(); document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
        styles = getSampleStyleSheet(); rows = [["Item", "Qty", "Unit price", "Total"]]
        for item in quotation.items.all(): rows.append([item.title, str(item.quantity), f"{item.unit_price:.2f}", f"{item.line_total:.2f}"])
        rows.extend([["", "", "Subtotal", f"{quotation.subtotal:.2f}"], ["", "", "Discount", f"{quotation.discount_amount:.2f}"], ["", "", "Tax", f"{quotation.tax_amount:.2f}"], ["", "", "Total", f"{quotation.total:.2f} {quotation.currency}"]])
        table = Table(rows, colWidths=[82*mm, 18*mm, 36*mm, 36*mm]); table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17191b")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .25, colors.HexColor("#cccccc")), ("ALIGN", (1,1), (-1,-1), "RIGHT"), ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold")]))
        story = [Paragraph("TwinPeaks Investment", styles["Title"]), Paragraph(f"Quotation {quotation.quote_number}", styles["Heading2"]), Paragraph(f"Issued: {quotation.sent_at.date() if quotation.sent_at else 'Pending'} &nbsp;&nbsp; Valid until: {quotation.valid_until or 'To be confirmed'}", styles["Normal"]), Spacer(1, 8*mm), Paragraph(f"<b>Customer:</b> {quotation.name}<br/><b>Email:</b> {quotation.email}<br/><b>Phone:</b> {quotation.phone_number}", styles["Normal"]), Spacer(1, 8*mm), table, Spacer(1, 8*mm), Paragraph(quotation.message or "", styles["Normal"]), Paragraph(quotation.terms or "", styles["Normal"])]
        document.build(story)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf"); response["Content-Disposition"] = f'inline; filename="{quotation.quote_number}.pdf"'; response["X-Robots-Tag"] = "noindex, nofollow"; return response
