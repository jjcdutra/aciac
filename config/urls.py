from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = f"{settings.ASSOCIACAO['NOME']} — Administração"
admin.site.site_title = f"{settings.ASSOCIACAO['NOME']} · Admin"
admin.site.index_title = "Painel administrativo"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("associados/", include("apps.associados.urls")),
    path("consultas/", include("apps.consultas.urls")),
    path("solicitacoes/", include("apps.solicitacoes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
