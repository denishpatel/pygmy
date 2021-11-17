from django.core.management import BaseCommand

from engine.models import Rules
from engine.utils import set_retry_cron


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('rule_id', nargs='+', type=int, help="Rule id to run. You can provide multiple "
                            "rule ids to run multiple rule")

    def handle(self, *args, **kwargs):
        for rid in kwargs['rule_id']:
            print("fetching Rule {}".format(rid))
            rule = Rules.objects.get(id=rid)
            set_retry_cron(rule)
