from django.db import models


class Service(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    icon = models.ImageField(upload_to="services/icons/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
