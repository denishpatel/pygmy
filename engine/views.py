from engine.models import AllEc2InstanceTypes
from engine.aws_wrapper import AWSData


def update_all_ec2_instances_db():
    try:
        all_instances = AWSData().describe_ec2_instance_types()
        if AllEc2InstanceTypes.objects.count() != len(all_instances):
            for instance in all_instances:
                try:
                    inst = AllEc2InstanceTypes.objects.get(instance_type=instance["InstanceType"])
                except AllEc2InstanceTypes.DoesNotExist:
                    aeit = AllEc2InstanceTypes()
                    aeit.instance_type = instance["InstanceType"]
                    aeit.supported_usage_classes = instance["SupportedUsageClasses"]
                    aeit.virtual_cpu_info = instance["VCpuInfo"]
                    aeit.memory_info = instance.get("MemoryInfo", {})
                    aeit.storage_info = instance.get("InstanceStorageInfo", {})
                    aeit.ebs_info = instance.get("EbsInfo", {})
                    aeit.network_info = instance["NetworkInfo"]
                    aeit.current_generation = instance["CurrentGeneration"]
                    aeit.hibernation_supported = instance["HibernationSupported"]
                    aeit.burstable_performance_supported = instance["BurstablePerformanceSupported"]
                    aeit.save()
    except Exception as e:
        print(str(e))
        print(instance)
        return
