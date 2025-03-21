from django.utils import timezone
from django import forms
from main_system import models
from django.core.exceptions import ValidationError
from main_system.utils.encrypt import md5
import re


class Boostrap:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['placeholder'] = field.label
            else:
                field.widget.attrs = {
                    'class': 'form-control',
                    'placeholder': field.label,
                }


class BoostrapModelForm(Boostrap, forms.ModelForm):
    pass


class BoostrapForm(Boostrap, forms.Form):
    pass

# new versions
class User_RegisterForm(BoostrapModelForm):
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = models.User
        fields = [
            "name",
            # "date_of_birth",
            # "gender",
            # "email",
            # "phone",
            # "address",
            "account",
            "password"
            # "account_balance",
            # "create_time",
            # "is_verified"
        ]
        widgets = {
            'password': forms.PasswordInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_verified':
                field.widget.attrs['class'] = 'form-check-input'  # Add style specifically for checkbox

    def clean_password(self):
        data = self.cleaned_data.get('password')
        md5_password = md5(data)
        exists = models.User.objects.filter(id=self.instance.pk, password=md5_password).exists()
        if exists:
            raise ValidationError('This password is the same as your previous password.')

        # Validate password length
        if len(data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        # Validate if it contains at least one uppercase and one lowercase letter
        if not re.search(r'[A-Z]', data):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', data):
            raise ValidationError('Password must contain at least one lowercase letter.')

        return md5(data)

    def clean_confirm_password(self):
        pwd = self.cleaned_data.get('password')
        confirm = md5(self.cleaned_data.get('confirm_password'))
        if pwd != confirm:
            raise ValidationError('Passwords must match.')
        return confirm

class Product_ModelForm(BoostrapModelForm):
    class Meta:
        model = models.Product
        fields = [
            "name",
            "description",
            "category",
            "price",
            "stock",
            "status",
            "picture"
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'min': '0.00'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

        def clean_price(self):
            price = self.cleaned_data.get('price')
            if price is None or price <= 0:
                raise ValidationError('Price must be greater than 0.')
            return price
        
        def clean_stock(self):
            stock = self.cleaned_data.get('stock')
            if stock is None or stock < 0:
                raise ValidationError('Stock cannot be negative.')
            return stock

        def clean(self):
            cleaned_data = super().clean()
            stock = cleaned_data.get("stock")
            status = cleaned_data.get("status")

            # Auto set status logic
            if stock == 0 or status == "Locked":  # Manually locked or stock is 0
                cleaned_data["status"] = "Locked"
            else:
                cleaned_data["status"] = "Active"

            return cleaned_data


class Product_EditForm(BoostrapModelForm):
    class Meta:
        model = models.Product
        fields = [
            "name",
            "description",
            "category",
            "price",
            "stock",
            "status",
            "picture"
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'min': '0.00'}),
            'status': forms.Select(choices=[("active", "Active"), ("locked", "Locked")], attrs={'class': 'form-select'}),
        }

        def clean(self):
            cleaned_data = super().clean()
            stock = cleaned_data.get("stock")
            status = cleaned_data.get("status")

            # Auto set status logic
            if stock == 0 or status == "Locked":  # Manually locked or stock is 0
                cleaned_data["status"] = "Locked"
            else:
                cleaned_data["status"] = "Active"

            return cleaned_data


# Admin
class Operator_ModelForm(BoostrapModelForm):
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput())

    class Meta:
        model = models.Operator
        fields = [
            "name",
            "gender",
            "email",
            "phone",
            "account",
            "password",
            "confirm_password",
            "is_operator",
            "role",
        ]
        widgets = {
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def clean_password(self):
        data = self.cleaned_data.get('password')
        md5_password = md5(data)
        exists = models.Operator.objects.filter(id=self.instance.pk, password=md5_password).exists()
        if exists:
            raise ValidationError('This password is the same as your previous password.')

        # Validate password length
        if len(data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        # Validate if it contains at least one uppercase and one lowercase letter
        if not re.search(r'[A-Z]', data):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', data):
            raise ValidationError('Password must contain at least one lowercase letter.')

        return md5(data)

    def clean_confirm_password(self):
        pwd = self.cleaned_data.get('password')
        confirm = md5(self.cleaned_data.get('confirm_password'))
        if pwd != confirm:
            raise ValidationError('Passwords must match.')

        return confirm

class Operator_EditForm(BoostrapModelForm):
    class Meta:
        model = models.Operator
        fields = [
            "name",
            "gender",
            "email",
            "phone",
            "account",
            "is_operator",
            "role",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_operator':
                field.widget.attrs['class'] = 'form-check-input'  # Add style specifically for checkbox


# Reset Password
class ResetPasswordForm(BoostrapModelForm):
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = models.User
        fields = [
            "password",
            "confirm_password",
        ]

        widgets = {
            'password': forms.PasswordInput,
        }

    def clean_password(self):
        data = self.cleaned_data.get('password')

        # Validate password length
        if len(data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        # Validate if it contains at least one uppercase and one lowercase letter
        if not re.search(r'[A-Z]', data):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', data):
            raise ValidationError('Password must contain at least one lowercase letter.')

        return md5(data)

    def clean_confirm_password(self):
        pwd = self.cleaned_data.get('password')
        confirm = md5(self.cleaned_data.get('confirm_password'))
        if pwd != confirm:
            raise ValidationError('Passwords must match.')

        return confirm


# User
class User_ModelForm(BoostrapModelForm):
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput())

    class Meta:
        model = models.User
        fields = [
            "name",
            "date_of_birth",
            "gender",
            "email",
            "phone",
            "address",
            "account",
            "password",
            "confirm_password",
            "create_time",
        ]
        widgets = {
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def clean_password(self):
        data = self.cleaned_data.get('password')
        md5_password = md5(data)
        exists = models.User.objects.filter(id=self.instance.pk, password=md5_password).exists()
        if exists:
            raise ValidationError('This password is the same as your previous password.')

        # Validate password length
        if len(data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        # Validate if it contains at least one uppercase and one lowercase letter
        if not re.search(r'[A-Z]', data):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', data):
            raise ValidationError('Password must contain at least one lowercase letter.')

        return md5(data)

    def clean_confirm_password(self):
        pwd = self.cleaned_data.get('password')
        confirm = md5(self.cleaned_data.get('confirm_password'))
        if pwd != confirm:
            raise ValidationError('Passwords must match.')

        return confirm

class User_EditForm(BoostrapModelForm):
    class Meta:
        model = models.User
        fields = [
            "name",
            "date_of_birth",
            "gender",
            "email",
            "phone",
            "address",
        ]


# Wallet
class Wallet_ModelForm(BoostrapModelForm):
    class Meta:
        model = models.Wallet
        fields = [
            "balance",
            "points",
        ]
        widgets = {
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

class WalletTransaction_ModelForm(BoostrapModelForm):
    class Meta:
        model = models.WalletTransaction
        fields = [
            "wallet",
            "transaction_type",
            "amount",
            "order",
            "promo_code",
            "original_amount",
            "final_amount",
            # "timestamp"
        ]
        widgets = {
            "wallet": forms.Select(attrs={'class': 'form-control', 'disabled': 'disabled'}),
            "transaction_type": forms.Select(attrs={'class': 'form-control', 'disabled': 'disabled'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'original_amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'final_amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            # "timestamp": forms.DateTimeInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            "order": forms.Select(attrs={'class': 'form-control', 'disabled': 'disabled'}),
            "promo_code": forms.Select(attrs={'class': 'form-control', 'disabled': 'disabled'})
        }
        labels = {
            'wallet': 'Wallet',
            'transaction_type': 'Transaction Type',
            'amount': 'Transaction Amount',
            'original_amount': 'Original Amount',
            'final_amount': 'Final Amount',
            # 'timestamp': 'Transaction Time',
            'order': 'Related Order',
            'promo_code': 'Promo Code'
        }


# Order
class Order_ModelForm(BoostrapModelForm):
    class Meta:
        model = models.Order
        fields = ['order_status', 'payment_method', 'shipping_address']
        widgets = {
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
        }

class OrderItem_ModelForm(BoostrapModelForm):
    class Meta:
        model = models.OrderItem
        fields = ['quantity']


# Promo Code
class PromoCode_ModelForm(BoostrapModelForm):
    class Meta:
        model = models.PromoCode
        fields = ['code', 'discount', 'min_order_value', 'expiry_date', 'description', 'status']
        widgets = {
            'code': forms.TextInput(),
            'discount': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'min_order_value': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'expiry_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'status': forms.Select(choices=[('active', 'active'), ('inactive', 'inactive'), ('expired', 'expired')], attrs={'class': 'form-select'})
        }
        labels = {
            'code': 'Promo Code',
            'discount': 'Discount Amount',
            'min_order_value': 'Minimum Order Value',
            'expiry_date': 'Expiry Date',
            'description': 'Description',
            'status': 'Status'
        }

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date < timezone.now():
            raise ValidationError('Expiry date cannot be earlier than the current time')
        return expiry_date


class PromoCode_EditForm(BoostrapModelForm):
    """Promo Code Edit Form"""
    class Meta:
        model = models.PromoCode
        fields = ['code', 'discount', 'min_order_value', 'expiry_date', 'description', 'status']
        widgets = {
            'code': forms.TextInput(attrs={'readonly': 'readonly'}),  # Code is read-only when editing
            'discount': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'min_order_value': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'expiry_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'status': forms.Select(choices=[('active', 'active'), ('inactive', 'inactive'), ('expired', 'expired')], attrs={'class': 'form-select'})
        }
        labels = {
            'code': 'Promo Code',
            'discount': 'Discount Amount',
            'min_order_value': 'Minimum Order Value',
            'expiry_date': 'Expiry Date',
            'description': 'Description',
            'status': 'Status'
        }

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date < timezone.now():
            raise ValidationError('Expiry date cannot be earlier than the current time')
        return expiry_date 


# Admin Forms
class AdminLoginForm(BoostrapForm):
    account = forms.CharField(label='Account', widget=forms.TextInput(), required=True)
    password = forms.CharField(label='Password', widget=forms.PasswordInput(), required=True)

    def clean_password(self):
        pwd = self.cleaned_data.get('password')
        return md5(pwd)

class AdminProfileForm(BoostrapModelForm):
    class Meta:
        model = models.Operator
        fields = [
            "name",
            "gender",
            "email",
            "phone",
        ]

