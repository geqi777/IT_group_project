from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required

from main_system.views.home_page import subscribe
from django.http import HttpRequest

from main_system import models
from main_system.models import Order, OrderItem, Cart, CartItem, User, WalletTransaction, HistoryNew, Operator, Subscription, PaymentCard, PromoCode


def create_order(request):
    """从购物车创建订单"""
    # 检查用户是否登录
    user_info = request.session.get('info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('login')

    user = User.objects.filter(id=user_info['user_id']).first()
    cart = Cart.objects.filter(user=user).first()
    if not cart or not cart.items.exists():
        messages.error(request, '购物车为空，无法创建订单')
        return redirect('/customer/cart/')

    try:
        with transaction.atomic():
            # 创建订单
            total_amount = cart.get_total_amount()
            order = Order.objects.create(
                user=user,
                total_amount=total_amount,
                shipping_fee=cart.get_shipping_fee(),
                vat=cart.get_vat(),
                final_amount=total_amount,  # 暂时使用total_amount作为final_amount
                shipping_address=user.address or '',
                order_status='pending'
            )

            # 创建订单项
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                    item_subtotal=cart_item.get_item_subtotal()
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

            # 将订单ID存入session
            request.session['current_order_id'] = order.id

            return redirect(f'/customer/order/{order.id}/shipping/')

    except Exception as e:
        messages.error(request, f'订单创建失败：{str(e)}')
        return redirect('/customer/cart/')


def order_list(request):
    """订单列表"""
    # 检查用户是否登录
    user_info = request.session.get('info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['user_id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    orders = Order.objects.filter(user=user).order_by('-timestamp')

    # 分页
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)

    return render(request, 'orders/order_list.html', {'orders': orders})


def admin_order_list(request):
    """管理员查看所有订单"""
    # 检查管理员是否登录
    operator_id = request.session.get(Operator,'operator_info')
    if not operator_id:
        messages.error(request, '请先登录')
        return redirect('/operator/login/')

    # 验证是否是管理员
    operator = Operator.objects.filter(id=operator_id, is_operator=True).first()
    if not operator:
        messages.error(request, '权限不足')
        return redirect('/operator/login/')

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
    user_info = request.session.get('info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['user_id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    order = models.Order.objects.filter(id=order_id, user=user).first()
    if not order:
        messages.error(request, '订单不存在')
        return redirect('/customer/order/list/')

    # 计算所有需要的值
    context = {
        'order': order,
        'points_value': float(order.points_used) * 0.01 if order.points_used else 0,
        'items_with_subtotal': [{
            'item': item,
            'subtotal': float(item.price) * item.quantity
        } for item in order.items.all()]
    }

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
                    amount=order.total_amount,
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
                    if user.wallet.balance >= order.total_amount:
                        with transaction.atomic():
                            # 扣除钱包余额
                            user.wallet.balance -= order.total_amount
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
                                amount=order.total_amount,
                                details=f'钱包支付订单：{order.order_number}'
                            )

                            # 记录钱包交易
                            WalletTransaction.objects.create(
                                wallet=user.wallet,
                                transaction_type='purchase',
                                amount=order.total_amount,
                                details=f'订单支付：{order.order_number}'
                            )

                            messages.success(request, '支付成功')
                    else:
                        messages.error(request, '钱包余额不足')
                else:
                    messages.error(request, '暂不支持其他支付方式')
            else:
                messages.error(request, '当前订单状态无法支付')

    return render(request, 'orders/order_detail.html', context)


def history_list(request):
    """用户历史记录"""
    # 检查用户是否登录
    user_info = request.session.get('info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['user_id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    histories = HistoryNew.objects.filter(user=user).select_related('order').order_by('-timestamp')

    # 分页
    paginator = Paginator(histories, 10)
    page = request.GET.get('page')
    histories = paginator.get_page(page)

    return render(request, 'orders/history_list.html', {'histories': histories})


def update_order_status(request, order_id):
    """管理员更新订单状态"""
    # 检查管理员是否登录
    operator_id = request.session.get('operator_info')
    if not operator_id:
        messages.error(request, '请先登录')
        return redirect('/operator/login/')

    # 验证是否是管理员
    operator = Operator.objects.filter(id=operator_id, is_operator=True).first()
    if not operator:
        messages.error(request, '权限不足')
        return redirect('/operator/login/')

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

    return redirect('/operator/order/')


def shipping(request, order_id):
    """订单配送信息页面"""
    # 检查用户是否登录
    user_info = request.session.get('info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['user_id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    # 获取订单
    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        messages.error(request, '订单不存在')
        return redirect('/customer/cart/')

    if request.method == 'POST':
        # 检查是否是取消订单的请求
        if request.POST.get('action') == 'cancel':
            try:
                with transaction.atomic():
                    # 恢复购物车项
                    cart = Cart.objects.get_or_create(user=user)[0]
                    for order_item in order.items.all():
                        CartItem.objects.create(
                            cart=cart,
                            product=order_item.product,
                            quantity=order_item.quantity,
                            add_time=timezone.now()
                        )
                    
                    # 删除订单和订单项
                    order.delete()
                    # 清除session中的订单ID
                    request.session.pop('current_order_id', None)
                    
                    messages.success(request, '已返回购物车')
                    return redirect('/customer/cart/')
            except Exception as e:
                messages.error(request, f'操作失败：{str(e)}')
                return redirect(f'/customer/order/{order.id}/shipping/')

        # 处理地址选择
        address_choice = request.POST.get('address_choice')
        if address_choice == 'existing' and user.address:
            shipping_address = user.address
        else:
            shipping_address = request.POST.get('shipping_address')
            city = request.POST.get('city')
            postcode = request.POST.get('postcode')
            country = request.POST.get('country')
            
            # 组合完整地址
            shipping_address = f"{shipping_address}, {city}, {postcode}, {country}"

            # 如果用户选择保存地址
            if request.POST.get('save_info'):
                user.address = shipping_address
                user.save()

        # 更新订单配送地址
        order.shipping_address = shipping_address
        order.save()

        # 如果用户订阅了新闻
        if request.POST.get('newsletter'):
            Subscription.objects.get_or_create(
                email=user.email,
                defaults={'name': user.name}
            )

        return redirect(f'/customer/order/{order.id}/payment/')

    return render(request, 'orders/shipping.html', {
        'user': user,
        'order': order
    })


def payment(request, order_id):
    """处理订单支付"""
    # 检查用户是否登录
    user_info = request.session.get('info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['user_id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    # 获取订单
    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        messages.error(request, '订单不存在')
        return redirect('/customer/cart/')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                payment_method = request.POST.get('payment_method')
                
                if payment_method == 'wallet':
                    # 钱包支付
                    if user.wallet.balance >= order.final_amount:
                        # 扣除钱包余额
                        user.wallet.balance -= order.final_amount
                        user.wallet.save()

                        # 更新订单状态
                        order.payment_method = 'wallet'
                        order.order_status = 'paid'
                        order.paid_time = timezone.now()
                        order.save()

                        # 记录钱包交易
                        WalletTransaction.objects.create(
                            wallet=user.wallet,
                            transaction_type='purchase',
                            amount=order.final_amount,
                            details=f'订单支付：{order.order_number}'
                        )

                        # 记录订单历史
                        HistoryNew.objects.create(
                            user=user,
                            order=order,
                            history_type='order_paid',
                            amount=order.final_amount,
                            details=f'钱包支付订单：{order.order_number}'
                        )

                        messages.success(request, '支付成功')
                    else:
                        messages.error(request, '钱包余额不足')
                        return redirect(f'/customer/order/{order.id}/payment/')

                elif payment_method == 'points':
                    # 积分支付
                    points_needed = int(order.final_amount * 100)  # 1积分=0.01英镑
                    if user.wallet.points >= points_needed:
                        # 扣除积分
                        user.wallet.points -= points_needed
                        user.wallet.save()

                        # 更新订单状态
                        order.payment_method = 'points'
                        order.order_status = 'paid'
                        order.paid_time = timezone.now()
                        order.points_used = points_needed
                        order.save()

                        # 记录钱包交易
                        WalletTransaction.objects.create(
                            wallet=user.wallet,
                            transaction_type='points_decrease',
                            points=points_needed,
                            details=f'积分支付订单：{order.order_number}'
                        )

                        # 记录订单历史
                        HistoryNew.objects.create(
                            user=user,
                            order=order,
                            history_type='order_paid',
                            points=points_needed,
                            details=f'积分支付订单：{order.order_number}'
                        )

                        messages.success(request, '支付成功')
                    else:
                        messages.error(request, '积分不足')
                        return redirect(f'/customer/order/{order.id}/payment/')

                elif payment_method == 'card':
                    # 信用卡支付
                    # 处理支付卡信息
                    if request.POST.get('save_card'):
                        payment_card = PaymentCard.objects.create(
                            user=user,
                            card_number=request.POST.get('card_number'),
                            expiry_date=request.POST.get('expiry_date'),
                            cvv=request.POST.get('cvv')
                        )
                        order.payment_card = payment_card

                    # 更新订单状态
                    order.payment_method = 'card'
                    order.order_status = 'paid'
                    order.paid_time = timezone.now()
                    order.save()

                    # 记录订单历史
                    HistoryNew.objects.create(
                        user=user,
                        order=order,
                        history_type='order_paid',
                        amount=order.final_amount,
                        details=f'信用卡支付订单：{order.order_number}'
                    )

                    messages.success(request, '支付成功')

                # 清除session中的订单ID
                request.session.pop('current_order_id', None)
                
                return redirect(f'/customer/order/{order.id}/detail/')

        except Exception as e:
            messages.error(request, f'支付失败：{str(e)}')
            return redirect(f'/customer/order/{order.id}/payment/')

    # 计算所需积分
    points_needed = int(order.final_amount * 100)  # 1积分=0.01英镑
    can_use_points = user.wallet.points >= points_needed

    return render(request, 'orders/payment.html', {
        'user': user,
        'order': order,
        'points_needed': points_needed,
        'can_use_points': can_use_points
    })