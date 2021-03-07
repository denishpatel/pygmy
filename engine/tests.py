from django.test import TestCase
from engine.aws_wrapper import AWSData
from engine.models import AllEc2InstanceTypes, AllEc2InstancesData, RdsInstances
from webapp.models import Settings


class AllEc2InstanceTypesTest(TestCase):
    def setUp(self):
        ad = AWSData()
        all_instances = ad.describe_ec2_instance_types()
        for instance in all_instances:
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

        # populate settings data
        syncSettings = {
            "ec2": "Sync EC2 Data",
            "rds": "Sync RDS Data",
            "logs": "Sync Log Data"
        }
        for key, value in syncSettings.items():
            try:
                Settings.objects.get(name=key)
            except Settings.DoesNotExist:
                setting = Settings()
                setting.name = key
                setting.last_sync = None
                setting.description = value
                setting.save()

        # for testing the ec2 instances data
        ad.describe_ec2_instances()

        ad.describe_rds_instances()

    def test_ec2_instance_types(self):
        """
        test if instance types are stored
        """
        ec2_small_instance = AllEc2InstanceTypes.objects.get(instance_type="t2.small")
        self.assertIsNotNone(ec2_small_instance)
        ec2_small_instance = AllEc2InstanceTypes.objects.get(instance_type="t2.xlarge")
        self.assertIsNotNone(ec2_small_instance)

    def test_ec2_instance_data(self):
        """
        Test if ec2 data is stored
        """
        all_data_count = AllEc2InstancesData.objects.count()
        self.assertNotEqual(all_data_count, 0)

    def test_rds_clusters_are_discoverable(self):
        """
        Info about the test
        """
        all_rds_instances = RdsInstances.objects.all()
        print(all_rds_instances)
        self.assertGreater(len(all_rds_instances),0)
