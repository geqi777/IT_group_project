from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from main_system.models import Cart, CartItem, Product, Order, OrderItem, User
from django.utils import timezone


# ==========================
# 购物车
# ==========================
def cart_view(request):
    """显示购物车页面"""
    # 检查用户是否登录
    customer_info = request.session.get('customer_info')
    if not customer_info:
        messages.warning(request, "请先登录后再访问购物车。")
        return redirect('/customer/login/')

    # 获取用户信息
    user = get_object_or_404(User, pk=customer_info['customer_id'])

    # 获取或创建用户的购物车
    cart, created = Cart.objects.get_or_create(user=user)
    return render(request, "cart/cart_view.html", {"cart": cart})


def cart_add(request, product_id):
    """添加商品到购物车"""
    # 检查用户是否登录
    customer_info = request.session.get('customer_info')
    if not customer_info:
        messages.warning(request, "请先登录后再添加商品到购物车。")
        return redirect('/customer/login/')

    # 获取用户信息
    user = get_object_or_404(User, pk=customer_info['customer_id'])
    product = get_object_or_404(Product, id=product_id, status='active')

    # 获取或创建用户的购物车
    cart, created = Cart.objects.get_or_create(user=user)

    # 获取要添加的数量
    quantity = int(request.POST.get('quantity', 1))

    # 检查库存
    if quantity > product.stock:
        messages.warning(request, f"库存不足，当前库存: {product.stock}")
        return redirect(request.META.get('HTTP_REFERER', 'product_page'))

    # 检查购物车中是否已有该商品
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )

    # 如果商品已存在，增加数量
    if not created:
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock:
            messages.warning(request, f"库存不足，当前库存: {product.stock}")
        else:
            cart_item.quantity = new_quantity
            cart_item.save()
            messages.success(request, f"已将 {product.name} 添加到购物车")
    else:
        messages.success(request, f"已将 {product.name} 添加到购物车")

    return redirect(request.META.get('HTTP_REFERER', 'product_page'))


def cart_edit(request, cart_item_id):
    """修改购物车商品数量"""
    # 检查用户是否登录
    customer_info = request.session.get('customer_info')
    if not customer_info:
        messages.warning(request, "请先登录。")
        return redirect('/customer/login/')

    # 获取用户信息
    user = get_object_or_404(User, pk=customer_info['customer_id'])

    # 确保只能修改自己的购物车
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=user)
    quantity = int(request.POST.get('quantity', 1))

    if quantity <= 0:
        cart_item.delete()
        messages.success(request, "商品已从购物车中移除")
    elif quantity > cart_item.product.stock:
        messages.warning(request, f"库存不足，当前库存: {cart_item.product.stock}")
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, "购物车已更新")

    return redirect('cart_view')


def cart_delete(request, cart_item_id):
    """从购物车中删除商品"""
    # 检查用户是否登录
    customer_info = request.session.get('customer_info')
    if not customer_info:
        messages.warning(request, "请先登录。")
        return redirect('/customer/login/')

    # 获取用户信息
    user = get_object_or_404(User, pk=customer_info['customer_id'])

    # 确保只能删除自己的购物车商品
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=user)
    cart_item.delete()
    messages.success(request, "商品已从购物车中移除")
    return redirect('cart_view')


def checkout(request):
    """结算购物车，创建订单"""
    # 检查用户是否登录
    customer_info = request.session.get('customer_info')
    if not customer_info:
        messages.warning(request, "请先登录。")
        return redirect('/customer/login/')

    if request.method != 'POST':
        return redirect('cart_view')

    # 获取用户信息
    user = get_object_or_404(User, pk=customer_info['customer_id'])
    cart = get_object_or_404(Cart, user=user)

    if not cart.items.exists():
        messages.warning(request, "购物车是空的")
        return redirect('cart_view')

    # 检查所有商品的库存
    for item in cart.items.all():
        if item.quantity > item.product.stock:
            messages.error(request, f"{item.product.name} 库存不足，请修改数量")
            return redirect('cart_view')

    # 创建订单
    order = Order.objects.create(
        user=user,
        total_amount=cart.get_total_amount(),
        order_status='pending',
        timestamp=timezone.now()
    )

    # 创建订单项并更新库存
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            subtotal=item.get_subtotal()
        )
        # 更新库存
        item.product.stock -= item.quantity
        item.product.save()

    # 清空购物车
    cart.items.all().delete()

    messages.success(request, f"订单创建成功！订单号: {order.id}")
    return redirect('order_detail', order_id=order.id)