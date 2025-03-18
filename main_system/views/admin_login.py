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
    # print("Form obtained")
    print("admin", md5("Admin123456"))
    if form.is_valid():
        account = form.cleaned_data['account']
        password = form.cleaned_data['password']

        # Find employee object
        employee_obj = models.Operator.objects.filter(account=account).first()
        # print(employee_obj.account, md5(employee_obj.password))
        # Verify if employee object exists and if the password is correct
        if not employee_obj or password != employee_obj.password:
            print('Account or password is incorrect')
            form.add_error('password', 'Account or password is incorrect')
            return render(request, 'login/admin_login.html', {'form': form})

        # Clear any existing session data
        keys_to_clear = ['admin_info', 'info', 'user_info', 'customer_info']
        for key in keys_to_clear:
            if key in request.session:
                del request.session[key]

        # Set session information
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
    """Admin profile page"""
    # Check if admin is logged in
    user_info = request.session.get('admin_info')
    if not user_info:
        return redirect('/operation/login/')
    
    # Get admin information
    user_id = user_info.get('employee_id')
    user = models.Operator.objects.get(id=user_id)
    
    # Handle form submission
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Update profile information
        if action == 'update_profile':
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            
            # Verify email uniqueness
            if models.Operator.objects.filter(email=email).exclude(id=user_id).exists():
                messages.error(request, 'This email is already in use')
            else:
                user.name = name
                user.email = email
                user.phone = phone
                user.save()
                
                # Update user information in session
                user_info['name'] = name
                user_info['email'] = email
                request.session['admin_info'] = user_info
                
                messages.success(request, 'Profile updated successfully')
                return redirect('/operation/profile/')
        
        # Change password
        elif action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Verify current password
            if not user.verify_password(current_password):
                messages.error(request, 'Current password is incorrect')
            # Verify if the new passwords match
            elif new_password != confirm_password:
                messages.error(request, 'The new passwords do not match')
            # Verify new password length
            elif len(new_password) < 6:
                messages.error(request, 'Password must be at least 6 characters long')
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Password changed successfully')
                return redirect('/operation/profile/')
    
    context = {
        'user': user,
        'active_menu': 'profile'
    }
    return render(request, 'operation/admin_profile.html', context)

def admin_logout(request):
    """Admin logout"""
    # Completely clear session data
    request.session.flush()
    
    return redirect('/operation/login/')
