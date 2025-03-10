from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.core.paginator import Paginator
from decimal import Decimal
import json

from main_system.models import PromoCode, Order, User, HistoryNew, Operator
from main_system.utils.boostrapModelForm import PromoCode_ModelForm, PromoCode_EditForm


def promo_code_list(request):
    """管理员查看所有优惠码"""
    # 验证管理员身份
    operator_info = request.session.get('operator_info')
    if not operator_info:
        return redirect('/operation/login/')
    
    operator_obj = Operator.objects.filter(id=operator_info['id']).first()
    if not operator_obj:
        return redirect('/operation/login/')

    promo_codes = PromoCode.objects.all().order_by('-created_time')
    
    # 分页
    paginator = Paginator(promo_codes, 10)
    page = request.GET.get('page')
    promo_codes = paginator.get_page(page)
    
    return render(request, 'admin/promo_codes/promo_code_list.html', {
        'promo_codes': promo_codes,
        'operator': operator_obj
    })


def promo_code_add(request):
    """添加新优惠码"""
    # 验证管理员身份
    operator_info = request.session.get('operator_info')
    if not operator_info:
        return redirect('/operation/login/')
    
    operator_obj = Operator.objects.filter(id=operator_info['id']).first()
    if not operator_obj:
        return redirect('/operation/login/')

    if request.method == 'POST':
        form = PromoCode_ModelForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '优惠码创建成功')
            return redirect('/admin/promo-codes/')
        else:
            messages.error(request, '创建失败，请检查输入')
    else:
        form = PromoCode_ModelForm()
    
    return render(request, 'admin/promo_codes/promo_code_edit.html', {
        'form': form,
        'title': '添加优惠码',
        'operator': operator_obj
    })


def promo_code_edit(request, code_id):
    """编辑优惠码"""
    # 验证管理员身份
    operator_info = request.session.get('operator_info')
    if not operator_info:
        return redirect('/operation/login/')
    
    operator_obj = Operator.objects.filter(id=operator_info['id']).first()
    if not operator_obj:
        return redirect('/operation/login/')

    promo_code = PromoCode.objects.filter(id=code_id).first()
    
    if request.method == 'POST':
        form = PromoCode_EditForm(data=request.POST, instance=promo_code)
        if form.is_valid():
            form.save()
            messages.success(request, '优惠码更新成功')
            return redirect('/admin/promo-codes/')
        else:
            messages.error(request, '更新失败，请检查输入')
    else:
        form = PromoCode_EditForm(instance=promo_code)
    
    return render(request, 'admin/promo_codes/promo_code_edit.html', {
        'form': form,
        'title': '编辑优惠码',
        'operator': operator_obj,
        'promo_code': promo_code
    })


def promo_code_delete(request, code_id):
    """删除优惠码"""
    # 验证管理员身份
    operator_info = request.session.get('operator_info')
    if not operator_info:
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    operator_obj = Operator.objects.filter(id=operator_info['id']).first()
    if not operator_obj:
        return JsonResponse({'success': False, 'message': '无效的管理员账户'})

    try:
        promo_code = PromoCode.objects.filter(id=code_id).first()
        promo_code.delete()
        messages.success(request, '优惠码删除成功')
    except Exception as e:
        messages.error(request, f'删除失败：{str(e)}')
    return redirect('promo_code_list')


def apply_promo_code(request):
    """应用优惠码到订单"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '无效的请求方法'})

    data = json.loads(request.body)
    order_id = data.get('order_id')
    promo_code = data.get('promo_code')

    try:
        order = Order.objects.get(id=order_id)
        promo_code_obj = PromoCode.objects.get(code=promo_code)

        # 检查优惠码是否有效
        if not promo_code_obj.is_valid():
            return JsonResponse({'success': False, 'message': '优惠码已过期或无效'})

        # 检查订单金额是否满足最低要求
        if order.subtotal_amount < promo_code_obj.min_order_value:
            return JsonResponse({
                'success': False,
                'message': f'订单金额需满£{promo_code_obj.min_order_value}才能使用此优惠码'
            })

        # 检查用户是否已使用过此优惠码
        if HistoryNew.objects.filter(
                user=order.user,
                promo_code=promo_code_obj,
                history_type='promo_code_used'
        ).exists():
            return JsonResponse({'success': False, 'message': '您已使用过此优惠码'})

        with transaction.atomic():
            # 更新订单金额
            order.promo_code = promo_code_obj
            order.promo_discount = promo_code_obj.discount
            order.final_amount = order.total_amount - promo_code_obj.discount
            order.save()

            # 记录历史
            HistoryNew.objects.create(
                user=order.user,
                order=order,
                history_type='promo_code_used',
                promo_code=promo_code_obj,
                amount=promo_code_obj.discount,
                original_amount=order.total_amount,
                final_amount=order.final_amount,
                details=f'使用优惠码：{promo_code_obj.code}'
            )

        return JsonResponse({
            'success': True,
            'message': '优惠码应用成功',
            'discount': float(promo_code_obj.discount),
            'final_amount': float(order.final_amount)
        })

    except PromoCode.DoesNotExist:
        return JsonResponse({'success': False, 'message': '优惠码不存在'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': '订单不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})