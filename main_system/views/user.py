
from main_system import models
from main_system.utils.pagination import PageNumberPagination
from main_system.utils.boostrapModelForm import User_ModelForm, User_EditForm, ResetPasswordForm
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.utils import timezone
from django.contrib import messages

def user_list(request):
    """ 获取用户列表，支持分页 """
    data = models.User.objects.all().order_by("-create_time")  # 按创建时间倒序排列
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
    return render(request, 'user/user_list.html', context)


def user_add(request):
    """ 添加新用户 """
    if request.method == 'GET':
        form = User_ModelForm()
        return render(request, 'main/user_change.html', {"form": form})

    form = User_ModelForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "New user added successfully.")
        return redirect('/user/list/')

    return render(request, 'main/user_change.html', {"form": form})


def user_edit(request, nid):
    """ 编辑用户信息 """
    row = models.User.objects.filter(id=nid).first()

    if not row:
        messages.error(request, "The user does not exist.")
        return redirect('/user/list/')

    if request.method == 'GET':
        form = User_EditForm(instance=row)
        return render(request, 'main/user_change.html', {"form": form})

    form = User_EditForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        messages.success(request, "User information updated successfully.")
        return redirect('/user/list/')

    return render(request, 'main/user_change.html', {"form": form})


def user_delete(request, nid):
    """ 删除用户，确保不能删除管理员账号 """
    user = models.User.objects.filter(id=nid).first()

    if not user:
        messages.error(request, "User not found.")
        return redirect('/user/list/')

    if user.account == "admin":  # 防止误删管理员账户
        messages.error(request, "Cannot delete administrator account!")
        return redirect('/user/list/')

    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect('/user/list/')


def reset_password(request, nid):
    """ 重置用户密码 """
    row = models.User.objects.filter(id=nid).first()

    if not row:
        messages.error(request, "User not found.")
        return redirect('/user/list/')

    if request.method == 'GET':
        form = ResetPasswordForm()
        return render(request, 'main/user_change.html', {"form": form})

    form = ResetPasswordForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        messages.success(request, "User password reset successfully.")
        return redirect('/user/list/')

    return render(request, 'main/user_change.html', {"form": form})


def user_profile(request):
    """ 显示用户个人信息 """
    user_info = request.session.get('info')

    user_detail = models.User.objects.get(pk=user_info['user_id'])

    profile_info = {
        'id': user_detail.id,
        'name': user_detail.name,
        'date_of_birth': user_detail.date_of_birth,
        'email': user_detail.email,
        'phone': user_detail.phone,
        'address': user_detail.address,
        'account': user_detail.account,
    }

    return render(request, 'user/user_profile.html', {'profile': profile_info})
