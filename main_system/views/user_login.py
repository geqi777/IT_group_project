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
    """User profile page"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        return redirect('/customer/login/')
    
    # Get user information
    user_id = user_info.get('id')
    user = models.User.objects.get(id=user_id)
    
    # Get user wallet information
    wallet = models.Wallet.objects.filter(user_id=user_id).first()
    if not wallet:
        wallet = models.Wallet.objects.create(user_id=user_id, balance=0, points=0)
    
    # Get the last 5 orders
    recent_orders = Order.objects.filter(user_id=user_id).order_by('-timestamp')[:5]
    
    # Handle form submission
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Update profile information
        if action == 'update_profile':
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            
            # Validate email uniqueness
            if models.User.objects.filter(email=email).exclude(id=user_id).exists():
                messages.error(request, 'This email is already in use')
            else:
                user.name = name
                user.email = email
                user.phone = phone
                user.address = address
                user.save()
                
                # Update user information in session
                user_info['name'] = name
                user_info['email'] = email
                request.session['user_info'] = user_info
                
                messages.success(request, 'Profile updated successfully')
                return redirect('/customer/profile/')
        
        # Change password
        elif action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validate current password
            if not user.verify_password(current_password):
                messages.error(request, 'Current password is incorrect')
            # Validate if the new passwords match
            elif new_password != confirm_password:
                messages.error(request, 'The new passwords do not match')
            # Validate new password length
            elif len(new_password) < 6:
                messages.error(request, 'Password must be at least 6 characters long')
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Password changed successfully')
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

        # Find user object
        user_obj = models.User.objects.filter(account=account).first()
        # Validate if user object exists and password is correct
        if not user_obj or password != user_obj.password:
            form.add_error('password', 'Account or password is incorrect')
            return render(request, 'login/user_login.html', {'form': form})

        # Clear any existing session data
        keys_to_clear = ['admin_info', 'info', 'user_info', 'customer_info']
        for key in keys_to_clear:
            if key in request.session:
                del request.session[key]

        # Set session information
        request.session['user_info'] = {
            'id': user_obj.id,
            'account': user_obj.account,
            'name': user_obj.name,
            'email': user_obj.email
        }
        
        # Set session expiry to 7 days
        request.session.set_expiry(7 * 24 * 60 * 60)
        
        # Ensure session is saved
        request.session.modified = True

        print('User logged in successfully:', request.session['user_info'])
        
        # Get the referring page, default to homepage if not available
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('/home/')

    return render(request, 'login/user_login.html', {'form': form})

def user_register(request):
    if request.method == 'GET':
        print('Accessed')
        form = User_RegisterForm()
        return render(request, 'login/user_register.html', {'form': form})

    form = User_RegisterForm(request.POST)
    if form.is_valid():
        print("Data present")
        # Save form but do not commit to database
        customer = form.save(commit=False)
        # Save to database
        customer.save()
        return redirect('/customer/login/')
    else:
        return render(request, 'login/user_register.html', {'form': form})

def user_logout(request):
    """User logout"""
    # Completely clear session data
    request.session.flush()
    
    messages.success(request, 'Logged out successfully')
    return redirect('/customer/login/')