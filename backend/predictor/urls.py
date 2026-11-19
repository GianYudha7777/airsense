from django.urls import path
from . import views
from . import ai_views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("metrics/", views.metrics, name="metrics"),
    path("predict/", views.predict, name="predict"),
    path(
    "ai/explain/",
    ai_views.explain_chart,
    name="ai-explain-chart"
),
]
