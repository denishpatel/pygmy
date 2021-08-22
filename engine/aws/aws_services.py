import time
import boto3
import datetime
from django.conf import settings
from django.utils import timezone
from webapp.models import Settings, AWS_REGION
from webapp.models import Settings as SettingsModal
from engine.models import ClusterInfo, DbCredentials


class AWSServices:
    ec2_client_region_dict = dict()
    rds_client_region_dict = dict()
    cloudwatch_client_region_dict = dict()
    SERVICE_TYPE = ""
    """
    Environment Variables to be set
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_REGION
    """

    def __init__(self):
        try:
            creds = DbCredentials.objects.get(name="aws")
            self.aws_session = boto3.Session(aws_access_key_id=cred.user_name, aws_secret_access_key=cred.password)
        except:
            self.aws_session = boto3.Session()
        self.ec2_client = self.aws_session.client('ec2', region_name=settings.DEFAULT_REGION)
        self.rds_client = self.aws_session.client('rds', region_name=settings.DEFAULT_REGION)
        for region in self.ec2_client.describe_regions()["Regions"]:
            region_name = region["RegionName"]
            self.ec2_client_region_dict[region_name] = self.aws_session.client('ec2', region_name=region_name)
            self.rds_client_region_dict[region_name] = self.aws_session.client('rds', region_name=region_name)
            self.cloudwatch_client_region_dict[region_name] = self.aws_session.client('cloudwatch',
                                                                                      region_name=region_name)

    @staticmethod
    def get_enabled_regions():
        regions = [setting.description for setting in Settings.objects.filter(type=AWS_REGION, value="True").all()]
        return regions

    def check_instance_status(self, instance_id):
        pass

    def check_instance_running(self, data):
        pass

    def get_tag_map(self, instance):
        pass

    def wait_till_status_up(self, instance):
        # TODO check streaming status after we confirm that its running.
        # TODO To be run on replica
        try:
            for i in range(0, 6):
                data = self.check_instance_status(instance)
                status = self.check_instance_running(data)
                if status:
                    return status
                time.sleep(20)
        except Exception as e:
            print(str(e))
            pass
        return None

    def update_last_sync_time(self):
        # Settings update
        setting = SettingsModal.objects.get(name__iexact=self.SERVICE_TYPE)
        setting.last_sync = timezone.now()
        setting.save()

    def get_cluster_name(self, tag_map):
        project = tag_map.get(settings.EC2_INSTANCE_PROJECT_TAG_KEY_NAME, None)
        environment = tag_map.get(settings.EC2_INSTANCE_ENV_TAG_KEY_NAME, None)
        cluster = tag_map.get(settings.EC2_INSTANCE_CLUSTER_TAG_KEY_NAME, None)
        print("Tag values project:{} environment:{} cluster:{}".format(project, environment, cluster))
        if project and environment and cluster:
            return "{}-{}-{}".format(project, environment, cluster)
        else:
            return None

    def get_or_create_cluster(self, instance, primary_node_ip, databaseName="postgres"):
        cluster, created = ClusterInfo.objects.get_or_create(primaryNodeIp=primary_node_ip, type=self.SERVICE_TYPE, databaseName=databaseName)
        if created:
            cluster_name = self.get_cluster_name(self.get_tag_map(instance))
            print("Cluster name ", cluster_name)
            if cluster_name:
                cluster.name = cluster_name
                cluster.save()
        return cluster

    def get_rds_cloudwatch_metrics(self):
        response = self.cloudwatch_client.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='CPUUtilization',
            Dimensions=[
                {
                    'Name': 'DBInstanceIdentifier',
                    'Value': 'postgres-replica'
                },
            ],
            StartTime=timezone.now() - datetime.timedelta(hours=1),
            EndTime=timezone.now(),
            Period=900,
            Statistics=[
                'Average',
            ]
        )
        return response
