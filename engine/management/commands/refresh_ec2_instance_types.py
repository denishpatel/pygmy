import logging
from django.core.management.base import BaseCommand
from engine.views import update_all_ec2_instances_db
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            update_all_ec2_instances_db()
        except Exception as e:
            logger.exception(e)
            return
