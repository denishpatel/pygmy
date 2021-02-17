import json
from django.utils import timezone
from django.core.management import BaseCommand
from engine.aws_wrapper import AWSData
from engine.models import Rules, Ec2DbInfo, EC2, RDS


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('rule_id', nargs='+', type=int, help="Rule id to run. You can provide multiple "
                                                                     "rule ids to run multiple rule")

    def handle(self, *args, **kwargs):
        for rid in kwargs['rule_id']:
            try:
                aws = AWSData()
                rule_db = Rules.objects.get(id=rid)
                rule_json = json.loads(rule_db.rule)
                ec2_type = rule_json["ec2_type"]
                rds_type = rule_json["rds_type"]
                all_dbs = Ec2DbInfo.objects.filter(cluster=rule_db.cluster)
                for db in all_dbs:
                    if db.type == EC2 and not db.isPrimary:
                        aws.scale_ec2_instance(db.instance_id, ec2_type)
                    elif db.type == RDS and not db.isPrimary:
                        db_parameter = db.instance_object.dBParameterGroups[0]['DBParameterGroupName']
                        aws.scale_rds_instance(db.instance_id, rds_type, db_parameter)
                rule_db.status = True
                rule_db.err_msg = ""
            except Exception as e:
                rule_db.status = False
                rule_db.err_msg = e
                print("No rule found")
            finally:
                rule_db.last_run = timezone.now()
                rule_db.save()
            print("Rule has completed successfully")
