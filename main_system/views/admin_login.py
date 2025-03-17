from django import forms
from django.shortcuts import render, redirect, HttpResponse
from main_system.utils.boostrapModelForm import BoostrapForm
from main_system.utils.encrypt import md5
from main_system import models
from django.contrib import messages

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

        # 清除可能存在的旧会话数据
        keys_to_clear = ['admin_info', 'info', 'user_info', 'customer_info']
        for key in keys_to_clear:
            if key in request.session:
                del request.session[key]

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

def admin_profile(request):
    """管理员个人资料页面"""
    # 检查管理员是否登录
    user_info = request.session.get('admin_info')
    if not user_info:
        return redirect('/operation/login/')
    
    # 获取管理员信息
    user_id = user_info.get('employee_id')
    user = models.Operator.objects.get(id=user_id)
    
    # 处理表单提交
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # 更新个人信息
        if action == 'update_profile':
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            
            # 验证邮箱唯一性
            if models.Operator.objects.filter(email=email).exclude(id=user_id).exists():
                messages.error(request, '该邮箱已被使用')
            else:
                user.name = name
                user.email = email
                user.phone = phone
                user.save()
                
                # 更新会话中的用户信息
                user_info['name'] = name
                user_info['email'] = email
                request.session['admin_info'] = user_info
                
                messages.success(request, '个人信息更新成功')
                return redirect('/operation/profile/')
        
        # 修改密码
        elif action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # 验证当前密码
            if not user.verify_password(current_password):
                messages.error(request, '当前密码不正确')
            # 验证两次输入的新密码是否一致
            elif new_password != confirm_password:
                messages.error(request, '两次输入的新密码不一致')
            # 验证新密码长度
            elif len(new_password) < 6:
                messages.error(request, '密码长度不能少于6个字符')
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, '密码修改成功')
                return redirect('/operation/profile/')
    
    context = {
        'user': user,
        'active_menu': 'profile'
    }
    return render(request, 'operation/admin_profile.html', context)

def admin_logout(request):
    """管理员退出登录"""
    # 完全清除会话数据
    request.session.flush()
    
    return redirect('/operation/login/')

