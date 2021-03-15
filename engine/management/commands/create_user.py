from users.models import User
from django.core.management import BaseCommand
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        user = User.objects.create_user('admin', password='admin')
        user.is_superuser = False
        user.is_staff = True
        user.save()