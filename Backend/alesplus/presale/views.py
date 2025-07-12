from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from .models import PresaleTransaction
from drf_yasg import openapi

class PresaleAPIView(APIView):

    @swagger_auto_schema(
        operation_description="Create a presale transaction",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_name': openapi.Schema(type=openapi.TYPE_STRING),
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="Optional phone number"),
                'payment_network': openapi.Schema(type=openapi.TYPE_STRING, description="Payment network (TRC20 or BEP20)"),
                'wallet_address': openapi.Schema(type=openapi.TYPE_STRING),
                'amount_usdt': openapi.Schema(type=openapi.TYPE_NUMBER, description="Amount in USDT"),
                'transaction_code': openapi.Schema(type=openapi.TYPE_STRING, description="Transaction code entered by user")
            }
        ),
        responses={
            201: openapi.Response(
                description="Transaction created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'transaction_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'token_quantity': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'transaction_code': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                ),
            ),
            400: "Bad Request",
        }
    )
    def post(self, request):
        user_name = request.data.get('user_name')
        email = request.data.get('email')
        phone_number = request.data.get('phone_number', '')
        payment_network = request.data.get('payment_network')
        wallet_address = request.data.get('wallet_address')
        amount_usdt = request.data.get('amount_usdt')
        transaction_code = request.data.get('transaction_code')

        if not all([user_name, email, payment_network, wallet_address, amount_usdt, transaction_code]):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        token_quantity = float(amount_usdt) / 0.10

        presale_transaction = PresaleTransaction.objects.create(
            user_name=user_name,
            email=email,
            phone_number=phone_number,
            payment_network=payment_network,
            wallet_address=wallet_address,
            amount_usdt=amount_usdt,
            token_quantity=token_quantity,
            transaction_code=transaction_code
        )

        return Response({
            "transaction_id": presale_transaction.id,
            "token_quantity": presale_transaction.token_quantity,
            "transaction_code": presale_transaction.transaction_code,
        }, status=status.HTTP_201_CREATED)
