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
# from django.contrib.auth.decorators import  login_required


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


# ==========================
# 购物车
# ==========================

# 添加商品到购物车
# @login_required
def cart_add(request, product_id):
    product = models.Product.objects.filter(id=product_id)

    # 获取当前用户购物车
    cart, created = models.Cart.objects.get_or_create(user=request.user)

    # 检查是否已在购物车中
    cart_item, created = models.CartItem.objects.get_or_create(cart=cart, product=product)

    # 计算新数量
    new_quantity = cart_item.quantity + 1

    # 确保新数量不超过库存
    if new_quantity > product.stock:
        messages.warning(request, f"Stock limit reached: Only {product.stock} available.")
    else:
        cart_item.quantity = new_quantity
        cart_item.save()
        messages.success(request, f"{product.name} added to cart!")

    return redirect(request.META.get('HTTP_REFERER', 'cart_view'))  # 返回上一个页面


# 购物车视图 + 增减商品数量
# @login_required
def cart_view(request):
    """ 显示购物车 """
    if not request.user.is_authenticated:
        messages.warning(request, "Please log in to access the cart.")
        return redirect("login")

    cart, created = models.Cart.objects.get_or_create(user=request.user)
    return render(request, "cart/cart_view.html", {"cart": cart})


# 更新购物车数量
# @login_required
def cart_edit(request, cart_item_id):
    cart_item = models.CartItem.objects.filter(id=cart_item_id, cart__user=request.user)

    if request.method == "POST":
        new_quantity = int(request.POST.get("quantity", 1))
        if new_quantity > 0:
            cart_item.quantity = new_quantity
            cart_item.save()
        else:
            cart_item.delete()  # 如果数量变为 0，则删除该商品

    return redirect("cart_view")


# 移除购物项
# @login_required
def cart_delete(request, cart_item_id):
    cart_item = models.CartItem.objects.filter(id=cart_item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect("cart_view")


# ==========================
# 订单
# ==========================

# 提交订单
# @login_required
def checkout(request):
    cart = get_object_or_404(models.Cart, user=request.user)

    if not cart.items.exists():
        messages.warning(request, "Your cart is empty!")
        return redirect("cart_view")

    # <实现支付逻辑>--unfinished
    messages.success(request, "Order placed successfully!")
    cart.items.all().delete()  # 清空购物车

    return redirect("home")
