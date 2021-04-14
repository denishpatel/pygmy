from rest_framework import serializers
from engine.models import Rules, ClusterInfo, ExceptionData, Ec2DbInfo


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rules
        fields = ['id', 'name', 'cluster', 'action', 'rule', 'run_at']


class RuleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=32)
    cluster_id = serializers.CharField(max_length=64)
    action = serializers.CharField(max_length=64)
    typeTime = serializers.ChoiceField(choices=["daily", "cron"])


class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClusterInfo
        fields = ['id', 'name', 'primaryNodeIp', 'type']


class ExceptionDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExceptionData
        fields = ['id', 'exception_date', 'clusters', 'added_on', 'updated_on']


class ExceptionCreateSerializer(serializers.Serializer):
    dates = serializers.JSONField(help_text="list of valid dates of format YYYY-MM-DD", default=list)
    clusterIds = serializers.JSONField(help_text="list of valid cluster ids", default=list)


class Ec2DbInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ec2DbInfo
        fields = ["instance_id", "instance_type", "isPrimary", "cluster"]
