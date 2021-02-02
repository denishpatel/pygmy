import logging

from django.core.management import BaseCommand

from webapp.models import Settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        syncSettings = {
            "ec2": "Sync EC2 Data",
            "rds": "Sync RDS Data",
            "logs": "Sync Log Data"
        }
        for key, value in syncSettings.items():
            setting = Settings()
            setting.name = key
            setting.last_sync = None
            setting.description = value
            setting.save()