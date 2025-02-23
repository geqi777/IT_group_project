from datetime import timezone

from main_system import models
from main_system.utils.pagination import PageNumberPagination
from main_system.utils.boostrapModelForm import Employee_ModelForm, Employee_EditForm, ResetPasswordForm, \
    Customer_EditForm, LicenseVerificationForm
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
import string, random
from django.utils import timezone
from django.contrib import messages
# 1111
def employee_list(request):
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


def o_customer_list(request):
    data = models.Customer.objects.all()
    # 从请求中获取 page_size，默认为 10
    page_size = request.GET.get('page_size', 20)
    if isinstance(page_size, str) and page_size.isdecimal():  # 确保 page 是字符串
        page_size = int(page_size)
    else:
        page_size = 20  # 设置默认值为 5
    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {'page_obj': page_obj.queryset,
               'page_string': page_obj.html(),
               }
    return render(request, 'operation/c_list.html', context)


def o_customer_edit(request, nid):
    # 使用 get() 直接获取单个对象，不需要 .first()
    row = models.Customer.objects.get(id=nid)  # 获取需要编辑的用户账户

    if request.method == 'GET':
        form = Customer_EditForm(instance=row)
        return render(request, 'main/change.html', {'form': form})

    form = Customer_EditForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        return redirect('/operation/customer/list/')

    return render(request, 'main/change.html', {'form': form})


def o_customer_delete(request, nid):
    # 删除用户
    models.Customer.objects.get(id=nid).delete()
    return redirect('/operation/customer/list/')


def o_customer_reset_password(request, nid):
    # 使用 get() 直接获取单个对象，不需要 .first()
    row = models.Customer.objects.get(id=nid)  # 获取需要编辑的用户对象
    if row is None:
        return redirect('/operation/customer/list/')

    if request.method == 'GET':
        form = ResetPasswordForm()
        return render(request, 'main/change.html', {'form': form})

    form = ResetPasswordForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        return redirect('/operation/customer/list/')

    return render(request, 'main/change.html', {'form': form})

def o_customer_verified(request, nid):
    # 获取客户信息
    row = models.Customer.objects.get(id=nid)  # 获取需要编辑的用户对象
    if request.method == 'POST':
        form = LicenseVerificationForm(request.POST, request.FILES, instance=row)
        if form.is_valid():
            form.save()  # 保存表单
            return redirect('/operation/customer/list/')  # 验证后跳转到客户列表
    else:
        form = LicenseVerificationForm(instance=row)

    return render(request, 'operation/o_verified_c.html', {'form': form, 'customer': row})


def coupons_list(request):
    coupons = models.Coupon.objects.all()
    return render(request, 'operation/coupon_list.html', {'coupons': coupons})

def coupon_add(request):
    if request.method == 'POST':
        num_codes = int(request.POST.get('num_codes', 5))
        discount = float(request.POST.get('discount', 2.5))
        min_order_value = float(request.POST.get('min_order_value', 20))
        expiry_days = int(request.POST.get('expiry_days', 30))

        today = timezone.now().date()
        expiry_date = today + timezone.timedelta(days=expiry_days)  # expiry_days=30

        for _ in range(num_codes):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            # discount = random.choice([2.5, 5, 7.5, 10])
            # min_order_value = random.choice([20, 25, 30])
            models.Coupon.objects.create(
                code=code,
                discount=discount,
                expiry_date=expiry_date,
                min_order_value=min_order_value
            )

        return redirect('/operation/coupon/list/')

def coupon_edit(request, coupon_id):
    # 使用 get() 直接获取单个对象，不需要 .first()
    coupon = models.Coupon.objects.get(id=coupon_id)  # !get不到coupon_id

    if request.method == 'POST':
        coupon.discount = request.POST['discount']
        coupon.expiry_date = request.POST['expiry_date']
        coupon.min_order_value = request.POST['min_order_value']
        coupon.save()
        return redirect('/operation/coupon/list/')

    return render(request, 'operation/coupon_list_edit.html', {'coupon': coupon})

def coupon_delete(request, coupon_id):
    coupon = models.Coupon.objects.get(id=coupon_id)  # !get不到coupon_id
    coupon.delete()
    messages.success(request, 'Code deleted successfully')
    return redirect('/operation/coupon/list/')