from io import BytesIO

from PIL import Image
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from rest_framework.test import APITestCase

from .models import Service


def png_upload(name):
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "#164d6b").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class ServiceImageTests(APITestCase):
    def admin_form(self, files=None):
        request = RequestFactory().get("/admin/services/service/add/")
        request.user = get_user_model()(is_staff=True, is_superuser=True)
        form_class = admin.site._registry[Service].get_form(request)
        return form_class(
            data={"title": "IT Support & Maintenance", "description": "Published service", "is_active": True},
            files=files or {},
        )

    def test_existing_services_without_images_remain_available(self):
        service = Service.objects.create(title="Network Infrastructure", description="Published")
        response = self.client.get("/api/services/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], service.pk)
        self.assertIsNone(response.data[0]["image"])

    def test_admin_can_upload_separate_icon_and_image(self):
        form = self.admin_form({"icon": png_upload("icon.png"), "image": png_upload("service.png")})
        self.assertTrue(form.is_valid(), form.errors)
        service = form.save()
        service.refresh_from_db()
        self.assertTrue(service.icon.name.startswith("services/icons/"))
        self.assertTrue(service.image.name.startswith("services/images/"))
        response = self.client.get("/api/services/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["image"], "http://testserver" + service.image.url)
        self.assertEqual(response.data[0]["icon"], "http://testserver" + service.icon.url)

    def test_admin_allows_image_to_be_omitted(self):
        form = self.admin_form()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.save().image)

    def test_admin_rejects_non_image_upload(self):
        form = self.admin_form({"image": SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")})
        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)
