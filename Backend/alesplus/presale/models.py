from django.db import models

class PresaleTransaction(models.Model):
    user_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    payment_network = models.CharField(max_length=10, choices=[('TRC20', 'TRC20'), ('BEP20', 'BEP20')])
    wallet_address = models.CharField(max_length=255)
    amount_usdt = models.DecimalField(max_digits=12, decimal_places=2)
    token_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_code = models.CharField(max_length=255)
    transaction_status = models.CharField(max_length=50, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.id} - {self.user_name}"
