from django.urls import path
from .views import PresaleAPIView

app_name = 'presale'

urlpatterns = [
    path('api/presale/', PresaleAPIView.as_view(), name='presale_api'),
]
