import json

from rest_framework import serializers, generics, filters
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from engine.models import Rules, ClusterInfo, ExceptionData
from engine.utils import RuleUtils, delete_cron


class CreateRuleAPIView(APIView):
    """
    Rule for EC2 DAILY:
    {
        "name": "EC 2 Cluster Rule DAILY",
        "typeTime": "DAILY",
        "dailyTime": "21:00",
        "cluster_id": 1,
        "action": "SCALE_DOWN",
        "ec2_type": "t2.nano",

        "enableReplicationLag": "on",
        "selectReplicationLagOp": "equal",
        "replicationLag": "12",

        "enableCheckConnection": "on",
        "selectCheckConnectionOp":"greater",
        "checkConnection": "12",

        "enableAverageLoad": "on",
        "selectAverageLoadOp": "less",
        "averageLoad": "32",

        "enableRetry": "on",
        "retryAfter: "15",
        "retryMax": "3",

        "enableReverse": "on",
        "reverse_action": "SCALE_UP",
        "reverseDailyTime": "06:00"
    },

    Rule for RDS with CRON settings:
    {
        "name": "RDS Cluster Rule CRON",
        "typeTime": "CRON",
        "cronTime": "* */21 * * *",

        "cluster_id": 2,
        "action": "SCALE_DOWN",
        "rds_type": "db.t2.small",

        "enableReplicationLag": "on",
        "selectReplicationLagOp": "equal",
        "replicationLag": "12",

        "enableCheckConnection": "on",
        "selectCheckConnectionOp":"greater",
        "checkConnection": "12",

        "enableAverageLoad": "on",
        "selectAverageLoadOp": "less",
        "averageLoad": "32",

        "enableRetry": "on",
        "retryAfter: "15",
        "retryMax": "3",

        "enableReverse": "on",
        "reverse_action": "SCALE_UP",
        "reverseCronTime": "* */21 * * *"
    }
    """
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser]

    def get(self, request):
        return Response(RuleSerializer(Rules.objects.all(), many=True).data)

    def post(self, request, format=None):
        result = dict()
        try:
            name = request.data.get("name", None)
            typeTime = request.data.get("typeTime", "daily")
            cluster = request.data.get("cluster_id", None)
            action = request.data.get("action", None)
            if name and cluster and action and typeTime:
                # Scale down Rule
                RuleUtils.add_rule_db(request.data)
                result.update({"success": True})
            else:
                raise Exception
        except Exception as e:
            print(str(e))
            result.update({"error": "missing parameter", "data": request.POST})
        return Response(result)


class EditRuleAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser]

    def post(self, request, id, format=None):
        result = dict()
        try:
            rule = Rules.objects.get(id=id)
            name = request.data.get("name", None)
            typeTime = request.data.get("typeTime", "daily")
            cluster = request.data.get("cluster_id", None)
            action = request.data.get("action", None)
            if name and cluster and action and typeTime:
                # Scale down Rule
                RuleUtils.add_rule_db(rule, request.data)
                result.update({"success": True})
            else:
                raise Exception
        except Rules.DoesNotExist:
            result = {"not_found": "not found"}
        except Exception as e:
            print(str(e))
            result.update({"error": "missing parameter", "data": request.POST})
        return Response(result)

    def delete(self, request, id):
        rule = Rules.objects.get(id=id)
        delete_cron(rule)
        rule.delete()
        return Response({"success": True})


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rules
        fields = ['id', 'name', 'cluster', 'action', 'rule', 'run_at', 'action']


class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClusterInfo
        fields = ['id', 'name', 'primaryNodeIp', 'type']


class ExceptionDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExceptionData
        fields = ['id', 'exception_date', 'clusters', 'added_on', 'updated_on']


class ClusterAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    queryset = ClusterInfo.objects.all()
    serializer_class = ClusterSerializer


class ExceptionApiView(APIView):
    """
    Request: {
        "dates": "2021-04-06, 2021-04-03",
        "clusterIds": [2]
    }
    """
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser]

    def post(self, request):
        dates = request.data.get("dates", None)
        clusters = request.data.get("clusterIds", None)
        try:
            if dates:
                clustersList = ClusterInfo.objects.filter(id__in=clusters)
                datesList = dates.split(",")
                for date in datesList:
                    exc, created = ExceptionData.objects.get_or_create(exception_date=date.strip(' '))
                    clist = list({"id": d.id, "value": d.clusterName} for d in clustersList)
                    if created:
                        exc.clusters = clist
                    else:
                        exc.clusters = list({v['id']: v for v in exc.clusters + clist}.values())
                    exc.save()
                return Response(dict({"success": True}))
        except Exception as e:
            print(e)
        return Response(dict({"success": True}))

    def get(self, request):
        return Response(ExceptionDataSerializer(ExceptionData.objects.all(), many=True).data)


class ExceptionEditApiView(APIView):
    """
    it override existing exception date data
    Request: {
        "dates": "2021-04-06, 2021-04-03",
        "clusterIds": [2]
    }
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request, id):
        dates = request.data.get("dates")
        clusters = request.data.get("clusterIds")
        try:
            current_exec = ExceptionData.objects.get(id=id)
            if dates:
                clustersList = ClusterInfo.objects.filter(id__in=clusters)
                clist = list({"id": d.id, "value": d.clusterName} for d in clustersList)
                datesList = dates.split(",")
                for date in datesList:
                    exc, created = ExceptionData.objects.get_or_create(exception_date=date.strip(' '))
                    if date == str(current_exec.exception_date):
                        exc.clusters = clist
                    else:
                        exc.clusters = list({v['id']:v for v in exc.clusters + clist}.values())
                    exc.save()
                return Response({"status": "Success"})
        except Exception as e:
            return Response({"status": "Failed"}, status=500)

    def delete(self, request, id, **kwargs):
        exc_date = ExceptionData.objects.get(id=id)
        exc_date.delete()
        return Response({"success": True})
