from django.db import models


class Solution(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    icon = models.ImageField(upload_to="solutions/icons/", blank=True, null=True)
    image = models.ImageField(
        upload_to="solutions/images/", blank=True, null=True,
        help_text="Optional main solution image (PNG, JPEG or WebP).",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
