import logging
from rest_framework import generics
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView
from rest_framework.response import Response
from engine.models import Rules, ClusterInfo, ExceptionData, Ec2DbInfo, ClusterManagement, DNSData
from engine.rules.rules_helper import RuleHelper
from engine.rules.cronutils import CronUtil
from drf_yasg2.utils import swagger_auto_schema
from webapp.serializers import RuleSerializer, ExceptionDataSerializer, ClusterSerializer, RuleCreateSerializer, \
    ExceptionCreateSerializer, Ec2DbInfoSerializer, DNSDataSerializer, ClusterManagementSerializer, ToggleClusterSerializer
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveUpdateDestroyAPIView, ListCreateAPIView, UpdateAPIView
from distutils.util import strtobool
from django.db import DatabaseError
from django.db import transaction
logger = logging.getLogger(__name__)


class CreateRuleAPIView(APIView):
    """
    Get or create rules
    """
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser]

    @swagger_auto_schema(tags=["Rules"], responses={200: RuleSerializer(many=True)})
    def get(self, request):
        return Response(RuleSerializer(Rules.objects.all(), many=True).data)

    @swagger_auto_schema(tags=["Rules"], request_body=RuleCreateSerializer(), responses={200: '{"success": True}'})
    def post(self, request, format=None):
        result = dict()
        try:
            name = request.data.get("name", None)
            typeTime = request.data.get("typeTime", "daily")
            cluster_id = request.data.get("cluster_id", None)
            cluster_obj = ClusterInfo.objects.get(id=cluster_id)
            action = request.data.get("action", None)
            if name and cluster_id and action and typeTime:
                # Scale down Rule
                RuleHelper.add_rule_db(request.data)
                result.update({"success": True})
            else:
                raise Exception("Bad Data!")
        except ClusterInfo.DoesNotExist:
            logger.error("ClusterInfo with id {} not found!".format(cluster_id))
            result.update({"error": "Invalid cluster ID"})
        except Exception as e:
            print(str(e))
            logger.exception(e)
            result.update({"error": "missing parameter", "data": str(e)})
        return Response(result)


class EditRuleAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser]

    @swagger_auto_schema(tags=["Rules"], request_body=RuleCreateSerializer(), responses={200: '{"success": True}'})
    def put(self, request, id, format=None):
        result = dict()
        try:
            rule = Rules.objects.get(id=id)
            name = request.data.get("name", None)
            typeTime = request.data.get("typeTime", "daily")
            cluster = request.data.get("cluster_id", None)
            action = request.data.get("action", None)
            if name and cluster and action and typeTime:
                # Scale down Rule
                RuleHelper.add_rule_db(request.data, rule)
                result.update({"success": True})
            else:
                raise Exception
        except Rules.DoesNotExist:
            result = {"not_found": "not found"}
        except Exception as e:
            print(str(e))
            result.update({"error": "missing parameter", "data": request.POST})
        return Response(result)

    @swagger_auto_schema(tags=["Rules"])
    def delete(self, request, id):
        rule = Rules.objects.get(id=id)
        CronUtil.delete_cron(rule)
        all_child_rules = rule.child_rule.all()
        for child_rule in all_child_rules:
            CronUtil.delete_cron(child_rule)
            child_rule.delete()
        rule.delete()
        return Response({"success": True})


class ClusterAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    queryset = ClusterInfo.objects.all()
    serializer_class = ClusterSerializer

    @swagger_auto_schema(tags=["Cluster"])
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


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

    @swagger_auto_schema(tags=["Exceptions"], request_body=ExceptionCreateSerializer(), responses={200: '{"success": True}'})
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
            logger.error(e)
        return Response(dict({"success": True}))

    @swagger_auto_schema(tags=["Exceptions"], responses={200: ExceptionDataSerializer(many=True)})
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

    @swagger_auto_schema(tags=["Exceptions"], request_body=ExceptionCreateSerializer(),
                         responses={200: '{"status": "Success"}'})
    def put(self, request, id):
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
                        exc.clusters = list({v['id']: v for v in exc.clusters + clist}.values())
                    exc.save()
                return Response({"status": "Success"})
        except Exception as e:
            logger.error(e)
            return Response({"status": "Failed"}, status=500)

    @swagger_auto_schema(operation_description="partial_update description override", tags=["Exceptions"])
    def delete(self, request, id, **kwargs):
        exc_date = ExceptionData.objects.get(id=id)
        exc_date.delete()
        return Response({"success": True})


class ListInstances(ListAPIView):
    """
    List all db instances
    """
    authentication_classes = []
    permission_classes = []
    queryset = Ec2DbInfo.objects.all()
    serializer_class = Ec2DbInfoSerializer


class CreateDNSEntry(ListCreateAPIView):
    """
    Create DNS entry
    """
    authentication_classes = []
    permission_classes = []
    serializer_class = DNSDataSerializer

    def get_queryset(self):
        return DNSData.objects.all()


class CreateClusterManagement(ListCreateAPIView):
    """
    Create Cluster Management
    """
    queryset = ClusterManagement.objects.all()
    authentication_classes = []
    permission_classes = []
    serializer_class = ClusterManagementSerializer

    @swagger_auto_schema(operation_summary="Get all Cluster Management Data", tags=["Cluster Management"])
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Create Cluster Management Rule", tags=["Cluster Management"])
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class EditClusterManagement(RetrieveUpdateDestroyAPIView):
    """
    Update Cluster Management
    """
    queryset = ClusterManagement.objects.all()
    authentication_classes = []
    permission_classes = []
    serializer_class = ClusterManagementSerializer


class ToggleCluster(UpdateAPIView):
    """
    Pause or Resume Cluster Scaling
    """
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser]
    serializer_class = ToggleClusterSerializer

    @swagger_auto_schema(operation_summary="Toggle Pygmy Management", tags=["Cluster"], request_body=ToggleClusterSerializer(), responses={200: '{"success": True}'})
    @transaction.atomic()
    def put(self, request, name):
        try:
            enable_cluster = bool(strtobool(request.data.get("enabled", None)))
        except Exception as e:
            result = {"Error": f"Invalid boolean used for enabled field: ({request.data.get('enabled', None)})"}
            return Response(result)

        try:
            cluster = ClusterInfo.objects.select_for_update(nowait=True).get(name=name)
            if cluster.enabled is True and enable_cluster is True:
                result = {"Success": "Cluster was already enabled"}
            elif cluster.enabled is False and enable_cluster is False:
                result = {"Success": "Cluster was already disabled"}
            elif cluster.enabled is True:
                cluster.enabled = False
                cluster.save()
                result = {"Success": "Cluster disabled"}
            else:
                cluster.enabled = True
                cluster.save()
                result = {"Success": "Cluster enabled"}
        except ClusterInfo.DoesNotExist:
            result = {"Error": "Cluster not found"}
        except DatabaseError as e:
            result = {"Error": f"Cluster is being resized"}
        except Exception as e:
            logger.error(f"Generic exception pausing or resuming cluster: {e}")
            result = {"Error": "missing parameter", "data": request.POST}
        return Response(result)
