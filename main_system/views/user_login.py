from django import forms
from django.shortcuts import render, redirect, HttpResponse
from main_system.utils.boostrapModelForm import BoostrapForm, User_RegisterForm
from main_system.utils.encrypt import md5
from main_system import models
from django.contrib import messages
from main_system.models import Order

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
    """用户个人资料页面"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        return redirect('/customer/login/')
    
    # 获取用户信息
    user_id = user_info.get('id')
    user = models.User.objects.get(id=user_id)
    
    # 获取用户钱包信息
    wallet = models.Wallet.objects.filter(user_id=user_id).first()
    if not wallet:
        wallet = models.Wallet.objects.create(user_id=user_id, balance=0, points=0)
    
    # 获取最近5个订单
    recent_orders = Order.objects.filter(user_id=user_id).order_by('-timestamp')[:5]
    
    # 处理表单提交
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # 更新个人信息
        if action == 'update_profile':
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            
            # 验证邮箱唯一性
            if models.User.objects.filter(email=email).exclude(id=user_id).exists():
                messages.error(request, '该邮箱已被使用')
            else:
                user.name = name
                user.email = email
                user.phone = phone
                user.address = address
                user.save()
                
                # 更新会话中的用户信息
                user_info['name'] = name
                user_info['email'] = email
                request.session['user_info'] = user_info
                
                messages.success(request, '个人信息更新成功')
                return redirect('/customer/profile/')
        
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
                return redirect('/customer/profile/')
    
    context = {
        'user': user,
        'wallet': wallet,
        'recent_orders': recent_orders
    }
    return render(request, 'customer/profile.html', context)

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

        # 清除可能存在的旧会话数据
        keys_to_clear = ['admin_info', 'info', 'user_info', 'customer_info']
        for key in keys_to_clear:
            if key in request.session:
                del request.session[key]

        # 设置 session 信息
        request.session['user_info'] = {
            'id': user_obj.id,
            'account': user_obj.account,
            'name': user_obj.name,
            'email': user_obj.email
        }
        
        # 设置session过期时间为7天
        request.session.set_expiry(7 * 24 * 60 * 60)
        
        # 确保session被保存
        request.session.modified = True

        print('用户登录成功:', request.session['user_info'])
        
        # 获取来源页面，如果没有则默认跳转到首页
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('/home/')

    return render(request, 'login/user_login.html', {'form': form})

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

def user_logout(request):
    """用户退出登录"""
    # 完全清除会话数据
    request.session.flush()
    
    messages.success(request, '已成功退出登录')
    return redirect('/customer/login/')