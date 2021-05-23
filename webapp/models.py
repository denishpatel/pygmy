from django.db import models

SYNC = "SYNC"
CONFIG = "CONFIG"
AWS_REGION = "AWS_REGION"

SETTINGS_TYPE = (
    (SYNC, "SYNC"),
    (CONFIG, "CONFIG"),
    (AWS_REGION, "AWS_REGION")
)


# Create your models here.
class Settings(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    type = models.CharField(max_length=255, default="CONFIG")
    in_progress = models.BooleanField(default=False)
    last_sync = models.DateTimeField(null=True)
