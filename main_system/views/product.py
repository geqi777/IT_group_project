from datetime import timezone
from main_system import models
from main_system.models import Product
from main_system.utils.pagination import PageNumberPagination
from main_system.utils.boostrapModelForm import Product_ModelForm, Product_EditForm
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
import string, random
from django.contrib import messages


# ==========================
# 管理员端功能
# ==========================

def product_list(request):
    """ 查看并管理商品列表 """
    data = models.Product.objects.all()

    # 从请求中获取 page_size，默认为 20
    page_size = request.GET.get('page_size', 20)
    if isinstance(page_size, str) and page_size.isdecimal():  # 确保 page_size 是数字
        page_size = int(page_size)
    else:
        page_size = 20  # 设置默认值

    # 创建分页对象并传递 page_size
    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {'page_obj': page_obj.queryset,
               'page_string': page_obj.html(),
               }
    return render(request, 'products/product_list.html', context)


def product_add(request):
    """ 添加新商品 """
    if request.method == 'GET':
        form = Product_ModelForm()
        return render(request, 'main/change.html', {"form": form})

    form = Product_ModelForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        messages.success(request, "Product added successfully.")
        return redirect('/operator/product/list/')

    return render(request, 'main/change.html', {"form": form})


def product_edit(request, product_id):
    """ 编辑商品 """

    row = models.Product.objects.filter(id=product_id).first()  # 获取需要编辑的产品对象

    if request.method == 'GET':
        form = Product_EditForm(instance=row)
        return render(request, 'main/change.html', {"form": form})

    form = Product_EditForm(request.POST, request.FILES, instance=row)
    if form.is_valid():
        form.save()
        messages.success(request, "Product edited successfully.")
        return redirect('/operator/product/list/')

    return render(request, 'main/change.html', {"form": form})


def product_delete(request, product_id):
    """ 删除商品 """
    models.Product.objects.filter(id=product_id).delete()
    return redirect('/operator/product/list/')


# ==========================
# 用户端功能
# ==========================

def product_page(request):
    """ 商品浏览页 + 筛 + 排 """
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'newest')

    products = Product.objects.filter(status='Active')

    if query:
        products = products.filter(name__icontains=query)

    if category:
        products = products.filter(category__name__icontains=category)

    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_time')

    return render(request, 'products/product_page.html', {'image': products, 'query': query, 'sort_by': sort_by})


def product_detail(request, product_id):
    """用户查看商品详情（包含库存信息）"""
    product = get_object_or_404(Product, id=product_id, status='active')
    quantity_range = range(1, product.stock + 1) if product.stock > 0 else []
    return render(request, 'products/product_detail.html', {'product': product, 'quantity_range': quantity_range})
