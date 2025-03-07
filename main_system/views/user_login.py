from django import forms
from django.shortcuts import render, redirect, HttpResponse
from main_system.utils.boostrapModelForm import BoostrapForm, User_RegisterForm
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

def user_profile(request):
    print("访问到user——profile")
    return HttpResponse('ok')

def user_login(request):
    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'login/user_login.html', {'form': form})

    form = LoginForm(data=request.POST)
    if form.is_valid():
        account = form.cleaned_data['account']
        password = form.cleaned_data['password']

        # 查找用户对象
        user_obj = models.User.objects.filter(account=account).first()
        # 验证用户对象是否存在以及密码是否正确
        if not user_obj or password != user_obj.password:
            form.add_error('password', 'Account or password is incorrect')
            return render(request, 'login/user_login.html', {'form': form})

        # 设置 session 信息
        request.session['info'] = {
            'user_id': user_obj.id,
            'user_account': user_obj.account,
            'name': user_obj.name,
        }

        print(request.session['info'])
        # if request.session['info']['role'] == 'manager':
        #     return redirect('/operation/manager/page/')
        print('准备跳转到home')
        # 获取来源页面，如果没有则默认跳转到首页
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('/home/')

    return render(request, 'login/user_login.html', {'form': form})


def logout(request):
    request.session.clear()
    return redirect('/')

def user_register(request):
    if request.method == 'GET':
        print('访问了')
        form = User_RegisterForm()
        return render(request, 'login/user_register.html', {'form': form})

    form = User_RegisterForm(request.POST)
    if form.is_valid():
        print("有数据")
        # 保存表单但不提交到数据库
        customer = form.save(commit=False)
        # 保存到数据库
        customer.save()
        return redirect('/customer/login/')
    else:
        return render(request, 'login/user_register.html', {'form': form})