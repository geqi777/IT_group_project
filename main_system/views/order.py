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
from decimal import Decimal
import re


def create_order(request):
    """从购物车创建订单"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    cart = Cart.objects.filter(user=user).first()
    if not cart or not cart.items.exists():
        messages.error(request, '购物车为空，无法创建订单')
        return redirect('/customer/cart/')

    try:
        with transaction.atomic():
            # 生成订单号
            order_number = timezone.now().strftime('%Y%m%d%H%M%S') + str(user.id).zfill(4)

            # 创建订单
            order = Order.objects.create(
                user=user,
                order_number=order_number,
                shipping_address=user.address or '',
                order_status='pending',
                subtotal_amount=cart.get_subtotal_amount(),
                shipping_fee=cart.get_shipping_fee(),
                vat=cart.get_vat(),
                total_amount=cart.get_total_amount(),
                final_amount=cart.get_total_amount()  # 初始时final_amount等于total_amount
            )

            # 创建订单项
            order_items = []
            for cart_item in cart.items.all():
                order_items.append(
                    OrderItem(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price,
                        item_subtotal=cart_item.get_item_subtotal()
                    )
                )

            # 批量创建订单项
            OrderItem.objects.bulk_create(order_items)

            # 记录历史
            # HistoryNew.objects.create(
            #     user=user,
            #     order=order,
            #     history_type='order_created',
            #     amount=cart.get_total_amount(),
            #     details=f'创建订单：{order.order_number}'
            # )

            # 将订单ID存入session
            request.session['current_order_id'] = order.id

            # 清空购物车
            cart.items.all().delete()
            
            # 更新会话中的购物车计数为0
            request.session['cart_count'] = 0

            return redirect(f'/customer/order/{order.id}/shipping/')

    except Exception as e:
        messages.error(request, f'订单创建失败：{str(e)}')
        return redirect('/customer/cart/')


def order_list(request):
    """订单列表"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    orders = Order.objects.filter(user=user).order_by('-timestamp')
    
    # 为每个订单检查是否有退货项目和是否所有商品都已评价
    for order in orders:
        order.has_returned_items = False
        order.all_reviewed = True
        order.has_refunded_items = False
        
        for item in order.items.all():
            # 检查退货状态
            if item.return_status == 'refunded':
                order.has_refunded_items = True
            elif item.return_status != 'none' and item.return_status != 'rejected':
                order.has_returned_items = True
            
            # 检查评价状态
            if not hasattr(item, 'review') or not item.review:
                order.all_reviewed = False

    # 分页
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)

    return render(request, 'orders/order_list.html', {'orders': orders})


def order_detail(request, order_id):
    """订单详情"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        messages.error(request, '订单不存在')
        return redirect('/customer/order/list/')

    # 检查是否有任何商品正在退货中或已退货
    has_returned_items = False
    for item in order.items.all():
        if item.return_status != 'none' and item.return_status != 'rejected':
            has_returned_items = True
            break

    # 计算所有需要的值
    context = {
        'order': order,
        'points_value': float(order.points_used) * 0.01 if order.points_used else 0,
        'items_with_subtotal': [{
            'item': item,
            'subtotal': float(item.price) * item.quantity
        } for item in order.items.all()],
        'has_returned_items': has_returned_items
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
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    histories = HistoryNew.objects.filter(user=user).select_related('order').order_by('-timestamp')

    # 分页
    paginator = Paginator(histories, 10)
    page = request.GET.get('page')
    histories = paginator.get_page(page)

    return render(request, 'orders/history_list.html', {'histories': histories})


def shipping(request, order_id):
    """订单配送信息页面"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
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
                    if 'current_order_id' in request.session:
                        del request.session['current_order_id']

                    messages.success(request, '已返回购物车')
                    return redirect('/customer/cart/')
            except Exception as e:
                messages.error(request, f'操作失败：{str(e)}')
                return redirect(f'/customer/order/{order.id}/shipping/')

        # 处理地址选择
        address_choice = request.POST.get('address_choice')

        # 获取联系人信息
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')

        # 验证必填字段
        if not all([first_name, last_name, email]):
            messages.error(request, '请填写完整的联系人信息')
            return redirect(f'/customer/order/{order.id}/shipping/')

        # 处理地址信息
        if address_choice == 'existing' and user.address:
            # 使用已有地址
            shipping_address = user.address
        else:
            # 获取新地址信息
            shipping_address = request.POST.get('shipping_address')
            city = request.POST.get('city')
            postcode = request.POST.get('postcode')
            country = request.POST.get('country')

            # 验证必填字段
            if not all([shipping_address, city, postcode, country]):
                messages.error(request, '请填写完整的地址信息')
                return redirect(f'/customer/order/{order.id}/shipping/')

            # 组合完整地址
            shipping_address = f"{shipping_address}, {city}, {postcode}, {country}"

            # 如果用户选择保存地址（可选）
            if request.POST.get('save_info'):
                user.address = shipping_address
                user.save()

        # 更新订单信息
        order.shipping_address = shipping_address
        order.contact_name = f"{first_name} {last_name}".strip()
        order.contact_email = email
        order.save()

        # 处理订阅（可选）
        if request.POST.get('newsletter'):
            Subscription.objects.get_or_create(
                email=email,
                defaults={'name': f"{first_name} {last_name}".strip()}
            )

        return redirect(f'/customer/order/{order.id}/payment/')

    # 重新计算订单金额
    order.subtotal_amount = sum(item.item_subtotal for item in order.items.all())
    order.shipping_fee = Decimal('0') if order.subtotal_amount >= Decimal('30') else Decimal('5')
    order.vat = order.subtotal_amount * Decimal('0.05')
    order.total_amount = order.subtotal_amount + order.shipping_fee + order.vat
    order.final_amount = order.total_amount
    order.save()

    return render(request, 'orders/shipping.html', {
        'user': user,
        'order': order
    })


def payment(request, order_id):
    """处理订单支付"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    # 获取订单
    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        messages.error(request, '订单不存在')
        return redirect('/customer/cart/')

    # 获取或创建钱包
    wallet, _ = models.Wallet.objects.get_or_create(
        user=user,
        defaults={'balance': Decimal('0'), 'points': 0}
    )

    # 计算是否可以使用积分支付
    points_needed = order.final_amount * 100  # 假设1元=100积分
    can_use_points = wallet.points >= points_needed

    # 获取用户已保存的支付卡
    saved_cards = models.PaymentCard.objects.filter(user=user)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')

        try:
            if payment_method == 'wallet':
                if wallet.balance >= order.final_amount:
                    # 钱包支付逻辑
                    with transaction.atomic():
                        wallet.balance -= order.final_amount
                        wallet.save()

                        order.payment_method = 'wallet'
                        order.payment_status = True
                        order.paid_time = timezone.now()
                        order.order_status = 'paid'
                        order.save()
                    # 记录钱包交易
                        WalletTransaction.objects.create(
                            wallet=wallet,
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

                    messages.success(request, '支付成功！')
                    return redirect(f'/customer/order/{order.id}/detail/')
                else:
                    messages.error(request, '钱包余额不足')

            elif payment_method == 'points':
                if can_use_points:
                    # 积分支付逻辑
                    with transaction.atomic():
                        wallet.points -= points_needed
                        wallet.save()

                        order.payment_method = 'points'
                        order.points_used = points_needed
                        order.payment_status = True
                        order.paid_time = timezone.now()
                        order.order_status = 'paid'
                        order.save()
                    # 记录钱包交易
                        WalletTransaction.objects.create(
                            wallet=wallet,
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

                    messages.success(request, '积分支付成功！')
                    return redirect(f'/customer/order/{order.id}/detail/')
                else:
                    messages.error(request, '积分不足')

            elif payment_method == 'card':
                saved_card_id = request.POST.get('saved_card_id')

                if saved_card_id:
                    # 使用已保存的卡片支付
                    card = get_object_or_404(models.PaymentCard, id=saved_card_id, user=user)

                    # 处理已保存卡片支付逻辑
                    with transaction.atomic():
                        order.payment_method = 'card'
                        order.payment_card = card
                        order.payment_status = True
                        order.paid_time = timezone.now()
                        order.order_status = 'paid'
                        order.save()

                        # 记录订单历史
                        HistoryNew.objects.create(
                            user=user,
                            order=order,
                            history_type='order_paid',
                            amount=order.final_amount,
                            details=f'信用卡支付订单：{order.order_number}'
                        )
                        
                        # 记录钱包交易 - 添加卡支付记录
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            transaction_type='card_payment',
                            amount=order.final_amount,
                            payment_card=order.payment_card,
                            details=f'信用卡支付订单：{order.order_number}'
                        )
                else:
                    # 处理新卡片支付
                    nickname = request.POST.get('nickname')
                    card_number = request.POST.get('card_number')
                    expiry_date = request.POST.get('expiry_date')
                    cvv = request.POST.get('cvv')
                    country = request.POST.get('country')
                    postcode = request.POST.get('postcode')
                    save_card = request.POST.get('save_card') == 'on'

                    # 验证卡片信息
                    if not all([card_number, expiry_date, cvv, country, postcode]):
                        messages.error(request, '请填写完整的卡片信息')
                        return redirect(f'/customer/order/{order.id}/payment/')

                    # 验证卡号格式
                    if not re.match(r'^\d{16}$', card_number.replace(' ', '')):
                        messages.error(request, '无效的卡号')
                        return redirect(f'/customer/order/{order.id}/payment/')

                    # 验证有效期格式
                    if not re.match(r'^\d{2}/\d{2}$', expiry_date):
                        messages.error(request, '无效的有效期格式')
                        return redirect(f'/customer/order/{order.id}/payment/')

                    # 验证CVV格式
                    if not re.match(r'^\d{3}$', cvv):
                        messages.error(request, '无效的CVV码')
                        return redirect(f'/customer/order/{order.id}/payment/')

                    with transaction.atomic():
                        if save_card:
                            # 保存新卡片
                            card = models.PaymentCard.objects.create(
                                user=user,
                                nickname=nickname or '未命名卡片',
                                card_number=card_number.replace(' ', ''),
                                expiry_date=expiry_date,
                                country=country,
                                postcode=postcode.upper()
                            )
                            order.payment_card = card
                        else:
                            # 创建临时卡对象但不保存到数据库
                            card = models.PaymentCard(
                                user=user,
                                nickname='一次性卡片',
                                card_number=card_number.replace(' ', ''),
                                expiry_date=expiry_date,
                                country=country,
                                postcode=postcode.upper()
                            )
                            if save_card:
                                card.save()
                            order.payment_card = card if save_card else None

                        order.payment_method = 'card'
                        order.payment_status = True
                        order.paid_time = timezone.now()
                        order.order_status = 'paid'
                        order.save()

                        # 记录订单历史
                        HistoryNew.objects.create(
                            user=user,
                            order=order,
                            history_type='order_paid',
                            amount=order.final_amount,
                            details=f'信用卡支付订单：{order.order_number}'
                        )
                        
                        # 记录钱包交易 - 添加卡支付记录
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            transaction_type='card_payment',
                            amount=order.final_amount,
                            payment_card=card if save_card else None,
                            details=f'信用卡支付订单：{order.order_number}'
                        )

                messages.success(request, '支付成功！')
                return redirect(f'/customer/order/{order.id}/detail/')

        except Exception as e:
            messages.error(request, f'支付失败：{str(e)}')
            return redirect(f'/customer/order/{order.id}/payment/')

    context = {
        'order': order,
        'wallet': wallet,
        'can_use_points': can_use_points,
        'points_needed': points_needed,
        'saved_cards': saved_cards,
    }

    return render(request, 'orders/payment.html', context)


def order_cancel(request, order_id):
    """取消订单（支持未支付和已支付订单）"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    order = Order.objects.get (id=order_id, user=user)

    # 检查订单状态
    if order.order_status not in ['pending', 'paid', 'shipped']:
        messages.error(request, '当前订单状态无法取消')
        return redirect('/customer/order/{{ order.id }}/detail/')

    try:
        with transaction.atomic():
            if order.order_status == 'pending':
                # 未支付订单直接取消
                order.order_status = 'cancelled'
                order.save()

                messages.success(request, '订单已取消')
            else:
                # 已支付订单需要退款
                if order.payment_method == 'wallet':
                    # 钱包退款
                    user.wallet.balance += order.final_amount
                    user.wallet.save()

                    # 记录退款交易
                    WalletTransaction.objects.create(
                        wallet=user.wallet,
                        transaction_type='refund',
                        amount=order.final_amount,
                        details=f'订单 {order.order_number} 取消退款'
                    )
                elif order.payment_method == 'points':
                    # 积分退还
                    user.wallet.points += order.points_used
                    user.wallet.save()

                    # 记录积分退还
                    WalletTransaction.objects.create(
                        wallet=user.wallet,
                        transaction_type='points_refund',
                        points=order.points_used,
                        details=f'订单 {order.order_number} 取消退还积分'
                    )
                elif order.payment_method == 'card':
                    # 信用卡退款逻辑（需要集成支付网关的退款API）
                    pass

                # 恢复商品库存
                for item in order.items.all():
                    item.product.stock += item.quantity
                    item.product.save()

                # 如果是已完成订单，需要扣除之前获得的积分
                if order.points_earned > 0 and order.order_status == 'completed':
                    # 确保积分不会变成负数
                    points_to_deduct = min(user.wallet.points, order.points_earned)
                    if points_to_deduct > 0:
                        user.wallet.points -= points_to_deduct
                        user.wallet.save()
                        
                        # 记录扣除积分交易
                        WalletTransaction.objects.create(
                            wallet=user.wallet,
                            transaction_type='points_used',
                            points=points_to_deduct,
                            details=f'订单 {order.order_number} 取消扣除之前获得的积分'
                        )

                # 更新订单状态
                order.order_status = 'refunded'
                order.save()

                messages.success(request, '订单已取消，退款将在3-5个工作日内到账')

            # 记录订单历史
            HistoryNew.objects.create(
                user=user,
                order=order,
                history_type='order_cancelled',
                amount=order.final_amount if order.payment_status else None,
                points=order.points_used if order.payment_method == 'points' else None,
                details=f'用户取消订单：{order.order_number}'
            )

    except Exception as e:
        messages.error(request, f'取消订单失败：{str(e)}')

    return redirect('/customer/order/')

def order_confirm_receipt(request, order_id):
    """确认收货"""
     # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    order = Order.objects.get (id=order_id, user=user)

    if order.order_status != 'delivered':
        messages.error(request, '当前订单状态无法确认收货')
        return redirect('order_detail', order_id=order_id)

    order.order_status = 'completed'
    order.complete_time = timezone.now()
    order.save()

    messages.success(request, '已确认收货')
    return redirect('/customer/order/')

def order_review(request, order_id):
    """订单评价"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    order = get_object_or_404(Order, id=order_id, user=user)

    if order.order_status != 'completed':
        messages.error(request, '只能评价已完成的订单')
        return redirect('/customer/order/')

    # 获取已评价和未评价的订单项
    reviewed_items = []
    unreviewed_items = []

    for item in order.items.all():
        if hasattr(item, 'review'):
            reviewed_items.append(item)
        else:
            unreviewed_items.append(item)
    
    # 如果没有未评价的商品，提示用户并返回订单列表
    if not unreviewed_items:
        messages.info(request, '该订单中的所有商品已评价，无需再次评价')
        return redirect('/customer/order/')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                for item in unreviewed_items:
                    rating = request.POST.get(f'rating_{item.id}')
                    comment = request.POST.get(f'comment_{item.id}')

                    if rating and comment:
                        item.add_review(int(rating), comment)

                messages.success(request, '评价提交成功')
                return redirect('/customer/order/')
        except Exception as e:
            messages.error(request, f'评价提交失败：{str(e)}')

    context = {
        'order': order,
        'reviewed_items': reviewed_items,
        'unreviewed_items': unreviewed_items,
    }

    return render(request, 'orders/order_review.html', context)

def order_return(request, order_id):
    """申请退货"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    order = get_object_or_404(Order, id=order_id, user=user)

    if order.order_status != 'completed':
        messages.error(request, '只能对已完成的订单申请退货')
        return redirect('/customer/order/')

    if request.method == 'POST':
        try:
            return_items = request.POST.getlist('return_items')
            return_reason = request.POST.get('return_reason')
            return_details = request.POST.get('return_details')

            if not return_items:
                messages.error(request, '请选择要退货的商品')
                return redirect('order_return', order_id=order_id)

            with transaction.atomic():
                # 更新订单项的退货状态
                for item_id in return_items:
                    item = get_object_or_404(OrderItem, id=item_id, order=order)
                    item.apply_return(return_reason, return_details)

                messages.success(request, '退货申请已提交，请等待审核')
                return redirect('/customer/order/')

        except Exception as e:
            messages.error(request, f'退货申请失败：{str(e)}')

    return render(request, 'orders/order_return.html', {'order': order})

def order_delete(request, order_id):
    """删除订单记录"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        messages.error(request, '订单不存在')
        return redirect('/customer/order/')

    if order.order_status == 'pending':
        messages.error(request, '未支付订单无法删除，请先取消订单')
        return redirect('/customer/order/')

    order.delete()
    messages.success(request, '订单记录已删除')
    return redirect('/customer/order/')


# 管理员端口 1
def admin_order_list(request):
    """管理员查看所有订单"""
    # 检查管理员是否登录
    operator_info = request.session.get('admin_info')
    if not operator_info:
        messages.error(request, '请先登录')
        return redirect('/operation/login/')

    # 验证是否是管理员
    operator = Operator.objects.filter(id=operator_info['employee_id']).first()
    if not operator or not operator.is_operator:
        messages.error(request, '权限不足')
        return redirect('/operation/login/')

    # 获取过滤参数
    order_status = request.GET.get('order_status')
    return_status = request.GET.get('return_status')

    # 基本查询
    order_items_query = OrderItem.objects.select_related('order', 'order__user', 'product').all()
    
    # 应用订单状态过滤
    if order_status:
        order_items_query = order_items_query.filter(order__order_status=order_status)
    
    # 应用退货状态过滤
    if return_status:
        order_items_query = order_items_query.filter(return_status=return_status)
    
    # 排序
    order_items = order_items_query.order_by('-order__timestamp')
    
    # 计算退货记录数量
    total_returns = OrderItem.objects.filter(return_status__in=['pending', 'approved', 'shipped', 'received', 'refunded']).count()

    # 分页
    paginator = Paginator(order_items, 20)
    page = request.GET.get('page')
    order_items = paginator.get_page(page)

    return render(request, 'orders/admin_order_list.html', {
        'order_items': order_items,
        'operator': operator,
        'order_status': order_status,
        'return_status': return_status,
        'total_returns': total_returns,
    })


def update_order_status(request, order_id):
    """管理员更新订单状态"""
    # 检查管理员是否登录
    operator_id = request.session.get('admin_info')
    if not operator_id:
        messages.error(request, '请先登录')
        return redirect('/operation/login/')

    # 验证是否是管理员
    operator = Operator.objects.filter(id=operator_id['employee_id'], is_operator=True).first()
    if not operator:
        messages.error(request, '权限不足')
        return redirect('/operation/login/')

    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')

        # 允许的状态更新
        allowed_statuses = ['paid', 'shipped', 'delivered', 'completed', 'cancelled']
        
        if new_status in allowed_statuses:
            with transaction.atomic():
                # 保存原始状态用于记录
                old_status = order.order_status
                
                # 更新订单状态
                order.order_status = new_status
                
                # 如果是完成订单，设置完成时间并更新积分
                if new_status == 'completed':
                    order.complete_time = timezone.now()
                    # 计算并添加积分
                    points_earned = int(order.final_amount * 10)  # 消费1元获得10积分
                    order.points_earned = points_earned
                    
                    # 更新用户钱包积分 - 确保钱包存在
                    wallet, created = models.Wallet.objects.get_or_create(
                        user=order.user,
                        defaults={'balance': Decimal('0'), 'points': 0}
                    )
                    wallet.points += points_earned
                    wallet.save()
                
                # 如果是取消订单
                if new_status == 'cancelled':
                    # 如果订单已支付，需要处理退款
                    if old_status in ['paid', 'shipped', 'delivered']:
                        with transaction.atomic():
                            # 根据支付方式退款
                            if order.payment_method == 'wallet':
                                # 退款到钱包
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                wallet.balance += order.final_amount
                                wallet.save()

                                # 记录钱包退款交易
                                WalletTransaction.objects.create(
                                    wallet=wallet,
                                    transaction_type='refund',
                                    amount=order.final_amount,
                                    details=f'订单 {order.order_number} 取消退款'
                                )
                            elif order.payment_method == 'points':
                                # 退还积分
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                wallet.points += order.points_used
                                wallet.save()

                                # 记录积分退还交易
                                WalletTransaction.objects.create(
                                    wallet=wallet,
                                    transaction_type='points_refund',
                                    points=order.points_used,
                                    details=f'订单 {order.order_number} 取消退还积分'
                                )
                            elif order.payment_method == 'card':
                                # 信用卡退款处理
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                
                                # 记录信用卡退款交易
                                WalletTransaction.objects.create(
                                    wallet=wallet,
                                    transaction_type='refund',
                                    amount=order.final_amount,
                                    payment_card=order.payment_card,
                                    details=f'订单 {order.order_number} 取消退款到信用卡'
                                )
                            
                            # 优惠券处理：如果订单使用了优惠券并且这是订单中唯一的商品或全部退款
                            if order.promo_code:
                                # 删除优惠券使用记录，允许用户再次使用
                                HistoryNew.objects.filter(
                                    user=order.user,
                                    promo_code=order.promo_code,
                                    history_type='promo_code_used',
                                    order=order
                                ).delete()
                                
                                # 记录优惠券返还操作
                                HistoryNew.objects.create(
                                    user=order.user,
                                    order=order,
                                    history_type='promo_code_returned',
                                    promo_code=order.promo_code,
                                    details=f'订单 {order.order_number} 取消，返还优惠券 {order.promo_code.code}'
                                )
                            
                            # 恢复所有商品库存
                            for item in order.items.all():
                                item.product.stock += item.quantity
                                item.product.save()

                            # 扣除之前获得的积分（如果有）
                            if order.points_earned > 0 and old_status == 'completed':
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                # 确保积分不会变成负数
                                points_to_deduct = min(wallet.points, order.points_earned)
                                if points_to_deduct > 0:
                                    wallet.points -= points_to_deduct
                                    wallet.save()
                                    
                                    # 记录扣除积分交易
                                    WalletTransaction.objects.create(
                                        wallet=wallet,
                                        transaction_type='points_used',
                                        points=points_to_deduct,
                                        details=f'订单 {order.order_number} 取消扣除之前获得的积分'
                                    )

                            # 更新订单状态为退款
                            order.order_status = 'refunded'

                # 最后统一保存订单状态
                order.save()

                # 记录历史
                status_display = dict(Order.ORDER_STATUS_CHOICES).get(new_status, new_status)
                HistoryNew.objects.create(
                    user=order.user,
                    order=order,
                    history_type=f'order_{new_status}',
                    details=f'订单状态从【{dict(Order.ORDER_STATUS_CHOICES).get(old_status, old_status)}】更新为【{status_display}】'
                )

                messages.success(request, f'订单状态已更新为: {status_display}')
        else:
            messages.error(request, '无效的订单状态')

        # 重定向回订单详情页
        return redirect(f'/operation/homepage/orders/detail/{order_id}/')
    
    # 如果不是POST请求，重定向到订单列表
    return redirect('/operation/homepage/orders/')


def process_return(request, order_id, item_id):
    """管理员处理退货申请"""
    # 检查管理员是否登录
    operator_id = request.session.get('admin_info')
    if not operator_id:
        messages.error(request, '请先登录')
        return redirect('/operation/login/')

    # 验证是否是管理员
    operator = Operator.objects.filter(id=operator_id['employee_id'], is_operator=True).first()
    if not operator:
        messages.error(request, '权限不足')
        return redirect('/operation/login/')

    item = OrderItem.objects.filter(id=item_id, order_id=order_id).first()
    if not item:
        messages.error(request, '订单项不存在')
        return redirect(f'/operation/homepage/orders/detail/{order_id}/')

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['approved', 'rejected', 'received', 'refunded']:
            try:
                with transaction.atomic():
                    if status == 'refunded':
                        # 计算退款金额
                        refund_amount = item.item_subtotal

                        # 处理退款
                        if item.order.payment_method == 'wallet':
                            # 确保用户有钱包
                            wallet, created = models.Wallet.objects.get_or_create(
                                user=item.order.user,
                                defaults={'balance': Decimal('0'), 'points': 0}
                            )
                            wallet.balance += refund_amount
                            wallet.save()

                            # 记录退款交易
                            WalletTransaction.objects.create(
                                wallet=wallet,
                                transaction_type='refund',
                                amount=refund_amount,
                                details=f'订单 {item.order.order_number} 商品退货退款'
                            )
                        elif item.order.payment_method == 'points':
                            # 积分退款
                            points_to_refund = int(refund_amount * 100)  # 1元=100积分的转换
                            wallet, created = models.Wallet.objects.get_or_create(
                                user=item.order.user,
                                defaults={'balance': Decimal('0'), 'points': 0}
                            )
                            wallet.points += points_to_refund
                            wallet.save()

                            # 记录积分退款交易
                            WalletTransaction.objects.create(
                                wallet=wallet,
                                transaction_type='points_refund',
                                points=points_to_refund,
                                details=f'订单 {item.order.order_number} 商品退货退还积分'
                            )
                        elif item.order.payment_method == 'card':
                            # 信用卡退款 - 记录在钱包中
                            wallet, created = models.Wallet.objects.get_or_create(
                                user=item.order.user,
                                defaults={'balance': Decimal('0'), 'points': 0}
                            )
                            
                            # 记录信用卡退款交易
                            WalletTransaction.objects.create(
                                wallet=wallet,
                                transaction_type='refund',
                                amount=refund_amount,
                                payment_card=item.order.payment_card,
                                details=f'订单 {item.order.order_number} 商品退货退款到信用卡'
                            )

                        # 恢复商品库存
                        item.product.stock += item.quantity
                        item.product.save()

                        # 更新退货状态
                        item.process_return(status, refund_amount)
                        
                        # 记录订单历史
                        HistoryNew.objects.create(
                            user=item.order.user,
                            order=item.order,
                            history_type='order_refunded',
                            amount=refund_amount,
                            details=f'订单商品退款: {item.product.name} x {item.quantity}'
                        )

                        # 检查是否所有订单项目都已退款或未退货，如是则更新整个订单状态为已退款
                        all_items_refunded = True
                        for order_item in item.order.items.all():
                            if order_item.return_status not in ['refunded', 'none', 'rejected']:
                                all_items_refunded = False
                                break
                        
                        if all_items_refunded:
                            # 更新订单状态为已退款
                            item.order.order_status = 'refunded'
                            
                            # 如果订单之前有获得积分，需要扣除这些积分
                            if item.order.points_earned > 0:
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=item.order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                
                                # 确保积分不会变成负数
                                points_to_deduct = min(wallet.points, item.order.points_earned)
                                if points_to_deduct > 0:
                                    wallet.points -= points_to_deduct
                                    wallet.save()
                                    
                                    # 记录扣除积分交易
                                    WalletTransaction.objects.create(
                                        wallet=wallet,
                                        transaction_type='points_used',
                                        points=points_to_deduct,
                                        details=f'订单 {item.order.order_number} 退款扣除之前获得的积分'
                                    )
                            
                            item.order.save()

                        # 优惠券处理：如果订单使用了优惠券并且这是订单中唯一的商品或全部退款
                        if item.order.promo_code and (item.order.items.count() == 1 or all(i.return_status == 'refunded' for i in item.order.items.all())):
                            # 删除优惠券使用记录，允许用户再次使用
                            HistoryNew.objects.filter(
                                user=item.order.user,
                                promo_code=item.order.promo_code,
                                history_type='promo_code_used',
                                order=item.order
                            ).delete()
                            
                            # 记录优惠券返还操作
                            HistoryNew.objects.create(
                                user=item.order.user,
                                order=item.order,
                                history_type='promo_code_returned',
                                promo_code=item.order.promo_code,
                                details=f'订单 {item.order.order_number} 商品退货，返还优惠券 {item.order.promo_code.code}'
                            )
                        # 如果订单有多个商品，并且使用了优惠券，需要按比例返还优惠金额
                        elif item.order.promo_code and item.order.promo_discount > 0:
                            # 计算当前商品占订单总价的比例
                            total_subtotal = sum(i.item_subtotal for i in item.order.items.all())
                            item_percentage = item.item_subtotal / total_subtotal if total_subtotal > 0 else 0
                            
                            # 计算应该退还的优惠金额
                            refund_discount = item.order.promo_discount * item_percentage
                            
                            # 将退款金额加上对应的优惠比例
                            refund_amount += refund_discount

                    else:
                        item.process_return(status)
                        
                        # 记录订单历史
                        action_map = {
                            'approved': '批准退货申请',
                            'rejected': '拒绝退货申请',
                            'received': '确认收到退货'
                        }
                        HistoryNew.objects.create(
                            user=item.order.user,
                            order=item.order,
                            history_type='order_refunded' if status == 'refunded' else 'order_cancelled',
                            details=f'{action_map.get(status, status)}: {item.product.name} x {item.quantity}'
                        )

                    messages.success(request, f'退货状态已更新为: {dict(OrderItem.RETURN_STATUS_CHOICES).get(status, status)}')

            except Exception as e:
                messages.error(request, f'处理失败：{str(e)}')
        else:
            messages.error(request, '无效的状态')

    return redirect(f'/operation/homepage/orders/detail/{order_id}/')

def admin_order_detail(request, order_id):
    """管理员查看订单详情"""
    # 检查管理员是否登录
    operator_id = request.session.get('admin_info')
    if not operator_id:
        messages.error(request, '请先登录')
        return redirect('/operation/login/')

    # 验证是否是管理员
    operator = Operator.objects.filter(id=operator_id['employee_id'], is_operator=True).first()
    if not operator:
        messages.error(request, '权限不足')
        return redirect('/operation/login/')

    # 获取订单信息
    order = get_object_or_404(Order, id=order_id)
    
    return render(request, 'orders/admin_order_detail.html', {
        'order': order,
        'operator': operator
    })