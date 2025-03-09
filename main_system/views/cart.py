from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from main_system import models
from main_system.models import Cart, CartItem, Product, Order, OrderItem, User, HistoryNew
from django.utils import timezone

from main_system.views.order import create_order


# ==========================
# 购物车
# ==========================
def cart_view(request):
    """购物车页面"""
    # 检查用户是否登录
    user_info = request.session.get('customer_info')
    print("购物车页面 - Session信息:", request.session.items())  # 添加调试信息
    
    if not user_info:
        print("购物车页面 - 未找到用户信息，重定向到登录页面")  # 添加调试信息
        messages.error(request, '请先登录')
        return redirect('/customer/login/')
    
    print("购物车页面 - 用户信息:", user_info)  # 添加调试信息
    
    # 获取用户的购物车
    user = User.objects.filter(id=user_info['user_id']).first()
    if not user:
        print("购物车页面 - 用户不存在，重定向到注册页面")  # 添加调试信息
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')
        
    cart = Cart.objects.filter(user=user).first()
    if not cart:
        cart = Cart.objects.create(user=user)
    
    return render(request, 'cart/cart_view.html', {
        'cart': cart,
        'user_info': user_info  # 传递用户信息到模板
    })


def cart_add(request, product_id):
    """添加商品到购物车"""
    # 检查用户是否登录
    user_info = request.session.get('customer_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        # 获取商品
        product = get_object_or_404(Product, id=product_id, status='active')
        
        # 检查库存
        if quantity > product.stock:
            quantity = product.stock
            messages.warning(request, f'商品库存不足，已将数量调整为最大可用库存：{product.stock}')
        
        # 获取或创建购物车
        user = User.objects.filter(id=user_info['user_id']).first()
        if not user:
            messages.error(request, '用户不存在')
            return redirect('/customer/register/')
            
        cart = Cart.objects.filter(user=user).first()
        if not cart:
            cart = Cart.objects.create(user=user)
        
        # 检查商品是否已在购物车中
        cart_item = CartItem.objects.filter(cart=cart, product=product).first()
        if cart_item:
            # 更新数量，确保不超过库存
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock:
                new_quantity = product.stock
                messages.warning(request, f'商品库存不足，已将数量调整为最大可用库存：{product.stock}')
            cart_item.quantity = new_quantity
            cart_item.save()
            messages.success(request, '商品数量已更新')
        else:
            # 创建新的购物车项
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity
            )
            messages.success(request, '商品已添加到购物车')
        
        # 如果是AJAX请求，返回JSON响应
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': '商品已添加到购物车',
                'cart_count': cart.items.count()
            })
        
        # 返回到之前的页面
        return redirect(request.META.get('HTTP_REFERER', '/products/product/collection/'))
    
    return redirect('/products/product/collection/')


def cart_edit(request, cart_item_id):
    """编辑购物车商品数量"""
    # 检查用户是否登录
    user_info = request.session.get('customer_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        # 获取购物车项
        user = User.objects.filter(id=user_info['user_id']).first()
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=user)
        
        # 检查库存
        if quantity > cart_item.product.stock:
            quantity = cart_item.product.stock
            messages.warning(request, f'商品库存不足，已将数量调整为最大可用库存：{cart_item.product.stock}')
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, '商品数量已更新')
        else:
            cart_item.delete()
            messages.success(request, '商品已从购物车中移除')
        
        # 如果是AJAX请求，返回JSON响应
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart = Cart.objects.get(user=user)
            return JsonResponse({
                'status': 'success',
                'message': '购物车已更新',
                'cart_count': cart.items.count(),
                'cart_total': float(cart.get_total_amount())
            })
    
    return redirect('/customer/cart/')


def cart_delete(request, cart_item_id):
    """删除购物车商品"""
    # 检查用户是否登录
    user_info = request.session.get('customer_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')
    
    if request.method == 'POST':
        # 获取购物车项
        user = User.objects.filter(id=user_info['user_id']).first()
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=user)
        cart_item.delete()
        
        messages.success(request, '商品已从购物车中移除')
        
        # 如果是AJAX请求，返回JSON响应
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart = Cart.objects.get(user=user)
            return JsonResponse({
                'status': 'success',
                'message': '商品已删除',
                'cart_count': cart.items.count(),
                'cart_total': float(cart.get_total_amount())
            })
    
    return redirect('/customer/cart/')


def checkout(request):
    """从购物车创建订单并跳转到配送信息页面"""
    # 检查用户是否登录
    user_info = request.session.get('customer_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['user_id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    cart = Cart.objects.filter(user=user).first()
    if not cart or not cart.items.exists():
        messages.error(request, '购物车为空')
        return redirect('/customer/cart/')

    # 调用create_order创建订单
    return create_order(request)