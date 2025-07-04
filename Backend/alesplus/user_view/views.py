from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, parsers
from django.core.files.storage import default_storage
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Contact, PartnershipRequest, CustomUser, TokenPurchase, NETWORK_CHOICES, PARTNERSHIP_CHOICES
from decimal import Decimal
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, PasswordResetToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import TokenPurchase
from .constants import TOKEN_PRICE, MIN_TOKENS, NETWORK_CHOICES
from .models import LoginHistory
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny


#token jwt
class JWTUserMixin:
    def get_user_from_token(self, request):
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return None
        token = auth.split()[1]
        try:
            validated_token = JWTAuthentication().get_validated_token(token)
            user = JWTAuthentication().get_user(validated_token)
            return user
        except Exception:
            return None



#contact landing by swagger +
class ContactUsView(APIView):

    @swagger_auto_schema(
        operation_summary="Submit contact form",
        operation_description="Save contact information submitted by users from landing page.",
        request_body=openapi.Schema(
            title="Contact Request",
            type=openapi.TYPE_OBJECT,
            required=["first_name", "last_name", "phone_number", "email", "description"],
            properties={
                "first_name": openapi.Schema(type=openapi.TYPE_STRING, description="First name of the user"),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING, description="Last name of the user"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="User's phone number"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", description="User's email address"),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Message or inquiry from the user"),
            }
        ),
        responses={
            200: openapi.Response(
                description="Successfully submitted",
                examples={
                    "application/json": {
                        "message": "Contact information saved successfully!"
                    }
                }
            ),
            400: openapi.Response(
                description="Missing fields",
                examples={
                    "application/json": {
                        "error": "Required fields are missing!"
                    }
                }
            )
        }
    )
    def post(self, request):
        data = request.data
        required_fields = ['first_name', 'last_name', 'phone_number', 'email', 'description']
        if all(field in data for field in required_fields):
            Contact.objects.create(**{f: data[f] for f in required_fields})
            return Response({'message': 'Contact information saved successfully!'})
        return Response({'error': 'Required fields are missing!'}, status=400)
    



#APIView
class PartnershipRequestView(APIView):
    def post(self, request):
        data = request.data
        required_fields = ['first_name', 'last_name', 'email', 'phone_number', 'cooperation_type']
        if not all(field in data for field in required_fields):
            return Response({'error': 'Missing required fields!'}, status=400)
        if data['cooperation_type'] not in dict(PARTNERSHIP_CHOICES):
            return Response({'error': 'Invalid cooperation type!'}, status=400)
        data['other_description'] = data.get('other_description') if data['cooperation_type'] == 'other' else None
        PartnershipRequest.objects.create(**data)
        return Response({'message': 'Partnership request submitted successfully!'})






#--User Registration and Login--

#register & login by swagger +
class AccountView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    @swagger_auto_schema(
        operation_description="Signup a new user (use ?auth=signup in query)",
        manual_parameters=[
            openapi.Parameter(
                'auth',
                openapi.IN_QUERY,
                description="Specify 'signup' to register. Leave empty to login.",
                type=openapi.TYPE_STRING
            )
        ],
        request_body=openapi.Schema(
            title="Signup/Login Request",
            type=openapi.TYPE_OBJECT,
            required=["first_name", "last_name", "email", "password", "verification_code"],
            properties={
                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING),
                "verification_code": openapi.Schema(type=openapi.TYPE_STRING),
                "role": openapi.Schema(type=openapi.TYPE_STRING),
                "avatar": openapi.Schema(type=openapi.TYPE_FILE),
            }
        ),
        responses={200: "User registered or logged in successfully"}
    )
    def post(self, request):
        auth_type = request.query_params.get('auth')
        if auth_type == 'signup':
            return self.register(request)
        return self.login(request)

    def register(self, request):
        data = request.data
        required_fields = ['first_name', 'last_name', 'email', 'password', 'verification_code']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return Response({'error': f"Missing required fields: {', '.join(missing_fields)}"}, status=400)

        email = data['email']
        if CustomUser.objects.filter(email=email).exists():
            return Response({'error': 'Email already registered!'}, status=400)

        avatar = request.FILES.get('avatar')
        if avatar and getattr(avatar, 'name', None):
            avatar_path = default_storage.save(f"avatars/{avatar.name}", avatar)
        else:
            avatar_path = None

        try:
            user = CustomUser.objects.create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=email,
                username=email.split('@')[0],
                password=make_password(data['password']),
                phone_number=data.get('phone_number'),
                verification_code=data['verification_code'],
                avatar=avatar_path,
                role=data.get('role', 'user')
            )

            refresh = RefreshToken.for_user(user)
            user.access_token = str(refresh.access_token)
            user.refresh_token = str(refresh)
            user.save()

            return Response({
                'message': 'User registered successfully!',
                'user_id': user.id,
                'access': user.access_token,
                'refresh': user.refresh_token
            })

        except Exception as e:
            return Response({'error': f"Server error: {str(e)}"}, status=500)

    def login(self, request):
        data = request.data
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return Response({'error': 'Email and password are required!'}, status=400)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Invalid credentials!'}, status=401)

        if check_password(password, user.password):
            refresh = RefreshToken.for_user(user)
            user.access_token = str(refresh.access_token)
            user.refresh_token = str(refresh)
            user.save()

            LoginHistory.objects.create(
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )

            return Response({
                'message': 'Login successful!',
                'user_id': user.id,
                'username': user.username,
                'access': user.access_token,
                'refresh': user.refresh_token
            })

        return Response({'error': 'Invalid credentials!'}, status=401)

#send email forget by swagger
class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Request password reset",
        operation_description="Sends a password reset link to the user's email if it exists.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email")
            }
        ),
        responses={
            200: openapi.Response(description="Reset email sent"),
        }
    )
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required!'}, status=400)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # امنیت: همیشه پیام مشابه بده
            return Response({'message': 'If your email exists in our system, a reset link has been sent.'}, status=200)

        # تولید توکن یکتا
        token = get_random_string(64)
        while PasswordResetToken.objects.filter(token=token).exists():
            token = get_random_string(64)

        # ساخت توکن در دیتابیس
        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(hours=1)
        )

        reset_link = f"https://auth.alecplus.tech/forgot-password?token={token}"
        message = (
            f"Hi {user.first_name},\n\n"
            f"You requested a password reset. Click the link below to reset your password:\n\n"
            f"{reset_link}\n\n"
            "If you didn't request this, just ignore this email."
        )

        send_mail(
            subject="Password Reset Request",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({'message': 'If your email exists in our system, a reset link has been sent.'}, status=200)


#Get token And creat password new
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Reset password using token",
        operation_description="Set a new password using a valid reset token.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["token", "new_password", "confirm_password"],
            properties={
                "token": openapi.Schema(type=openapi.TYPE_STRING),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "confirm_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            }
        ),
        responses={
            200: "Password reset successful",
            400: "Invalid or expired token / Password mismatch"
        }
    )
    def post(self, request):
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not token or not new_password or not confirm_password:
            return Response({'error': 'All fields are required.'}, status=400)

        if new_password != confirm_password:
            return Response({'error': 'Passwords do not match.'}, status=400)

        try:
            token_obj = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid token.'}, status=400)

        if not token_obj.is_valid():
            return Response({'error': 'Token has expired or already used.'}, status=400)

        user = token_obj.user
        user.password = make_password(new_password)
        user.save()

        # Deactivate the token
        token_obj.used = True
        token_obj.save()

        return Response({'message': 'Password has been reset successfully.'})


#--User Account & Security--

#Login History by swagger +
class LoginHistoryView(JWTUserMixin, APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get login history for the current user",
        responses={200: openapi.Response(
            description="List of login history records",
            examples={
                "application/json": [
                    {
                        "ip_address": "192.168.1.1",
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "login_time": "2025-06-18T12:34:56Z"
                    }
                ]
            }
        )}
    )
    def get(self, request):
        user = self.get_user_from_token(request)
        history = LoginHistory.objects.filter(user=user).order_by('-login_time')[:50]
        data = [
            {
                "ip_address": entry.ip_address,
                "user_agent": entry.user_agent,
                "login_time": entry.login_time
            }
            for entry in history
        ]
        return Response(data)


#Active Devices List by swagger +
class ActiveDevicesView(JWTUserMixin, APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get list of unique active devices (based on IP and User-Agent)",
        responses={200: openapi.Response(
            description="List of active devices",
            examples={
                "application/json": [
                    {
                        "ip_address": "192.168.1.1",
                        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                    }
                ]
            }
        )}
    )
    def get(self, request):
        user = self.get_user_from_token(request)
        unique_devices = LoginHistory.objects.filter(user=user).values('ip_address', 'user_agent').distinct()
        return Response(list(unique_devices))


#change password by swagger +
class ChangePasswordView(APIView, JWTUserMixin):
    @swagger_auto_schema(
        operation_summary="Change user password",
        operation_description="Changes the authenticated user's password and returns new access and refresh tokens.",
        manual_parameters=[
            openapi.Parameter('Authorization', openapi.IN_HEADER, description="JWT token (Bearer ...)", type=openapi.TYPE_STRING, required=True)
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["current_password", "new_password"],
            properties={
                "current_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            }
        ),
        responses={200: "Password changed successfully"}
    )
    def post(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed!'}, status=401)

        data = request.data
        if not check_password(data.get('current_password'), user.password):
            return Response({'error': 'Current password is incorrect!'}, status=400)

        user.password = make_password(data.get('new_password'))
        refresh = RefreshToken.for_user(user)
        user.access_token = str(refresh.access_token)
        user.refresh_token = str(refresh)
        user.save()

        return Response({
            'message': 'Password changed successfully!',
            'access': user.access_token,
            'refresh': user.refresh_token
        })







#--User Profile and Preferences--

#view profile by swagger +
class ViewUserProfileView(APIView, JWTUserMixin):
    @swagger_auto_schema(
        operation_summary="View user profile",
        operation_description="Returns the authenticated user's profile information.",
        manual_parameters=[
            openapi.Parameter('Authorization', openapi.IN_HEADER, description="JWT token (Bearer ...)", type=openapi.TYPE_STRING, required=True)
        ],
        responses={200: openapi.Response(
            description="User profile",
            examples={
                "application/json": {
                    "user_id": 1,
                    "first_name": "Ali",
                    "last_name": "Rezaei",
                    "email": "ali@example.com",
                    "phone_number": "09120000000",
                    "username": "ali",
                    "avatar_url": "http://localhost:8000/media/avatars/ali.png"
                }
            }
        )}
    )
    def get(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed!'}, status=401)
        return Response({
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': user.phone_number,
            'username': user.username,
            'avatar_url': user.avatar.url if user.avatar else None
        })


#edit profile by swagger
class UpdateUserProfileView(APIView, JWTUserMixin):
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    @swagger_auto_schema(
        operation_summary="Update user profile",
        operation_description="Allows authenticated users to update their profile information and avatar.",
        manual_parameters=[
            openapi.Parameter('Authorization', openapi.IN_HEADER, description="JWT token (Bearer ...)", type=openapi.TYPE_STRING, required=True)
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING),
                "avatar": openapi.Schema(type=openapi.TYPE_FILE),
            }
        ),
        responses={200: openapi.Response(
            description="Profile updated successfully",
            examples={"application/json": {"message": "Profile updated successfully!"}}
        )
        }
    )
    def post(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed!'}, status=401)

        data = request.data
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.phone_number = data.get('phone_number', user.phone_number)

        if 'avatar' in request.FILES:
            avatar = request.FILES['avatar']
            avatar_path = default_storage.save(f"avatars/{avatar.name}", avatar)
            user.avatar = avatar_path

        user.save()
        return Response({'message': 'Profile updated successfully!'})












#buy token by swagger
class CreatePurchaseRequestView(APIView, JWTUserMixin):
    @swagger_auto_schema(
        operation_summary="Create token purchase request",
        manual_parameters=[
            openapi.Parameter('Authorization', openapi.IN_HEADER, description="JWT token", type=openapi.TYPE_STRING)
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["token_amount", "network", "verification_code"],
            properties={
                "token_amount": openapi.Schema(type=openapi.TYPE_INTEGER),
                "network": openapi.Schema(type=openapi.TYPE_STRING, enum=[n[0] for n in NETWORK_CHOICES]),
                "verification_code": openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={200: "Purchase created successfully"}
    )
    def post(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed'}, status=401)

        data = request.data
        if not all(field in data for field in ['token_amount', 'network', 'verification_code']):
            return Response({'error': 'Missing required fields'}, status=400)

        if data['network'] not in dict(NETWORK_CHOICES):
            return Response({'error': 'Invalid network selected'}, status=400)

        if user.verification_code != data['verification_code']:
            return Response({'error': 'Invalid verification code'}, status=400)

        try:
            token_amount = int(data['token_amount'])
            if token_amount < MIN_TOKENS:
                return Response({'error': f'Minimum purchase is {MIN_TOKENS} tokens.'}, status=400)
        except ValueError:
            return Response({'error': 'token_amount must be an integer'}, status=400)

        usdt_amount = Decimal(token_amount) * TOKEN_PRICE
        wallet_addresses = {
            'TRC20': 'TXMTej3ecvp5nnJRufbhBoRGNygjubrrZa',
            'BEP20': '0x887b46aBb77B372aC7ae2d4F75C1f93890C31827',
            'ERC20': '0x887b46aBb77B372aC7ae2d4F75C1f93890C31827'
        }
        trust_links = {
            'TRC20': f'https://link.trustwallet.com/send?coin=195&address={wallet_addresses["TRC20"]}&token_id=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t',
            'BEP20': f'https://link.trustwallet.com/send?coin=20000714&address={wallet_addresses["BEP20"]}&token_id=0x55d398326f99059fF775485246999027B3197955',
            'ERC20': f'https://link.trustwallet.com/send?coin=60&address={wallet_addresses["ERC20"]}&token_id=0xdAC17F958D2ee523a2206206994597C13D831ec7'
        }

        address = wallet_addresses[data['network']]
        purchase = TokenPurchase.objects.create(
            user=user,
            usdt_amount=usdt_amount,
            network=data['network'],
            wallet_address=address,
            status='pending'
        )
        return Response({
            'message': 'Purchase request created successfully.',
            'purchase_id': purchase.id,
            'wallet_address': address,
            'usdt_amount': str(usdt_amount),
            'token_amount': token_amount,
            'trust_wallet_link': trust_links[data['network']]
        })



#hash token by swagger
class ConfirmTransactionView(APIView, JWTUserMixin):
    @swagger_auto_schema(
        operation_summary="Confirm blockchain transaction",
        operation_description="Allows the authenticated user to confirm their transaction by providing purchase_id and tx_hash.",
        manual_parameters=[
            openapi.Parameter('Authorization', openapi.IN_HEADER, description="JWT token", type=openapi.TYPE_STRING)
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["purchase_id", "tx_hash"],
            properties={
                "purchase_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "tx_hash": openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            200: openapi.Response(description="Transaction submitted for review"),
            400: openapi.Response(description="Missing required fields"),
            403: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Purchase not found")
        }
    )
    def post(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed'}, status=401)

        data = request.data
        if not all(field in data for field in ['purchase_id', 'tx_hash']):
            return Response({'error': 'Missing required fields'}, status=400)

        try:
            purchase = TokenPurchase.objects.get(id=data['purchase_id'])
        except TokenPurchase.DoesNotExist:
            return Response({'error': 'Purchase not found'}, status=404)

        if purchase.user != user:
            return Response({'error': 'Unauthorized'}, status=403)

        purchase.tx_hash = data['tx_hash']
        purchase.status = 'reviewing'
        purchase.save()

        return Response({'message': 'Transaction submitted and is under review.'})



#Get status by swagger
class PurchaseStatusView(APIView, JWTUserMixin):
    @swagger_auto_schema(
        operation_summary="Get purchase status",
        operation_description="Allows the authenticated user to check the status of one of their token purchases.",
        manual_parameters=[
            openapi.Parameter('Authorization', openapi.IN_HEADER, description="JWT token", type=openapi.TYPE_STRING),
            openapi.Parameter('purchase_id', openapi.IN_QUERY, description="ID of the purchase", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response(description="Returns purchase details"),
            400: openapi.Response(description="Missing purchase_id"),
            403: openapi.Response(description="Unauthorized access"),
            404: openapi.Response(description="Purchase not found")
        }
    )
    def get(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed'}, status=401)

        purchase_id = request.query_params.get('purchase_id')
        if not purchase_id:
            return Response({'error': 'purchase_id is required'}, status=400)

        try:
            purchase = TokenPurchase.objects.get(id=purchase_id)
        except TokenPurchase.DoesNotExist:
            return Response({'error': 'Purchase not found'}, status=404)

        if purchase.user != user:
            return Response({'error': 'Unauthorized'}, status=403)

        from .constants import TOKEN_PRICE
        token_amount = int(purchase.usdt_amount / TOKEN_PRICE)

        return Response({
            'purchase_id': purchase.id,
            'user': purchase.user.username,
            'network': purchase.network,
            'usdt_amount': str(purchase.usdt_amount),
            'token_amount': token_amount,
            'status': purchase.status,
            'wallet_address': purchase.wallet_address,
            'tx_hash': purchase.tx_hash
        })



#list buys token
class UserPurchasesView(APIView, JWTUserMixin):
    @swagger_auto_schema(
        operation_summary="List of user token purchases",
        manual_parameters=[
            openapi.Parameter('Authorization', openapi.IN_HEADER, description="JWT token", type=openapi.TYPE_STRING)
        ],
        responses={200: "List of purchases"}
    )
    def get(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed'}, status=401)

        purchases = TokenPurchase.objects.filter(user=user).order_by('-created_at')
        data = [
            {
                'purchase_id': p.id,
                'usdt_amount': str(p.usdt_amount),
                'token_amount': int(p.usdt_amount / TOKEN_PRICE),
                'network': p.network,
                'status': p.status,
                'wallet_address': p.wallet_address,
                'tx_hash': p.tx_hash,
                'created_at': p.created_at.isoformat()
            } for p in purchases
        ]
        return Response({'purchases': data})




#General documentation for the Authorization header by swagger
auth_header = openapi.Parameter(
    'Authorization',
    openapi.IN_HEADER,
    description="JWT token (e.g., Bearer eyJ...)", 
    type=openapi.TYPE_STRING,
    required=True
)




#Total Asset Overview by swagger
class TotalAssetOverviewView(APIView, JWTUserMixin):
    @swagger_auto_schema(
        operation_summary="User's Total Asset Overview",
        operation_description="Returns total and confirmed (withdrawable) USDT and token amounts for the authenticated user.",
        manual_parameters=[auth_header],
        responses={200: openapi.Response(
            description="Asset overview",
            examples={
                "application/json": {
                    "total_usdt": "250.00",
                    "total_tokens": 2500,
                    "withdrawable_usdt": "150.00",
                    "withdrawable_tokens": 1500
                }
            }
        )}
    )
    def get(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed'}, status=401)
        all_purchases = TokenPurchase.objects.filter(user=user)
        confirmed = all_purchases.filter(status='confirmed')
        total_usdt = sum(p.usdt_amount for p in all_purchases)
        confirmed_usdt = sum(p.usdt_amount for p in confirmed)
        return Response({
            "total_usdt": str(total_usdt),
            "total_tokens": int(total_usdt / TOKEN_PRICE),
            "withdrawable_usdt": str(confirmed_usdt),
            "withdrawable_tokens": int(confirmed_usdt / TOKEN_PRICE)
        })




#Total Purchased Tokens by swagger
class TotalPurchasedTokensView(APIView, JWTUserMixin):
    @swagger_auto_schema(
        operation_summary="Total Purchased Tokens",
        operation_description="Returns the total number of tokens and total USDT spent by the authenticated user.",
        manual_parameters=[auth_header],
        responses={200: openapi.Response(
            description="Total purchased tokens",
            examples={
                "application/json": {
                    "total_purchased_tokens": 5000,
                    "total_spent_usdt": "500.00"
                }
            }
        )}
    )
    def get(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed'}, status=401)
        purchases = TokenPurchase.objects.filter(user=user)
        total_usdt = sum(p.usdt_amount for p in purchases)
        return Response({
            "total_purchased_tokens": int(total_usdt / TOKEN_PRICE),
            "total_spent_usdt": str(total_usdt)
        })




#Withdrawable Balance by swagger
class WithdrawableBalanceView(APIView, JWTUserMixin):
    @swagger_auto_schema(
        operation_summary="Withdrawable Token Balance",
        operation_description="Returns confirmed (withdrawable) USDT and token balance for the authenticated user.",
        manual_parameters=[auth_header],
        responses={200: openapi.Response(
            description="Withdrawable balance",
            examples={
                "application/json": {
                    "withdrawable_tokens": 2000,
                    "withdrawable_usdt": "200.00"
                }
            }
        )}
    )
    def get(self, request):
        user = self.get_user_from_token(request)
        if not user:
            return Response({'error': 'Authentication failed'}, status=401)
        confirmed = TokenPurchase.objects.filter(user=user, status='confirmed')
        total_usdt = sum(p.usdt_amount for p in confirmed)
        return Response({
            "withdrawable_tokens": int(total_usdt / TOKEN_PRICE),
            "withdrawable_usdt": str(total_usdt)
        })
    




