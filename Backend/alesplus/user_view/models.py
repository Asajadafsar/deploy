from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings

# -----------------------------
# Contact Model
# -----------------------------
class Contact(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# -----------------------------
# Custom User Manager
# -----------------------------
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

# -----------------------------
# Custom User Model
# -----------------------------
class CustomUser(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    verification_code = models.CharField(
        max_length=6,
        validators=[RegexValidator(regex=r'^\d{6}$', message='Verification code must be exactly 6 digits')]
    )
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)

    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.username} ({self.email})"

# -----------------------------
# Token Purchase Model
# -----------------------------
NETWORK_CHOICES = [
    ('TRC20', 'USDT (TRC20)'),
    ('ERC20', 'USDT (ERC20)'),
    ('BEP20', 'USDT (BEP20)')
]

class TokenPurchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    usdt_amount = models.DecimalField(max_digits=20, decimal_places=6)
    network = models.CharField(max_length=10, choices=NETWORK_CHOICES)
    wallet_address = models.CharField(max_length=255)
    tx_hash = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')  # pending, confirmed, rejected
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.usdt_amount} USDT ({self.network})"

# -----------------------------
# Partnership Request Model
# -----------------------------
PARTNERSHIP_CHOICES = [
    ('advertising', 'Advertising'),
    ('investment_invention', 'Investment for Inventions Only'),
    ('investment_metaverse', 'Investment for Metaverse Only'),
    ('infrastructure', 'Infrastructure Development / Data Engineering & Website'),
    ('corporate_connection', 'Connection with Major Corporate Supporters'),
    ('exchange_listing', 'Token Listing Collaboration on Major Exchanges'),
    ('other', 'Other'),
]

class PartnershipRequest(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    cooperation_type = models.CharField(max_length=50, choices=PARTNERSHIP_CHOICES)
    other_description = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_cooperation_type_display()}"

# -----------------------------
# Password Reset Token Model
# -----------------------------
class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() < self.expires_at

# -----------------------------
# Login History Model
# -----------------------------
class LoginHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    login_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.ip_address} - {self.login_time.strftime('%Y-%m-%d %H:%M:%S')}"
