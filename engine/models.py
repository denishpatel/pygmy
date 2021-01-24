from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class DbCredentials(models.Model):
    name = models.CharField(max_length=100)
    user_name = models.CharField(max_length=255)
    password = models.CharField(max_length=255)


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


class AllEc2InstancesData(models.Model):
    instanceId = models.CharField(max_length=255, null=False, primary_key=True)
    name = models.CharField(max_length=255)
    instanceType = models.CharField(max_length=255, null=False)
    keyName = models.CharField(max_length=255, null=False)
    launchTime = models.DateTimeField()
    availabilityZone= models.CharField(max_length=255)
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


def getClusterName():
    return "Cluster " + str(ClusterInfo.objects.all().count() + 1)

EC2 = "EC2"
RDS = "RDS"

CLUSTER_TYPES = (
    (EC2, "EC2"),
    (RDS, "RDS")
)


class ClusterInfo(models.Model):
    name = models.CharField(max_length=100, default=getClusterName)
    primaryNodeIp = models.CharField(max_length=100)
    type = models.CharField(choices=CLUSTER_TYPES, max_length=30)


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


class Ec2DbInfo(models.Model):
    # instance = models.OneToOneField(AllEc2InstancesData, on_delete=models.CASCADE, related_name="db_info")
    instance = models.CharField(max_length=255)
    isPrimary = models.BooleanField(default=False)
    cluster = models.ForeignKey(ClusterInfo, on_delete=models.DO_NOTHING, null=True)
    dbName = models.CharField(max_length=255)
    isConnected = models.BooleanField(default=False)
    lastUpdated = models.DateTimeField(auto_now=True)
    type = models.CharField(choices=CLUSTER_TYPES, max_length=30)
