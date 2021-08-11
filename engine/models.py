from engine.utils import CryptoUtil
from django.db import models
from datetime import datetime
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation


def getClusterName():
    return "Cluster " + str(ClusterInfo.objects.count() + 1)


def getRuleName():
    return "Rule " + str(Rules.objects.count() + 1)


EC2 = "EC2"
RDS = "RDS"
SCALE_DOWN = "SCALE_DOWN"
SCALE_UP = "SCALE_UP"
DAILY = "DAILY"
CRON = "CRON"

CLUSTER_TYPES = (
    (EC2, "EC2"),
    (RDS, "RDS")
)

RuleType = (
    (SCALE_DOWN, "SCALE_DOWN"),
    (SCALE_UP, "SCALE_UP")
)

RunType = (
    (DAILY, "DAILY"),
    (CRON, "CRON")
)


class ClusterInfo(models.Model):
    name = models.CharField(max_length=100, default=getClusterName)
    primaryNodeIp = models.CharField(max_length=100)
    databaseName = models.CharField(max_length=255, default="postgres")
    type = models.CharField(choices=CLUSTER_TYPES, max_length=30)

    @property
    def clusterName(self):
        return "{}-({})".format(self.name, self.id)


class SecureField(models.CharField):

    def __init__(self, *args, **kwargs):
        self.crypto_util = CryptoUtil()
        super(SecureField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        return self.crypto_util.decode(value)

    def get_prep_value(self, value):
        if not value:
            return value
        if not isinstance(value, str):
            value = str(value)
        return self.crypto_util.encode(value)


class DbCredentials(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    user_name = models.CharField(max_length=255)
    password = SecureField(max_length=255)


class Ec2DbInfo(models.Model):
    instance_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    instance_id = models.CharField(max_length=255)
    instance_object = GenericForeignKey('instance_type', 'instance_id')
    isPrimary = models.BooleanField(default=False)
    cluster = models.ForeignKey(ClusterInfo, on_delete=models.DO_NOTHING, null=True, related_name="instance")
    dbName = models.CharField(max_length=255)
    isConnected = models.BooleanField(default=False)
    lastUpdated = models.DateTimeField(auto_now=True)
    type = models.CharField(choices=CLUSTER_TYPES, max_length=30)
    last_instance_type = models.CharField(max_length=255, null=True)


class AllEc2InstanceTypes(models.Model):
    """
    Simple DB to store all instances.
    We need to periodically update this info
    """
    instance_type = models.CharField(max_length=64, primary_key=True)
    supported_usage_classes = models.JSONField(default=list)
    virtual_cpu_info = models.JSONField(null=False, default=dict)
    memory_info = models.JSONField(null=False, default=dict)
    storage_info = models.JSONField(null=False, default=dict)
    ebs_info = models.JSONField(null=False, default=dict)
    network_info = models.JSONField(null=False, default=dict)
    current_generation = models.BooleanField(default=True)
    hibernation_supported = models.BooleanField(default=True)
    burstable_performance_supported = models.BooleanField(default=True)

    def save_instance_types(self, instance):
        self.instance_type = instance.get("InstanceType")
        self.supported_usage_classes = instance.get("SupportedUsageClasses", {})
        self.virtual_cpu_info = instance.get("VCpuInfo", {})
        self.memory_info = instance.get("MemoryInfo", {})
        self.storage_info = instance.get("InstanceStorageInfo", {})
        self.ebs_info = instance.get("EbsInfo", {})
        self.network_info = instance.get("NetworkInfo", {})
        self.current_generation = instance.get("CurrentGeneration", True)
        self.hibernation_supported = instance.get("HibernationSupported", True)
        self.burstable_performance_supported = instance.get("BurstablePerformanceSupported", True)
        self.save()


class AllRdsInstanceTypes(models.Model):
    """
    Simple DB to store all rds instances types.
    We need to periodically update this info
    """
    engine = models.CharField(max_length=24, default='postgres', null=False)
    engine_version = models.CharField(max_length=16, null=False)
    instance_type = models.CharField(max_length=64, primary_key=True)
    support_storage_encryption = models.BooleanField()
    multi_az_capable = models.BooleanField()
    read_replica_capable = models.BooleanField()
    storage_type = models.CharField(max_length=32, default="standard")
    support_iops = models.BooleanField()
    min_storage_size = models.IntegerField()
    max_storage_size = models.IntegerField()
    support_storage_auto_scaling = models.BooleanField()

    class Meta:
        unique_together = ['engine', 'engine_version', 'instance_type']
        index_together = ['engine', 'engine_version', 'instance_type']

    def save_instance_types(self, instance):
        self.instance_type = instance["DBInstanceClass"]
        self.engine = instance["Engine"]
        self.engine_version = instance["EngineVersion"]
        self.support_storage_encryption = instance["SupportsStorageEncryption"]
        self.multi_az_capable = instance["MultiAZCapable"]
        self.read_replica_capable = instance.get("ReadReplicaCapable", False)
        self.storage_type = instance.get("StorageType", "")
        self.support_iops = instance.get("SupportsIops", False)
        self.min_storage_size = instance["MinStorageSize"]
        self.max_storage_size = instance["MaxStorageSize"]
        self.support_storage_auto_scaling = instance["SupportsStorageAutoscaling"]
        self.save()


class AllEc2InstancesData(models.Model):
    instanceId = models.CharField(max_length=255, null=False, primary_key=True)
    region = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    instanceType = models.CharField(max_length=255, null=False)
    keyName = models.CharField(max_length=255, null=False)
    launchTime = models.DateTimeField()
    availabilityZone = models.CharField(max_length=255)
    privateDnsName = models.CharField(max_length=255)
    privateIpAddress = models.CharField(max_length=255)
    publicDnsName = models.CharField(max_length=255)
    publicIpAddress = models.CharField(max_length=255)
    state = models.JSONField()
    subnetId = models.CharField(max_length=255)
    vpcId = models.CharField(max_length=255)
    architecture = models.CharField(max_length=255)
    blockDeviceMapping = models.JSONField(encoder=DjangoJSONEncoder)
    ebsOptimized = models.CharField(max_length=255)
    securityGroups = models.JSONField()
    tags = models.JSONField()
    virtualizationType = models.CharField(max_length=255)
    cpuOptions = models.JSONField()
    lastUpdated = models.DateTimeField(auto_now=True)
    credentials = models.ForeignKey(DbCredentials, on_delete=models.SET_NULL, null=True)
    dbInfo = GenericRelation(Ec2DbInfo, object_id_field='instance_id', content_type_field='instance_type',
                             related_query_name='ec2')

    class Meta:
        unique_together = (('instanceId', 'region'),)


class RdsInstances(models.Model):
    dbInstanceIdentifier = models.CharField(max_length=255, primary_key=True)
    region = models.CharField(max_length=255)
    dbInstanceClass = models.CharField(max_length=255)
    dbName = models.CharField(max_length=255)
    engine = models.CharField(max_length=255)
    dbInstanceStatus = models.CharField(max_length=255)
    dbEndpoint = models.JSONField()
    dbStorage = models.CharField(max_length=200)
    dbVpcSecurityGroups = models.JSONField()
    masterUsername = models.CharField(max_length=255)
    preferredBackupWindow = models.CharField(max_length=255)
    availabilityZone = models.CharField(max_length=255)
    dBParameterGroups = models.JSONField()
    engineVersion = models.CharField(max_length=255)
    licenseModel = models.CharField(max_length=255)
    publiclyAccessible = models.BooleanField(default=False)
    tagList = models.JSONField()
    dbInfo = GenericRelation(Ec2DbInfo, object_id_field='instance_id', content_type_field='instance_type',
                             related_query_name='rds')

    class Meta:
        unique_together = (('dbInstanceIdentifier', 'region'),)


class InstanceStateInfo(models.Model):
    instance_type = models.CharField(max_length=100)
    instance_id = models.CharField(max_length=100)
    last_type = models.CharField(max_length=100)
    changed_to = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_created=True)


class Rules(models.Model):
    """
    Model to store the rules to be applied
    """
    name = models.CharField(max_length=100, default=getRuleName)
    cluster = models.ForeignKey(ClusterInfo, on_delete=models.CASCADE, related_name="rules")
    rule = models.JSONField()
    action = models.CharField(choices=RuleType, max_length=100)
    action_arg = models.CharField(max_length=255, null=True)
    status = models.BooleanField(default=False, null=True)
    run_type = models.CharField(choices=RunType, max_length=100)
    run_at = models.CharField(max_length=100, null=False)
    err_msg = models.CharField(max_length=255, null=True)
    last_run = models.DateTimeField(auto_created=True, null=True)
    parent_rule = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="child_rule")


class ActionLogs(models.Model):
    """
    Model to store all the action logs
    """
    rule = models.ForeignKey(Rules, on_delete=models.CASCADE)
    time = models.DateTimeField(auto_now_add=True, null=True)
    msg = models.CharField(max_length=255)
    extra_data = models.TextField(null=True)
    status = models.BooleanField(default=False)


def is_valid_date(data):
    try:
        if isinstance(data, str):
            data = datetime.strptime(data, "%Y-%m-%d")
        date = timezone.datetime.date(data)
        return True
    except ValueError:
        print("Invalid date : " + str(data))
        return False


class ExceptionData(models.Model):
    """
    All exception days will be stored here
    Before every rule is applied, data for
    that cluster is checked if there is an
    exception to it
    """
    exception_date = models.DateField(null=False, unique=True)
    clusters = models.JSONField(default=list)
    added_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)


class DNSData(models.Model):
    """
    All DNS data per cluster will be stored
    here. Data will be stored here using API
    """
    hosted_zone_name = models.CharField(max_length=64)
    dns_name = models.CharField(max_length=128)
    instance_id = models.OneToOneField(Ec2DbInfo, on_delete=models.CASCADE, related_name="dns_entry")


class ClusterManagement(models.Model):
    """
    All cluster management settings
    """
    avg_load = models.CharField(max_length=255)
    fallback_instances_scale_up = models.JSONField(null=True)
    fallback_instances_scale_down = models.JSONField(null=True)
    check_active_users = models.JSONField(null=True)
    cluster_id = models.OneToOneField(ClusterInfo, on_delete=models.CASCADE, related_name="load_management")
