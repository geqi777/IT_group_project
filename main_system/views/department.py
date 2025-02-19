from django.shortcuts import render, redirect
from main_system import models
from main_system.utils.pagination import PageNumberPagination

def department_list(request):
    data = models.Department.objects.all()
    page_obj = PageNumberPagination(request, data)
    context = {
        'data': page_obj.queryset,  # 将 'page_obj.queryset' 更改为 'data'
        'page_string': page_obj.html()
    }
    return render(request, 'operation/department_list.html', context)


def department_add(request):
    if request.method == 'GET':
        return render(request, 'operation/d_list_add.html')

    data = request.POST.get('department')

    models.Department.objects.create(
        name=data,
    )
    return redirect('/operation/department/list/')


def department_delete(request, nid):
    models.Department.objects.filter(id=nid).delete()
    return redirect(f'/operation/department/list/')


def department_edit(request, nid):
    if request.method == 'GET':
        data = models.Department.objects.filter(id=nid).first()
        return render(request, 'operation/d_list_edit.html', {"data": data})

    new_department = request.POST.get('department')
    models.Department.objects.filter(id=nid).update(name=new_department)
    return redirect('/operation/department/list/')
