from rest_framework.test import APITestCase

from .models import Leader


class LeaderListTests(APITestCase):
    def test_only_active_leaders_are_public(self):
        Leader.objects.create(name="Visible", role="Director", bio="Public", is_active=True)
        Leader.objects.create(name="Hidden", role="Director", bio="Private", is_active=False)

        response = self.client.get("/api/leaders/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([leader["name"] for leader in response.data], ["Visible"])
