from main_system import models
from main_system.utils.pagination import PageNumberPagination
from main_system.utils.boostrapModelForm import Employee_ModelForm, Employee_EditForm, ResetPasswordForm, \
    Customer_EditForm
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
import string, random
from django.utils import timezone
from django.contrib import messages

def admin_list(request):
    data = models.Employee.objects.all()
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


def employee_add(request):
    if request.method == 'GET':
        form = Employee_ModelForm()
        return render(request, 'main/change.html', {"form": form})
    form = Employee_ModelForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect('/operation/employee/list/')
    else:
        print(form.errors)
        return render(request, 'main/change.html', {"form": form})


def employee_edit(request, nid):
    row = models.Employee.objects.filter(id=nid).first()  # 获取需要编辑的员工对象

    if request.method == 'GET':
        # 当 GET 请求时，使用 instance 参数加载现有数据
        form = Employee_EditForm(instance=row)
        return render(request, 'main/change.html', {"form": form})

    # 如果是 POST 请求，则验证和保存提交的数据
    form = Employee_EditForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        return redirect('/operation/employee/list/')

    return render(request, 'main/change.html', {"form": form})


def employee_delete(request, nid):
    models.Employee.objects.filter(id=nid).delete()
    return redirect('/operation/employee/list/')


def reset_password(request, nid):
    row = models.Employee.objects.filter(id=nid).first()  # 获取需要编辑的员工对象
    if row is None:
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


def employee_profile(request):

    employee_info = request.session.get('info')
    employee_detail = models.Employee.objects.get(pk=employee_info['employee_id'])

    print(employee_detail)

    e_profile_info = {
        'id': employee_detail.id,
        'name': employee_detail.name,
        'email': employee_detail.email,
        'phone': employee_detail.phone,
        'date_of_birth': employee_detail.date_of_birth,
        'address': employee_detail.address,
        'is_employee': employee_detail.is_employee,
        'account': employee_detail.account,
        'role': employee_detail.role,
        'department': employee_detail.department,
    }

    return render(request, 'operation/employee_profile.html', {'e_profile': e_profile_info})
