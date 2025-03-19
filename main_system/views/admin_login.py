from django import forms
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from main_system.utils.boostrapModelForm import BoostrapForm, AdminLoginForm, AdminProfileForm
from main_system.utils.encrypt import md5
from main_system import models
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from main_system.views.admin_dashboard import admin_message

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

# Admin login
def admin_login(request):
    """Admin login page"""
    
    if request.method == 'GET':
        form = AdminLoginForm()
        return render(request, 'operation/admin_login.html', {'form': form})

    form = AdminLoginForm(data=request.POST)
    if form.is_valid():
        admin_account = form.cleaned_data.get('account')
        admin_password = form.cleaned_data.get('password')
        
        # Get admin account and verify
        admin = models.Operator.objects.filter(account=admin_account).first()
        if not admin:
            form.add_error('account', 'This account does not exist')
            return render(request, 'operation/admin_login.html', {'form': form})
        
        # Verify password 
        if not admin.verify_password(admin_password):
            form.add_error('password', 'Incorrect password')
            return render(request, 'operation/admin_login.html', {'form': form})
        
        # Verification passed, store info in session
        request.session["admin_info"] = {
            'employee_id': admin.id,
            'name': admin.name,
            'role': admin.role,
            'is_operator': admin.is_operator
        }
        request.session.set_expiry(60 * 60 * 24)  # Session expires in 24 hours
        
        # Redirect to admin dashboard
        return redirect('/operation/homepage/')
        
    return render(request, 'operation/admin_login.html', {'form': form})


def logout(request):
    request.session.clear()
    return redirect('/')

# Admin profile
@admin_message
def admin_profile(request):
    """Admin profile page"""
    
    # Get admin ID from session
    admin_id = request.session.get('admin_info')
    if not admin_id or not admin_id.get('employee_id'):
        return redirect('/operation/login/')
    
    # Get admin object
    admin = get_object_or_404(models.Operator, id=admin_id.get('employee_id'))
    
    if request.method == 'GET':
        form = AdminProfileForm(instance=admin)
        return render(request, 'operation/admin_profile.html', {'form': form})
    
    # POST request - update admin profile
    form = AdminProfileForm(data=request.POST, instance=admin)
    if form.is_valid():
        form.save()
        
        # Update session info
        request.session["admin_info"] = {
            'employee_id': admin.id,
            'name': admin.name,
            'role': admin.role,
            'is_operator': admin.is_operator
        }
        
        request.admin_messages.success('Profile updated successfully')
        return redirect('/operation/profile/')
    
    return render(request, 'operation/admin_profile.html', {'form': form})

# Admin logout
@admin_message
def admin_logout(request):
    """Admin logout"""
    
    # Clear admin session
    if 'admin_info' in request.session:
        # del request.session['admin_info']
        request.session.flush()
    
    return redirect('/operation/login/')
