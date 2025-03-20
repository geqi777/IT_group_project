from main_system import models
from main_system.utils.pagination import PageNumberPagination
from main_system.utils.boostrapModelForm import User_ModelForm, User_EditForm, ResetPasswordForm
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from main_system.views.admin_dashboard import admin_message

@admin_message
def user_list(request):
    """ Get user list with pagination support """
    data = models.User.objects.all().order_by("-create_time")  # Order by creation time descending
    page_size = request.GET.get('page_size', 20)

    if isinstance(page_size, str) and page_size.isdecimal():
        page_size = int(page_size)
    else:
        page_size = 20

    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {
        'page_obj': page_obj.queryset,
        'page_string': page_obj.html(),
    }
    return render(request, 'operation/admin_user_list.html', context)


@admin_message
def user_add(request):
    """ Add new user """
    if request.method == 'GET':
        form = User_ModelForm()
        return render(request, 'operation/admin_user_add.html', {"form": form})

    form = User_ModelForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "New user added successfully.")
        return redirect('/operation/homepage/users/')

    return render(request, 'operation/admin_user_add.html', {"form": form})


@admin_message
def user_edit(request, nid):
    """ Edit user information """
    row = models.User.objects.filter(id=nid).first()

    if not row:
        messages.error(request, "The user does not exist.")
        return redirect('/user/list/')

    if request.method == 'GET':
        form = User_EditForm(instance=row)
        return render(request, 'main/operation_change.html', {"form": form})

    form = User_EditForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        messages.success(request, "User information updated successfully.")
        return redirect('/operation/homepage/users/')

    return render(request, 'main/operation_change.html', {"form": form})


@admin_message
def user_delete(request, nid):
    """ Delete user """
    user = models.User.objects.filter(id=nid).first()
    if not user:
        messages.error(request, "User not found.")
        return redirect('/operation/homepage/users/')

    if user.id == 1:
        messages.error(request, "Cannot delete administrator account!")
        return redirect('/operation/homepage/users/')

    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect('/operation/homepage/users/')


@admin_message
def reset_password(request, nid):
    """ Reset user password """
    row = models.User.objects.filter(id=nid).first()
    if not row:
        messages.error(request, "User not found.")
        return redirect('/operation/homepage/users/')

    if request.method == 'GET':
        form = ResetPasswordForm()
        return render(request, 'main/user_change.html', {"form": form})

    form = ResetPasswordForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        messages.success(request, "User password reset successfully.")
        return redirect('/operation/homepage/users/')

    return render(request, 'main/user_change.html', {"form": form})



