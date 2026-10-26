from django.urls import path

from . import views

app_name = "consultas"

urlpatterns = [
    path("", views.consulta, name="consulta"),
    path("ajax/", views.consulta_ajax, name="consulta_ajax"),
]
