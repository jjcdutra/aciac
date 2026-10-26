from django.urls import path

from . import views

app_name = "associados"

urlpatterns = [
    path("cadastro/", views.cadastro, name="cadastro"),
    path("entrar/", views.LoginView.as_view(), name="login"),
    path("sair/", views.LogoutView.as_view(), name="logout"),
    path("painel/", views.painel, name="painel"),
    path("perfil/", views.perfil, name="perfil"),
    path(
        "recuperar-senha/",
        views.PasswordResetView.as_view(),
        name="recuperar_senha",
    ),
    path(
        "recuperar-senha/enviado/",
        views.PasswordResetDoneView.as_view(),
        name="recuperar_senha_enviado",
    ),
    path(
        "recuperar-senha/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "recuperar-senha/completado/",
        views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
