from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


def getClusterName():
    return "Cluster " + str(ClusterInfo.objects.all().count() + 1)


def getRuleName():
    return "Rule " + str(Rules.objects.all().count() + 1)


EC2 = "EC2"
RDS = "RDS"
SCALE_DOWN = "SCALE_DOWN"
SCALE_UP = "SCALE_UP"

CLUSTER_TYPES = (
    (EC2, "EC2"),
    (RDS, "RDS")
)

RuleType = (
    (SCALE_DOWN, "SCALE_DOWN"),
    (SCALE_UP, "SCALE_UP")
)


class ClusterInfo(models.Model):
    name = models.CharField(max_length=100, default=getClusterName)
    primaryNodeIp = models.CharField(max_length=100)
    type = models.CharField(choices=CLUSTER_TYPES, max_length=30)


class DbCredentials(models.Model):
    name = models.CharField(max_length=100)
    user_name = models.CharField(max_length=255)
    password = models.CharField(max_length=255)


class Ec2DbInfo(models.Model):
    # instance = models.OneToOneField(AllEc2InstancesData, on_delete=models.CASCADE, related_name="db_info")
    instance_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    instance_id = models.CharField(max_length=255)
    instance_object = GenericForeignKey('instance_type', 'instance_id')
    isPrimary = models.BooleanField(default=False)
    cluster = models.ForeignKey(ClusterInfo, on_delete=models.DO_NOTHING, null=True)
    dbName = models.CharField(max_length=255)
    isConnected = models.BooleanField(default=False)
    lastUpdated = models.DateTimeField(auto_now=True)
    type = models.CharField(choices=CLUSTER_TYPES, max_length=30)


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


class AllEc2InstancesData(models.Model):
    instanceId = models.CharField(max_length=255, null=False, primary_key=True)
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
    dbInfo = GenericRelation(Ec2DbInfo, related_query_name='ec2')


class RdsInstances(models.Model):
    dbInstanceIdentifier = models.CharField(max_length=255, primary_key=True)
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
    dbInfo = GenericRelation(Ec2DbInfo, related_query_name='rds')


class InstanceStateInfo(models.Model):
    instance_type = models.CharField(max_length=100)
    instance_id = models.CharField(max_length=100)
    last_type = models.CharField(max_length=100)
    changed_to = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_created=True)


class Rules(models.Model):
    name = models.CharField(max_length=100, default=getRuleName)
    cluster = models.ForeignKey(ClusterInfo, on_delete=models.CASCADE)
    rule = models.JSONField()
    action = models.CharField(choices=RuleType, max_length=100)
    action_arg = models.CharField(max_length=255, null=True)
    status = models.BooleanField(default=False, null=True)
    run_at = models.CharField(max_length=100, null=False)
    err_msg = models.CharField(max_length=255, null=True)
    last_run = models.DateTimeField(auto_created=True, null=True)
