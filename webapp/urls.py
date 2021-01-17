from django.urls import path

from webapp.views import LandingView, SecretsView

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("secrets", SecretsView.as_view(), name="secrets")
]