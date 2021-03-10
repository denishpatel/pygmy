from django.urls import path, re_path

from webapp.view.actions import ActionsView
from webapp.view.exceptions import ExceptionsView, ExceptionsCreateView, ExceptionsEditView
from webapp.view.rules import CreateRulesView, RulesView, EditRuleView
from webapp.view.settings import SettingsView, SettingsRefreshView
from webapp.views import LandingView, SecretsView, ClusterView, InstanceView, \
    ClusterEditView

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("secrets", SecretsView.as_view(), name="secrets"),
    path("rules", RulesView.as_view(), name="rules"),
    path("rules/create", CreateRulesView.as_view(), name="create_rule"),
    # path("rules/<int:id>", DeleteRulesView.as_view(), name="delete_rule"),
    path("rules/<int:id>/edit", EditRuleView.as_view(), name="edit_rule"),
    path("exceptions/", ExceptionsView.as_view(), name="exceptions"),
    path("exceptions/create", ExceptionsCreateView.as_view(), name="create_exception"),
    path("exceptions/<int:id>/edit", ExceptionsEditView.as_view(), name="edit_exception"),
    re_path(r'^cluster/(?P<id>\d+)/edit', ClusterEditView.as_view(), name="clusters_edit"),
    re_path(r'^cluster/(?P<id>\d+)/', ClusterView.as_view(), name="clusters"),
    path('instance/<str:cluster_type>/<str:id>/edit', InstanceView.as_view(), name="instance_edit"),
    path("settings", SettingsView.as_view(), name="settings"),
    path("settings/reload", SettingsRefreshView.as_view(), name="settings_reload"),
    path("actions", ActionsView.as_view(), name="action_list"),
]