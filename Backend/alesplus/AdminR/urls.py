from django.urls import path
from .views import getone_transaction, view_presale_transactions , update_transaction_status
from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path('transactions/', view_presale_transactions, name='view_presale_transactions'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('transactions/<int:transaction_id>/', getone_transaction, name='getone_transaction'),
    path('transactions/<int:transaction_id>/status/', update_transaction_status),
]
