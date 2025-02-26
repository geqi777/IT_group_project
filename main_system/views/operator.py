from main_system import models
from main_system.utils.pagination import PageNumberPagination
from main_system.utils.boostrapModelForm import Operator_ModelForm, Operator_EditForm, ResetPasswordForm, \
    User_EditForm
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
import string, random
from django.utils import timezone
from django.contrib import messages

def operator_list(request):
    data = models.Operator.objects.all()
    # 从请求中获取 page_size，默认为 10
    page_size = request.GET.get('page_size', 20)
    if isinstance(page_size, str) and page_size.isdecimal():  # 确保 page 是字符串
        page_size = int(page_size)
    else:
        page_size = 20  # 设置默认值为 10

    # 创建分页对象并传递 page_size
    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {'page_obj': page_obj.queryset,
               'page_string': page_obj.html(),
               }
    return render(request, 'operation/employee_list.html', context)


def operator_add(request):
    if request.method == 'GET':
        form = Operator_ModelForm()
        return render(request, 'main/change.html', {"form": form})
    #form = Operator_EditForm(request.POST)
    form = Operator_ModelForm(request.POST)

    if form.is_valid():
        form.save()
        return redirect('/operation/employee/list/')
    else:
        print(form.errors)
        return render(request, 'main/change.html', {"form": form})


def operator_edit(request, nid):
    row = models.Operator.objects.filter(id=nid).first()  # 获取需要编辑的员工对象

    if request.method == 'GET':
        # 当 GET 请求时，使用 instance 参数加载现有数据
        form = Operator_EditForm(instance=row)
        return render(request, 'main/change.html', {"form": form})

    # 如果是 POST 请求，则验证和保存提交的数据
    form = Operator_EditForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        return redirect('/operation/employee/list/')

    return render(request, 'main/change.html', {"form": form})


def operator_delete(request, nid):
    operator = models.Operator.objects.filter(id=nid).first()
    if not operator:
        messages.error(request, "Operator not found.")
        return redirect('/operation/employee/list/')

    # if operator.role == "SuperAdmin":
    #     messages.error(request, "Cannot delete Super Admin!")
    #     return redirect('/operation/employee/list/')

    operator.delete()
    messages.success(request, "Operator deleted successfully.")
    return redirect('/operation/employee/list/')


def reset_password(request, nid):
    row = models.Operator.objects.filter(id=nid).first()  # 获取需要编辑的员工对象
    if not row:
        messages.error(request, "The operator does not exist.")
        return redirect('/operation/employee/list/')

    if request.method == 'GET':
        # 当 GET 请求时，使用 instance 参数加载现有数据
        form = ResetPasswordForm()
        return render(request, 'main/change.html', {"form": form})

    # 如果是 POST 请求，则验证和保存提交的数据
    form = ResetPasswordForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        return redirect('/operation/employee/list/')

    return render(request, 'main/change.html', {"form": form})


def operator_profile(request):

    operator_info = request.session.get('info')
    operator_detail = models.Operator.objects.get(pk=operator_info['operator_id'])

    print(operator_detail)

    e_profile_info = {
        'id': operator_detail.id,
        'name': operator_detail.name,
        'date_of_birth': operator_detail.date_of_birth,
        'email': operator_detail.email,
        'phone': operator_detail.phone,
        'address': operator_detail.address,
        'is_operator': operator_detail.is_employee,
        'account': operator_detail.account,
        'role': operator_detail.role,
    }

    return render(request, 'operation/employee_profile.html', {'e_profile': e_profile_info})
