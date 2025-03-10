from django import forms
from django.shortcuts import render, redirect, HttpResponse
from main_system.utils.boostrapModelForm import BoostrapForm
from main_system.utils.encrypt import md5
from main_system import models

"""
account = admin
password = Admin123456

account = manager
password = Admin123456
"""

class LoginForm(BoostrapForm):
    account = forms.CharField(label='account', widget=forms.TextInput(attrs={'class': 'form-control'}), required=True)
    password = forms.CharField(label='password', widget=forms.PasswordInput(attrs={'class': 'form-control'}),
                               required=True)

    def clean_password(self):
        pwd = self.cleaned_data.get('password')
        return md5(pwd)

def admin_login(request):
    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'login/admin_login.html', {'form': form})

    form = LoginForm(data=request.POST)
    # print("获取到form")
    print("admin", md5("Admin123456"))
    if form.is_valid():
        account = form.cleaned_data['account']
        password = form.cleaned_data['password']

        # 查找员工对象
        employee_obj = models.Operator.objects.filter(account=account).first()
        # print(employee_obj.account, md5(employee_obj.password))
        # 验证员工对象是否存在以及密码是否正确
        if not employee_obj or password != employee_obj.password:
            print('Account or password is incorrect')
            form.add_error('password', 'Account or password is incorrect')
            return render(request, 'login/admin_login.html', {'form': form})

        # 设置 session 信息
        request.session['admin_info'] = {
            'employee_id': employee_obj.id,
            'employee_account': employee_obj.account,
            'is_employee': employee_obj.is_operator,
            'role': employee_obj.role,
            'name': employee_obj.name,
        }

        print(request.session['admin_info'])
        # if request.session['info']['role'] == 'manager':
        #     return redirect('/operation/manager/page/')
        return redirect('/operation/homepage/')

    return render(request, 'login/admin_login.html', {'form': form})


def logout(request):
    request.session.clear()
    return redirect('/')

