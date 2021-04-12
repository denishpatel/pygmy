from engine.models import AllEc2InstanceTypes, AllRdsInstanceTypes
from engine.aws_wrapper import AWSData


def update_all_ec2_instances_types_db(**kwargs):
    try:
        all_instances = AWSData().describe_ec2_instance_types(**kwargs)
        if AllEc2InstanceTypes.objects.count() != len(all_instances):
            for instance in all_instances:
                try:
                    inst = AllEc2InstanceTypes.objects.get(instance_type=instance["InstanceType"])
                except AllEc2InstanceTypes.DoesNotExist:
                    aeit = AllEc2InstanceTypes()
                    aeit.instance_type = instance.get("InstanceType")
                    aeit.supported_usage_classes = instance.get("SupportedUsageClasses", {})
                    aeit.virtual_cpu_info = instance.get("VCpuInfo", {})
                    aeit.memory_info = instance.get("MemoryInfo", {})
                    aeit.storage_info = instance.get("InstanceStorageInfo", {})
                    aeit.ebs_info = instance.get("EbsInfo", {})
                    aeit.network_info = instance.get("NetworkInfo", {})
                    aeit.current_generation = instance.get("CurrentGeneration", True)
                    aeit.hibernation_supported = instance.get("HibernationSupported", True)
                    aeit.burstable_performance_supported = instance.get("BurstablePerformanceSupported", True)
                    aeit.save()
    except Exception as e:
        print(str(e))
        print(instance)
        return


def update_all_rds_instance_types_db():
    try:
        all_instances = AWSData().describe_rds_instance_types()
        if AllRdsInstanceTypes.objects.count() != len(all_instances):
            for instance in all_instances:
                try:
                    inst = AllRdsInstanceTypes.objects.get(instance_type=instance["DBInstanceClass"],
                                                           engine=instance["Engine"],
                                                           engine_version= instance["EngineVersion"])
                except AllRdsInstanceTypes.DoesNotExist:
                    arit = AllRdsInstanceTypes()
                    arit.instance_type = instance["DBInstanceClass"]
                    arit.engine = instance["Engine"]
                    arit.engine_version = instance["EngineVersion"]
                    arit.support_storage_encryption = instance["SupportsStorageEncryption"]
                    arit.multi_az_capable = instance["MultiAZCapable"]
                    arit.read_replica_capable = instance.get("ReadReplicaCapable", False)
                    arit.storage_type = instance.get("StorageType", "")
                    arit.support_iops = instance.get("SupportsIops", False)
                    arit.min_storage_size = instance["MinStorageSize"]
                    arit.max_storage_size = instance["MaxStorageSize"]
                    arit.support_storage_auto_scaling = instance["SupportsStorageAutoscaling"]
                    arit.save()
    except Exception as e:
        print(str(e))
        # print(instance)
        return


def update_ec2_data():
    all_instances = AWSData().describe_ec2_instances()
    # for db in all_instances:
    #     dbInfo = DBInfo
    pass
