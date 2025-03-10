from django import forms
from django.shortcuts import render, redirect, HttpResponse
from main_system.utils.boostrapModelForm import BoostrapForm
from main_system.utils.encrypt import md5
from main_system import models


class LoginForm(BoostrapForm):
    account = forms.CharField(label='account', widget=forms.TextInput(attrs={'class': 'form-control'}), required=True)
    password = forms.CharField(label='password', widget=forms.PasswordInput(attrs={'class': 'form-control'}),
                               required=True)

    def clean_password(self):
        pwd = self.cleaned_data.get('password')
        return md5(pwd)


"""
account = admin
password = Admin123456

account = manager
password = Admin123456
"""


def employee_login(request):
    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'main/employee_login.html', {'form': form})

    form = LoginForm(data=request.POST)
    if form.is_valid():
        account = form.cleaned_data['account']
        password = form.cleaned_data['password']

        # 查找员工对象
        employee_obj = models.Employee.objects.filter(account=account).first()
        # 验证员工对象是否存在以及密码是否正确
        if not employee_obj or password != employee_obj.password:
            form.add_error('password', 'Account or password is incorrect')
            return render(request, 'main/employee_login.html', {'form': form})

        # 设置 session 信息
        request.session['admin_info'] = {
            'employee_id': employee_obj.id,
            'employee_account': employee_obj.account,
            'is_employee': employee_obj.is_employee,
            'role': employee_obj.role,
            'name': employee_obj.name,
        }
        return redirect('/operation/homepage/')

    return render(request, 'main/employee_login.html', {'form': form})


def logout(request):
    request.session.clear()
    return redirect('/')


def customer_login(request):
    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'customer/customer_login.html', {'form': form})

    form = LoginForm(data=request.POST)
    if form.is_valid():
        account = form.cleaned_data['account']
        password = form.cleaned_data['password']

        # 查找用户对象
        customer_obj = models.Customer.objects.filter(account=account).first()

        # 验证账号是否存在
        if not customer_obj:
            form.add_error('account', 'This account is not registered.')
            return render(request, 'customer/customer_login.html', {'form': form})

        # 验证密码是否正确
        if customer_obj.password != password:  # 假设密码未加密，如果有加密则需要进行解密或哈希比较
            form.add_error('password', 'Password is incorrect.')
            return render(request, 'customer/customer_login.html', {'form': form})

        # 设置 session 信息
        request.session['customer_info'] = {
            'customer_id': customer_obj.id,
            'customer_account': customer_obj.account,
            'is_verified': customer_obj.is_verified,
            'name': customer_obj.name,
        }
        return redirect('/customer/home/')

    return render(request, 'customer/customer_login.html', {'form': form})

