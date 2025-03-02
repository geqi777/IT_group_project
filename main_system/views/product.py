from datetime import timezone
from main_system import models
from main_system.models import Product
from main_system.utils.pagination import PageNumberPagination
from main_system.utils.boostrapModelForm import Product_ModelForm, Product_EditForm
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Case, When, IntegerField
from django.utils import timezone
import string, random
from django.contrib import messages
from django.core.paginator import Paginator
# from django.contrib.auth.decorators import  login_required


# ==========================
# 管理员端功能
# ==========================
# 1-1
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
    """ 商品浏览页 + 筛选 + 排序 """
    # 获取筛选参数
    query = request.GET.get('q', '')
    categories = request.GET.getlist('category', [])
    sort_by = request.GET.get('sort', 'newest')
    price_range = request.GET.get('price_range', 'any')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    # 基础查询：只显示激活状态的商品
    products = Product.objects.filter(status='active')

    # 应用搜索过滤
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    # 应用类别过滤
    if categories:
        products = products.filter(category__in=categories)

    # 应用价格过滤
    if price_range != 'any':
        if price_range == 'custom' and price_min and price_max:
            products = products.filter(price__gte=float(price_min), price__lte=float(price_max))
        elif price_range != 'custom':
            price_min, price_max = price_range.split(',')
            if price_min:
                products = products.filter(price__gte=float(price_min))
            if price_max:
                products = products.filter(price__lte=float(price_max))

    # 应用排序
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_time')
    elif sort_by == 'relevance' and query:  # 只在有搜索查询时应用相关性排序
        products = products.annotate(
            relevance=Case(
                When(name__icontains=query, then=2),  # 名称匹配权重更高
                When(description__icontains=query, then=1),  # 描述匹配权重较低
                default=0,
                output_field=IntegerField(),
            )
        ).order_by('-relevance', '-created_time')
    else:  # 默认按最新排序
        products = products.order_by('-created_time')

    # 分页
    page_number = request.GET.get('page', 1)
    paginator = Paginator(products, 9)  # 每页显示9个商品
    page_obj = paginator.get_page(page_number)

    # 准备分类选项
    all_categories = [{'key': key, 'name': name} for key, name in Product.CATEGORY_CHOICES]

    context = {
        'products': page_obj,
        'categories': all_categories,
        'selected_categories': categories,
        'current_sort': sort_by,
        'selected_price_range': price_range,
    }

    return render(request, 'products/product_page.html', context)


def product_detail(request, product_id):
    """用户查看商品详情（包含库存信息）"""
    product = get_object_or_404(Product, id=product_id, status='active')
    quantity_range = range(1, product.stock + 1) if product.stock > 0 else []
    return render(request, 'products/product_detail.html', {'product': product, 'quantity_range': quantity_range})


def search_products(request):
    """搜索商品"""
    query = request.GET.get('q', '')
    if query:
        # 从名称和类别中搜索
        products = Product.objects.filter(
            Q(name__icontains=query) |  # 名称包含关键词
            Q(category__icontains=query)  # 类别包含关键词
        ).filter(status='active').distinct()  # 只显示激活状态的商品
    else:
        products = Product.objects.filter(status='active')

    # 分页
    paginator = Paginator(products, 12)  # 每页12个商品
    page = request.GET.get('page')
    products = paginator.get_page(page)

    return render(request, 'products/product_page.html', {
        'products': products,
        'search_query': query,
        'categories': [{'key': key, 'name': name} for key, name in Product.CATEGORY_CHOICES]  # 添加分类选项
    })


