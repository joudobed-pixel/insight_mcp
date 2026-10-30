from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("branches", views.BranchViewSet, basename="branch")
router.register("surveys", views.SurveyViewSet, basename="survey")

urlpatterns = [
    # HTML pages
    path("", views.dashboard, name="dashboard"),
    path("compare/", views.compare, name="compare"),
    path("capabilities/", views.capabilities, name="capabilities"),
    # REST API
    path("api/capabilities/", views.api_capabilities, name="api-capabilities"),
    path("api/analyze/", views.api_analyze, name="api-analyze"),
    path("api/compare/", views.api_compare, name="api-compare"),
    path("api/", include(router.urls)),
]
