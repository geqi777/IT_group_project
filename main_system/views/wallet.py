from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
from django.db.utils import IntegrityError

from main_system import models
from main_system.models import User, Wallet, PaymentCard, WalletTransaction

def wallet_view(request):
    """钱包详情页面，显示余额、积分和支付卡列表"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    # 获取或创建钱包
    wallet, created = Wallet.objects.get_or_create(
        user=user,
        defaults={
            'balance': Decimal('0'),
            'points': 0
        }
    )

    # 获取支付卡列表
    payment_cards = PaymentCard.objects.filter(user=user)

    # 获取最近的交易记录
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-timestamp')[:5]

    return render(request, 'wallet/wallet_view.html', {
        'wallet': wallet,
        'payment_cards': payment_cards,
        'transactions': transactions
    })

def payment_card_list(request):
    """支付卡列表页面"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    # 获取支付卡列表
    payment_cards = PaymentCard.objects.filter(user=user)

    return render(request, 'wallet/payment_card.html', {
        'payment_cards': payment_cards
    })

def payment_card_add(request):
    """添加新支付卡"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    if request.method == 'POST':
        try:
            # 获取表单数据
            card_number = request.POST.get('card_number').replace(' ', '')  # 移除空格
            
            # 检查卡号是否已存在
            if PaymentCard.objects.filter(card_number=card_number).exists():
                messages.error(request, '该卡号已被使用')
                return redirect('/customer/wallet/cards/add/')
                
            # 创建新支付卡
            card = PaymentCard.objects.create(
                user=user,
                nickname=request.POST.get('nickname') or '未命名卡片',
                card_number=card_number,
                expiry_date=request.POST.get('expiry_date'),
                cvv=request.POST.get('cvv'),
                country=request.POST.get('country'),
                postcode=request.POST.get('postcode').upper()
            )
            messages.success(request, '支付卡添加成功')
            return redirect('/customer/wallet/cards/')
            
        except IntegrityError:
            messages.error(request, '该卡号已被使用')
            return redirect('/customer/wallet/cards/add/')
        except Exception as e:
            messages.error(request, f'添加失败：{str(e)}')
            return redirect('/customer/wallet/cards/add/')

    return render(request, 'wallet/card_add.html')

def payment_card_edit(request, card_id):
    """编辑支付卡"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    try:
        # 获取支付卡，使用get()而不是filter()
        card = PaymentCard.objects.get(id=card_id, user=user)

        if request.method == 'POST':
            try:
                # 更新支付卡信息
                card.nickname = request.POST.get('nickname')
                card.expiry_date = request.POST.get('expiry_date')
                card.country = request.POST.get('country')
                card.postcode = request.POST.get('postcode')
                card.save()

                messages.success(request, '支付卡更新成功')
                return redirect('/customer/wallet/cards/')
            except Exception as e:
                messages.error(request, f'更新失败：{str(e)}')

        return render(request, 'wallet/card_edit.html', {'card': card})
        
    except PaymentCard.DoesNotExist:
        messages.error(request, '支付卡不存在或已被删除')
        return redirect('/customer/wallet/cards/')

def payment_card_delete(request, card_id):
    """删除支付卡"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    # 获取并软删除支付卡
    try:
        card = PaymentCard.objects.get(id=card_id, user=user)
        card.delete()  # 直接删除记录
        messages.success(request, '支付卡已删除')
    except PaymentCard.DoesNotExist:
        messages.error(request, '支付卡不存在')
    
    return redirect('/customer/wallet/cards/')

def wallet_top_up(request):
    """钱包充值"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    # 获取钱包
    wallet = get_object_or_404(Wallet, user=user)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            payment_card_id = request.POST.get('payment_card_id')

            if amount <= 0:
                messages.error(request, '充值金额必须大于0')
                return redirect('/customer/wallet/top-up/')

            # 验证支付卡
            card = get_object_or_404(PaymentCard, id=payment_card_id, user=user)

            with transaction.atomic():
                # 更新钱包余额
                wallet.balance += amount
                wallet.save()

                # 记录交易
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='top up',
                    amount=amount,
                    payment_card=card,
                    details=f'通过卡片 {card.card_number[-4:]} 充值'
                )

                messages.success(request, f'成功充值 £{amount}')
                return redirect('/customer/wallet/')

        except Exception as e:
            messages.error(request, f'充值失败：{str(e)}')

    # 获取用户的支付卡列表
    payment_cards = PaymentCard.objects.filter(user=user)
    return render(request, 'wallet/top_up.html', {
        'wallet': wallet,
        'payment_cards': payment_cards
    })

def transaction_history(request):
    """交易记录"""
    # 检查用户是否登录
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, '请先登录')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, '用户不存在')
        return redirect('/customer/register/')

    # 获取钱包
    wallet = get_object_or_404(Wallet, user=user)

    # 获取所有交易记录
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-timestamp')

    # 分页
    paginator = Paginator(transactions, 10)
    page = request.GET.get('page')
    transactions = paginator.get_page(page)

    return render(request, 'wallet/transactions.html', {
        'wallet': wallet,
        'transactions': transactions
    })
