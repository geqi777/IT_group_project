from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required

from ..models import Order, OrderItem, Cart, CartItem, User, WalletTransaction, HistoryNew, Operator


def create_order(request):
    """从购物车创建订单"""
    # 检查用户是否登录
    user_id = request.session.get('info')
    if not user_id:
        messages.error(request, '请先登录')
        return redirect('login')

    user = User.objects.filter(id=user_id).first()
    cart = Cart.objects.filter(user=user).first()
    if not cart or not cart.items.exists():
        messages.error(request, '购物车为空，无法创建订单')
        return redirect('cart_view')

    try:
        with transaction.atomic():
            # 创建订单
            order = Order.objects.create(
                user=user,
                total_amount=cart.get_total_amount(),
                final_amount=cart.get_total_amount(),  # 暂时不考虑优惠
                shipping_address=user.address or ''
            )

            # 创建订单项
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                    subtotal=cart_item.get_subtotal()
                )

            # 记录历史
            HistoryNew.objects.create(
                user=user,
                order=order,
                history_type='order_created',
                amount=order.total_amount,
                details=f'创建订单：{order.order_number}'
            )

            # 清空购物车
            cart.items.all().delete()

            messages.success(request, f'订单创建成功，订单号：{order.order_number}')
            return redirect('order_detail', order_id=order.id)

    except Exception as e:
        messages.error(request, f'订单创建失败：{str(e)}')
        return redirect('cart_view')


def order_list(request):
    """订单列表"""
    # 检查用户是否登录
    user_id = request.session.get('info')
    if not user_id:
        messages.error(request, '请先登录')
        return redirect('login')

    user = User.objects.filter(id=user_id).first()
    orders = Order.objects.filter(user=user).order_by('-timestamp')

    # 分页
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)

    return render(request, 'orders/order_list.html', {
        'orders': orders
    })

# 1
def admin_order_list(request):
    """管理员查看所有订单"""
    # 检查管理员是否登录
    operator_id = request.session.get(Operator,'operator_info')
    if not operator_id:
        messages.error(request, '请先登录')
        return redirect('operator_login')

    # 验证是否是管理员
    operator = Operator.objects.filter(id=operator_id, is_operator=True).first()
    if not operator:
        messages.error(request, '权限不足')
        return redirect('operator_login')

    # 获取所有订单项
    order_items = OrderItem.objects.select_related('order', 'order__user', 'product').all().order_by(
        '-order__timestamp')

    # 分页
    paginator = Paginator(order_items, 20)
    page = request.GET.get('page')
    order_items = paginator.get_page(page)

    return render(request, 'orders/admin_order_list.html', {
        'order_items': order_items,
        'operator': operator  # 传递管理员信息到模板
    })


def order_detail(request, order_id):
    """订单详情"""
    # 检查用户是否登录
    user_id = request.session.get('info')
    if not user_id:
        messages.error(request, '请先登录')
        return redirect('login')

    user = User.objects.filter(id=user_id).first()
    order = get_object_or_404(Order, id=order_id, user=user)

    if request.method == 'POST':
        # 处理订单操作
        action = request.POST.get('action')

        if action == 'cancel':
            if order.order_status == 'pending':
                order.order_status = 'cancelled'
                order.save()

                # 记录历史
                HistoryNew.objects.create(
                    user=user,
                    order=order,
                    history_type='order_cancelled',
                    amount=order.final_amount,
                    details='用户取消订单'
                )

                messages.success(request, '订单已取消')
            else:
                messages.error(request, '当前订单状态无法取消')

        elif action == 'pay':
            if order.order_status == 'pending':
                # 处理支付逻辑
                payment_method = request.POST.get('payment_method')
                if payment_method == 'wallet':
                    if user.wallet.balance >= order.final_amount:
                        with transaction.atomic():
                            # 扣除钱包余额
                            user.wallet.balance -= order.final_amount
                            user.wallet.save()

                            # 更新订单状态
                            order.payment_method = 'wallet'
                            order.payment_status = True
                            order.order_status = 'paid'
                            order.paid_time = timezone.now()
                            order.save()

                            # 记录历史
                            HistoryNew.objects.create(
                                user=user,
                                order=order,
                                history_type='order_paid',
                                amount=order.final_amount,
                                details=f'钱包支付订单：{order.order_number}'
                            )

                            # 记录钱包交易
                            WalletTransaction.objects.create(
                                wallet=user.wallet,
                                transaction_type='purchase',
                                amount=order.final_amount,
                                details=f'订单支付：{order.order_number}'
                            )

                            messages.success(request, '支付成功')
                    else:
                        messages.error(request, '钱包余额不足')
                else:
                    messages.error(request, '暂不支持其他支付方式')
            else:
                messages.error(request, '当前订单状态无法支付')

    return render(request, 'orders/order_detail.html', {
        'order': order
    })


def history_list(request):
    """用户历史记录"""
    # 检查用户是否登录
    user_id = request.session.get('info')
    if not user_id:
        messages.error(request, '请先登录')
        return redirect('login')

    user = User.objects.filter(id=user_id).first()
    histories = HistoryNew.objects.filter(user=user).select_related('order').order_by('-timestamp')

    # 分页
    paginator = Paginator(histories, 10)
    page = request.GET.get('page')
    histories = paginator.get_page(page)

    return render(request, 'orders/history_list.html', {
        'histories': histories
    })


def update_order_status(request, order_id):
    """管理员更新订单状态"""
    # 检查管理员是否登录
    operator_id = request.session.get('operator_info')
    if not operator_id:
        messages.error(request, '请先登录')
        return redirect('operator_login')

    # 验证是否是管理员
    operator = Operator.objects.filter(id=operator_id, is_operator=True).first()
    if not operator:
        messages.error(request, '权限不足')
        return redirect('operator_login')

    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')

        if new_status in ['shipped', 'delivered', 'completed']:
            with transaction.atomic():
                order.order_status = new_status
                if new_status == 'completed':
                    order.complete_time = timezone.now()
                order.save()

                # 记录历史
                HistoryNew.objects.create(
                    user=order.user,
                    order=order,
                    history_type=f'order_{new_status}',
                    details=f'订单状态更新为：{order.get_order_status_display()}'
                )

                messages.success(request, '订单状态更新成功')
        else:
            messages.error(request, '无效的订单状态')

    return redirect('admin_order_list')