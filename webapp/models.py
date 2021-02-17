from django.db import models


# Create your models here.
class Settings(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255)
    in_progress = models.BooleanField(default=False)
    last_sync = models.DateTimeField(null=True)
