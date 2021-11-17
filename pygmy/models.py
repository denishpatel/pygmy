from django.db import models


class Log(models.Model):
    time = models.DateTimeField(null=False, auto_now_add=True)
    level_name = models.CharField(null=True, max_length=255)
    module = models.CharField(null=True, max_length=255)
    line_no = models.IntegerField(null=True)
    message = models.TextField(null=True)
    last_line = models.TextField(null=True)
    object = models.JSONField(null=True)
