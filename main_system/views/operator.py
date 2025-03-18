from main_system import models
from main_system.utils.pagination import PageNumberPagination
from main_system.utils.boostrapModelForm import Operator_ModelForm, Operator_EditForm, ResetPasswordForm
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib import messages

def operator_list(request):
    data = models.Operator.objects.all()
    # Get page_size from request, default is 20
    page_size = request.GET.get('page_size', 20)
    if isinstance(page_size, str) and page_size.isdecimal():  # Ensure page is a string
        page_size = int(page_size)
    else:
        page_size = 20  # Set default value to 20

    # Create pagination object and pass page_size
    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {'page_obj': page_obj.queryset,
               'page_string': page_obj.html(),
               }
    return render(request, 'operation/admin_operator_list.html', context)


def operator_add(request):
    if request.method == 'GET':
        form = Operator_ModelForm()
        return render(request, 'operation/admin_operator_add.html', {"form": form})

    form = Operator_ModelForm(request.POST)

    if form.is_valid():
        form.save()
        messages.success(request, "New admin added successfully.")
        return redirect('/operation/homepage/admins/')
    else:
        print(form.errors)
        return render(request, 'operation/admin_operator_add.html', {"form": form})


def operator_edit(request, nid):
    row = models.Operator.objects.filter(id=nid).first()  # Get the employee object to be edited

    if request.method == 'GET':
        # When GET request, use instance parameter to load existing data
        form = Operator_EditForm(instance=row)
        return render(request, 'main/change.html', {"form": form})

    # If it's a POST request, validate and save the submitted data
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
    row = models.Operator.objects.filter(id=nid).first()  # Get the employee object to be edited
    if not row:
        messages.error(request, "The operator does not exist.")
        return redirect('/operation/employee/list/')

    if request.method == 'GET':
        # When GET request, use instance parameter to load existing data
        form = ResetPasswordForm()
        return render(request, 'main/change.html', {"form": form})

    # If it's a POST request, validate and save the submitted data
    form = ResetPasswordForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        return redirect('/operation/employee/list/')

    return render(request, 'main/change.html', {"form": form})
