from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger schema setup
schema_view = get_schema_view(
    openapi.Info(
        title="AlecPlus API",
        default_version='v1',
        description="Full API documentation for AlecPlus system",
        terms_of_service="https://alecplus.tech/terms/",
        contact=openapi.Contact(email="support@alecplus.tech"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # ✅ Swagger UI as root (https://api.alecplus.tech/)
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='root-swagger-ui'),

    # ✅ Optional: JSON and YAML endpoints
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    # ✅ Optional: Redoc UI (https://api.alecplus.tech/redoc/)
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # ✅ Your API routes (e.g., https://api.alecplus.tech/contact)
    path('', include('user_view.urls')),

    # Add presale API route
    path('presale/', include('presale.urls')),  # Add this line
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
