from django.urls import path, re_path
from django.views.generic import TemplateView

from webapp.view.actions import ActionsView
from webapp.view.apis import ClusterAPIView, ExceptionApiView, ExceptionEditApiView
from webapp.view.exceptions import ExceptionsView, ExceptionsCreateView, ExceptionsEditView
from webapp.view.rules import CreateRulesView, RulesView, EditRuleView
from webapp.view.apis import CreateRuleAPIView, EditRuleAPIView
from webapp.view.settings import SettingsView, SettingsRefreshView
from webapp.views import LandingView, SecretsView, ClusterView, InstanceView, ClusterEditView, SecretsEditView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("login", auth_views.LoginView.as_view(template_name='login.html'), name="login"),
    path("logout", auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),
    path("edit", auth_views.PasswordChangeView.as_view(template_name="edit.html"), name='edit'),
    path("edit/done", TemplateView.as_view(template_name="password_change_done.html"), name='password_change_done'),
    path("secrets", SecretsView.as_view(), name="secrets"),
    path("secrets/<int:id>", SecretsEditView.as_view(), name="edit_secrets"),
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

    path("v1/api/rules", CreateRuleAPIView.as_view(), name="create_rule_api"),
    path("v1/api/rules/<int:id>", EditRuleAPIView.as_view(), name="edit_rule_api"),
    path("v1/api/clusters", ClusterAPIView.as_view(), name="create_rule_api"),
    path("v1/api/exceptions", ExceptionApiView.as_view(), name="create_rule_api"),
    path("v1/api/exceptions/<int:id>", ExceptionEditApiView.as_view(), name="create_rule_api"),
]