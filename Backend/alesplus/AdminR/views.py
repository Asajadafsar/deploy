import json
from functools import wraps
from rest_framework_simplejwt.tokens import AccessToken
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from presale.models import PresaleTransaction
from user_view.models import CustomUser as User  # این alias استفاده شده
from rest_framework import status

# Token verification decorator with role check
def token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Authorization header is missing'}, status=401)

        token = auth_header.split(' ')[1]

        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)  # ✅ اینجا باید از alias استفاده کنی

            if user.role != 'admin':
                return JsonResponse({'error': 'Permission denied'}, status=403)

            request.user = user
        except Exception as e:
            return JsonResponse({'error': 'Invalid token', 'details': str(e)}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper

# View all Presale Transactions (admin-only)
@api_view(['GET'])
@token_required
def view_presale_transactions(request):
    range_param = request.GET.get("range", "[0, 10]")
    filter_param = request.GET.get("filter", "")

    try:
        final_range = json.loads(range_param)
        if not isinstance(final_range, list) or len(final_range) != 2:
            final_range = [0, 10]
    except Exception:
        final_range = [0, 10]

    try:
        filter_dict = json.loads(filter_param)
        search = filter_dict.get("q", "")
    except Exception:
        search = ""

    queryset = PresaleTransaction.objects.filter(
        Q(user_name__icontains=search) | Q(email__icontains=search)
    ).order_by('-created_at')

    total = queryset.count()
    sliced = queryset[final_range[0]: final_range[1]]

    data = [
        {
            "id": tx.id,
            "user_name": tx.user_name,
            "email": tx.email,
            "phone_number": tx.phone_number,
            "payment_network": tx.payment_network,
            "user_wallet_address": tx.user_wallet_address,
            "user_wallet_network": tx.user_wallet_network,
            "amount_usdt": float(tx.amount_usdt),
            "token_quantity": float(tx.token_quantity),
            "transaction_code": tx.transaction_code,
            "transaction_status": tx.transaction_status,
            "created_at": tx.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for tx in sliced
    ]

    response = Response(data)
    response["Content-Range"] = f"transactions {final_range[0]}-{final_range[1]-1}/{total}"
    response["Access-Control-Expose-Headers"] = "Content-Range"
    return response

#Edit status
@api_view(['PUT'])
@token_required
def update_transaction_status(request, transaction_id):
    try:
        transaction = PresaleTransaction.objects.get(pk=transaction_id)
    except PresaleTransaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('transaction_status')
    if not new_status:
        return JsonResponse({'error': 'transaction_status is required'}, status=status.HTTP_400_BAD_REQUEST)

    transaction.transaction_status = new_status
    transaction.save()

    return Response({
        'message': 'Transaction status updated successfully',
        'id': transaction.id,
        'transaction_status': transaction.transaction_status
    }, status=status.HTTP_200_OK)


