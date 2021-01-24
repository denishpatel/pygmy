from django.urls import path, re_path

from webapp.views import LandingView, SecretsView, ClusterView

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("secrets", SecretsView.as_view(), name="secrets"),
    re_path(r'^cluster/(?P<id>\d+)/', ClusterView.as_view(), name="clusters"),
]