from django.urls import path

from webapp.views import LandingView

urlpatterns = [
    path("", LandingView.as_view(), name="landing")
]