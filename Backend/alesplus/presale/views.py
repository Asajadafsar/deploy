from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import PresaleTransaction
from django.core.mail import send_mail

class PresaleAPIView(APIView):

    @swagger_auto_schema(
        operation_description="Create a presale transaction",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_name': openapi.Schema(type=openapi.TYPE_STRING),
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="Optional phone number"),
                'payment_network': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Payment network for deposit (TRC20 or BEP20)",
                    enum=["TRC20", "BEP20"]
                ),
                'user_wallet_address': openapi.Schema(type=openapi.TYPE_STRING),
                'user_wallet_network': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Network of user's wallet (TRC20 or BEP20)",
                    enum=["TRC20", "BEP20"]
                ),
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
        user_wallet_address = request.data.get('user_wallet_address')
        user_wallet_network = request.data.get('user_wallet_network')
        amount_usdt = request.data.get('amount_usdt')
        transaction_code = request.data.get('transaction_code')

        if not all([user_name, email, payment_network, user_wallet_address, user_wallet_network, amount_usdt, transaction_code]):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        if payment_network not in ['TRC20', 'BEP20'] or user_wallet_network not in ['TRC20', 'BEP20']:
            return Response({"error": "Invalid network choice"}, status=status.HTTP_400_BAD_REQUEST)

        token_quantity = float(amount_usdt) / 0.10

        # ذخیره تراکنش
        presale_transaction = PresaleTransaction.objects.create(
            user_name=user_name,
            email=email,
            phone_number=phone_number,
            payment_network=payment_network,
            user_wallet_address=user_wallet_address,
            user_wallet_network=user_wallet_network,
            amount_usdt=amount_usdt,
            token_quantity=token_quantity,
            transaction_code=transaction_code
        )

        try:
            send_mail(
                subject='✅ Alecplus Token Presale Confirmation',
                message=(
                    f"Dear {user_name},\n\n"
                    f"Thank you for participating in the Alecplus token presale.\n\n"
                    f"Here are your transaction details:\n"
                    f"- Payment Amount (USDT): {amount_usdt}\n"
                    f"- Token Quantity: {token_quantity}\n"
                    f"- Deposit Network: {payment_network}\n"
                    f"- Your Wallet: {user_wallet_address} ({user_wallet_network})\n"
                    f"- Transaction Code: {transaction_code}\n\n"
                    f"Once our platform is fully launched, "
                    f"your purchased tokens will be credited to your account.\n\n"
                    f"Stay tuned for updates and thank you for trusting Alecplus!\n\n"
                    f"Best regards,\n"
                    f"Alecplus Team"
                ),
                from_email='notification@alecplus.tech',
                recipient_list=[email],
                fail_silently=False,
            )

            send_mail(
                subject='🔔 New Presale Registration',
                message=(
                    f"Hello Alecplus Admin,\n\n"
                    f"A new user has registered for the token presale. Here are the details:\n\n"
                    f"- Name: {user_name}\n"
                    f"- Email: {email}\n"
                    f"- Phone: {phone_number}\n"
                    f"- Payment Amount (USDT): {amount_usdt}\n"
                    f"- Token Quantity: {token_quantity}\n"
                    f"- Deposit Network: {payment_network}\n"
                    f"- User Wallet: {user_wallet_address} ({user_wallet_network})\n"
                    f"- Transaction Code: {transaction_code}\n\n"
                    f"Please verify and process the transaction.\n\n"
                    f"Regards,\n"
                    f"Alecplus System"
                ),
                from_email='notification@alecplus.tech',
                recipient_list=['info@alecplus.tech'],
                fail_silently=False,
            )

        except Exception as e:
            return Response({
                "error": "Transaction saved but failed to send confirmation email.",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "transaction_id": presale_transaction.id,
            "token_quantity": presale_transaction.token_quantity,
            "transaction_code": presale_transaction.transaction_code,
        }, status=status.HTTP_201_CREATED)
