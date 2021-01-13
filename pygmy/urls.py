"""pygmy URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URL conf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from rest_framework import permissions
from drf_yasg2.views import get_schema_view
from drf_yasg2 import openapi
from users.views import Logout, Profile, ObtainAuthToken


schema_view = get_schema_view(
   openapi.Info(
      title="PYGMY API",
      default_version='v1',
      description="Swagger document to check out API documentation",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="denish.j.patel@gmail.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

admin.site.site_header = 'PygMy Administration'           # default: "Django Administration"
admin.site.index_title = 'PygMy Admin Area'               # default: "Site administration"
admin.site.site_title = 'PygMy Admin'                     # default: "Django site admin"


urlpatterns = [
    path('pygmyadmin/', admin.site.urls),

    # Swagger APIs
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # user APIs
    path('api/login/', ObtainAuthToken.as_view()),
    path('api/logout/', Logout.as_view()),
    path('api/profile/', Profile.as_view()),
]
