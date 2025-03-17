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
                field.widget.attrs['class'] = 'form-check-input'  # 特别为复选框添加样式

    def clean_password(self):
        data = self.cleaned_data.get('password')
        md5_password = md5(data)
        exists = models.User.objects.filter(id=self.instance.pk, password=md5_password).exists()
        if exists:
            raise ValidationError('This password is the same as your previous password.')

        # 验证密码长度
        if len(data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        # 验证是否包含至少一个大写字母和一个小写字母
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

            # 自动设置状态逻辑
            if stock == 0 or status == "Locked":  # 手动锁定或库存为 0
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

            # 自动设置状态逻辑
            if stock == 0 or status == "Locked":  # 手动锁定或库存为 0
                cleaned_data["status"] = "Locked"
            else:
                cleaned_data["status"] = "Active"

            return cleaned_data


# 管理员
class Operator_ModelForm(BoostrapModelForm):
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput())

    class Meta:
        model = models.Operator
        fields = [
            "name",
            "date_of_birth",
            "gender",
            "email",
            "phone",
            "account",
            "password",
            "confirm_password",
            "is_operator",
            "role",
            "join_time",
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

        # 验证密码长度
        if len(data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        # 验证是否包含至少一个大写字母和一个小写字母
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
            "date_of_birth",
            "gender",
            "email",
            "phone",
            "account",
            "is_operator",
            "role",
            "join_time",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_operator':
                field.widget.attrs['class'] = 'form-check-input'  # 特别为复选框添加样式


# 设置密码
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

        # 验证密码长度
        if len(data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        # 验证是否包含至少一个大写字母和一个小写字母
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


# 用户
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

        # 验证密码长度
        if len(data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        # 验证是否包含至少一个大写字母和一个小写字母
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


# 钱包
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
            'wallet': '钱包',
            'transaction_type': '交易类型',
            'amount': '交易金额',
            'original_amount': '原始金额',
            'final_amount': '最终金额',
            # 'timestamp': '交易时间',
            'order': '关联订单',
            'promo_code': '优惠码'
        }


# 订单
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


# 优惠码
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
            'code': '优惠码',
            'discount': '折扣金额',
            'min_order_value': '最低订单金额',
            'expiry_date': '过期日期',
            'description': '描述',
            'status': '状态'
        }

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date < timezone.now():
            raise ValidationError('过期日期不能早于当前时间')
        return expiry_date


class PromoCode_EditForm(BoostrapModelForm):
    """优惠码编辑表单"""
    class Meta:
        model = models.PromoCode
        fields = ['code', 'discount', 'min_order_value', 'expiry_date', 'description', 'status']
        widgets = {
            'code': forms.TextInput(attrs={'readonly': 'readonly'}),  # 编辑时code只读
            'discount': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'min_order_value': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'expiry_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'status': forms.Select(choices=[('active', 'active'), ('inactive', 'inactive'), ('expired', 'expired')], attrs={'class': 'form-select'})
        }
        labels = {
            'code': '优惠码',
            'discount': '折扣金额',
            'min_order_value': '最低订单金额',
            'expiry_date': '过期日期',
            'description': '描述',
            'status': '状态'
        }

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date < timezone.now():
            raise ValidationError('过期日期不能早于当前时间')
        return expiry_date 

