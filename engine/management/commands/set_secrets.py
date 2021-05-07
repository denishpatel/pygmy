import logging
from django.core.management import BaseCommand
from engine.models import DbCredentials

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        aws_access_key = input("Enter AWS Access Key: ")
        aws_secret = input("Enter AWS Secret: ")
        secret, created = DbCredentials.objects.get_or_create(name="aws")
        secret.description = "AWS Secrets"
        secret.user_name = aws_access_key
        secret.password = aws_secret
        secret.save()

        db_username = input("Enter Db username: ")
        db_pwd = input("Enter Db password: ")
        db_secret, created = DbCredentials.objects.get_or_create(name="postgres")
        db_secret.description = "Postgres Secrets"
        db_secret.user_name = db_username
        db_secret.password = db_pwd
        db_secret.save()

        print("Done")
