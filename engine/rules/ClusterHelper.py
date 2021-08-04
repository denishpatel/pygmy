import json
from django.db.models import F

from engine.models import ClusterInfo


class ClusterHelper:

    @classmethod
    def get_cluster_list(cls):
        return cls.get_selection_list(ClusterInfo.objects.all(), "type", "name", "id")

    @staticmethod
    def get_selection_list(query, table_col, value_col, data_col):
        data = list(query.values(table_col).annotate(value=F(value_col), data=F(data_col)))
        return json.dumps(data)
