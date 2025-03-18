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
    """Admin view all promo codes"""
    # Verify admin identity
    operator_info = request.session.get('admin_info')
    if not operator_info:
        return redirect('/operation/login/')
    
    operator = get_object_or_404(Operator, id=operator_info['employee_id'])


    promo_codes = PromoCode.objects.all().order_by('-created_time')
    
    # Pagination
    paginator = Paginator(promo_codes, 10)
    page = request.GET.get('page')
    promo_codes = paginator.get_page(page)
    
    return render(request, 'operation/promo_code_list.html', {
        'promo_codes': promo_codes,
        'operator': operator,
        'section': 'promo_codes'
    })


def promo_code_add(request):
    """Add new promo code"""
    # Verify admin identity
    operator_info = request.session.get('admin_info')
    if not operator_info:
        return redirect('/operation/login/')
    
    operator = get_object_or_404(Operator, id=operator_info['employee_id'])

    if request.method == 'POST':
        form = PromoCode_ModelForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Promo code created successfully')
            return redirect('promo_code_list')
        else:
            messages.error(request, 'Creation failed, please check your input')
    else:
        form = PromoCode_ModelForm()
    
    return render(request, 'operation/promo_code_edit.html', {
        'form': form,
        'title': 'Add Promo Code',
        'operator': operator,
    })


def promo_code_edit(request, code_id):
    """Edit promo code"""
    # Verify admin identity
    operator_info = request.session.get('admin_info')
    if not operator_info:
        return redirect('/operation/login/')
    
    operator = get_object_or_404(Operator, id=operator_info['employee_id'])

    promo_code = PromoCode.objects.filter(id=code_id).first()
    
    if request.method == 'POST':
        form = PromoCode_EditForm(data=request.POST, instance=promo_code)
        if form.is_valid():
            form.save()
            messages.success(request, 'Promo code updated successfully')
            return redirect('promo_code_list')
        else:
            messages.error(request, 'Update failed, please check your input')
    else:
        form = PromoCode_EditForm(instance=promo_code)
    
    return render(request, 'operation/promo_code_edit.html', {
        'form': form,
        'title': 'Edit Promo Code',
        'operator': operator,
        'promo_code': promo_code
    })


def promo_code_delete(request, code_id):
    """Delete promo code"""
    # Verify admin identity
    operator_info = request.session.get('admin_info')
    if not operator_info:
        return JsonResponse({'success': False, 'message': 'Please log in first'})
    
    operator_obj = Operator.objects.filter(id=operator_info['id']).first()
    if not operator_obj:
        return JsonResponse({'success': False, 'message': 'Invalid admin account'})

    try:
        promo_code = PromoCode.objects.filter(id=code_id).first()
        promo_code.delete()
        messages.success(request, 'Promo code deleted successfully')
    except Exception as e:
        messages.error(request, f'Deletion failed: {str(e)}')
    return redirect('promo_code_list')


def apply_promo_code(request):
    """Apply promo code to order"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})

    data = json.loads(request.body)
    order_id = data.get('order_id')
    promo_code = data.get('promo_code')

    try:
        order = Order.objects.get(id=order_id)
        promo_code_obj = PromoCode.objects.get(code=promo_code)

        # Check if promo code is valid
        if not promo_code_obj.is_valid():
            return JsonResponse({'success': False, 'message': 'Promo code expired or invalid'})

        # Check if order amount meets minimum requirement
        if order.subtotal_amount < promo_code_obj.min_order_value:
            return JsonResponse({
                'success': False,
                'message': f'Order amount must be at least £{promo_code_obj.min_order_value} to use this promo code'
            })

        # Check if user has already used this promo code
        if HistoryNew.objects.filter(
                user=order.user,
                promo_code=promo_code_obj,
                history_type='promo_code_used'
        ).exists():
            return JsonResponse({'success': False, 'message': 'You have already used this promo code'})

        with transaction.atomic():
            # Update order amount
            order.promo_code = promo_code_obj
            order.promo_discount = promo_code_obj.discount
            order.final_amount = order.total_amount - promo_code_obj.discount
            order.save()

            # Record history
            HistoryNew.objects.create(
                user=order.user,
                order=order,
                history_type='promo_code_used',
                promo_code=promo_code_obj,
                amount=promo_code_obj.discount,
                original_amount=order.total_amount,
                final_amount=order.final_amount,
                details=f'Used promo code: {promo_code_obj.code}'
            )

        return JsonResponse({
            'success': True,
            'message': 'Promo code applied successfully',
            'discount': float(promo_code_obj.discount),
            'final_amount': float(order.final_amount)
        })

    except PromoCode.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Promo code does not exist'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order does not exist'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})