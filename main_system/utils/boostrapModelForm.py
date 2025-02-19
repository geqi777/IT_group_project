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


class Employee_ModelForm(BoostrapModelForm):
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = models.Employee
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
            "is_employee",
            "role",
            "join_time",
            "department"
        ]
        widgets = {
            'password': forms.PasswordInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_employee':
                field.widget.attrs['class'] = 'form-check-input'  # 特别为复选框添加样式

    def clean_password(self):
        data = self.cleaned_data.get('password')
        md5_password = md5(data)
        exists = models.Employee.objects.filter(id=self.instance.pk, password=md5_password).exists()
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


class Vehicle_ModelForm(BoostrapModelForm):
    class Meta:
        model = models.Vehicle
        fields = ['name', 'power', 'price', 'situation', 'vehicle_type', 'vehicle_number',
                  'rental_time', 'latitude', 'longitude', 'user']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            # 添加样式
            field.widget.attrs['class'] = 'form-control'  # 为所有字段添加 form-control 样式
            if name == 'is_available':
                field.widget.attrs['class'] = 'form-check-input'  # 特别为复选框添加样式
            elif name == 'rental_time':
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['readonly'] = 'readonly'  # 设置租赁时间为只读


class Employee_EditForm(BoostrapModelForm):
    class Meta:
        model = models.Employee
        fields = [
            "name",
            "date_of_birth",
            "gender",
            "email",
            "phone",
            "address",
            "account",
            "is_employee",
            "role",
            "join_time",
            "department"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_employee':
                field.widget.attrs['class'] = 'form-check-input'  # 特别为复选框添加样式


class ResetPasswordForm(BoostrapModelForm):
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = models.Employee
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


class Customer_ModelForm(BoostrapModelForm):
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = models.Customer
        fields = [
            "name",
            "email",
            "date_of_birth",
            "gender",
            "phone",
            "address",
            "account",
            "password",
            "account_balance",
            "create_time",
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
        exists = models.Employee.objects.filter(id=self.instance.pk, password=md5_password).exists()
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


class Customer_EditForm(BoostrapModelForm):
    class Meta:
        model = models.Customer
        fields = [
            "name",
            "email",
            "date_of_birth",
            "gender",
            "phone",
            "address",
            "driver_license",  # 驾照文件字段
            "is_verified"      # 验证字段
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_verified':
                field.widget.attrs['class'] = 'form-check-input'


class Customer_Edit2Form(BoostrapModelForm):
    class Meta:
        model = models.Customer
        fields = [
            "name",
            "email",
            "date_of_birth",
            "gender",
            "phone",
            "address",
            # "driver_license",  # 驾照文件字段
            # "is_verified"      # 验证字段
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_verified':
                field.widget.attrs['class'] = 'form-check-input'


class Customer_RegisterForm(BoostrapModelForm):
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = models.Customer
        fields = [
            "name",
            "email",
            "date_of_birth",
            "gender",
            "phone",
            "address",
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
        exists = models.Employee.objects.filter(id=self.instance.pk, password=md5_password).exists()
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

        # Override the save method to ensure is_verified is set to False

class LicenseUploadForm(forms.ModelForm):
    class Meta:
        model = models.Customer
        fields = ['driver_license']  # 驾照上传字段
        labels = {
            'driver_license': 'Upload your driver license',  # 标签
        }
        widgets = {
            'driver_license': forms.ClearableFileInput(attrs={'class': 'form-control'}),  # 控件样式
        }

class LicenseVerificationForm(forms.ModelForm):
    class Meta:
        model = models.Customer
        fields = ['driver_license', 'is_verified']  # 只需要驾照和是否验证字段
        labels = {
            'driver_license': 'Driver License',
            'is_verified': 'Verify License'
        }
        widgets = {
            'driver_license': forms.ClearableFileInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'is_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['driver_license'].widget.attrs['readonly'] = True  # 驾照为只读

class HistoryModelForm(BoostrapModelForm):
    confirm_rating = forms.IntegerField(label='Confirm Rating')

    class Meta:
        model = models.History
        fields = [
            'vehicle',
            'start_time',
            'end_time',
            'cost',
            'start_location_name',
            'end_location_name',
            'rating',
            'confirm_rating',
            'review',
            'status'
        ]
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'start_location_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'end_location_name': forms.TextInput(attrs={'class': 'form-control'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control'}),
            'review': forms.Textarea(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),  # 使用Select来显示状态选择框
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if name == 'confirm_rating':
                field.widget.attrs['class'] = 'form-check-input'

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is None or rating < 1 or rating > 5:
            raise ValidationError('Rating must be between 1 and 5.')
        return rating

class VehicleReportForm(forms.ModelForm):
    class Meta:
        model = models.VehicleReport
        fields = ['description', 'image']  # 包含问题描述和图片上传
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Describe the issue...'}), required=True)
    image = forms.ImageField(required=False)
