from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from main_system import models
from main_system.models import User, Product, Order, Review, Operator, PromoCode, OrderItem
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
import datetime
from collections import defaultdict
import json
import random
from decimal import Decimal
from datetime import timedelta
from functools import wraps

# 添加一个装饰器函数处理管理员页面的消息
def admin_message(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 定义自定义的消息方法
        def error(message):
            request.session.setdefault('admin_messages', []).append(('error', message))
        
        def success(message):
            request.session.setdefault('admin_messages', []).append(('success', message))
        
        def info(message):
            request.session.setdefault('admin_messages', []).append(('info', message))
        
        def warning(message):
            request.session.setdefault('admin_messages', []).append(('warning', message))
        
        # 将自定义消息方法添加到request对象
        request.admin_messages = type('', (), {
            'error': error,
            'success': success,
            'info': info,
            'warning': warning,
        })
        
        # 执行原始视图函数
        response = view_func(request, *args, **kwargs)
        
        # 处理Django render返回的响应
        if hasattr(response, 'context_data'):
            # 如果是TemplateResponse
            admin_messages = request.session.pop('admin_messages', [])
            response.context_data['admin_messages'] = admin_messages
        elif response.__class__.__name__ == 'HttpResponse' and not response.streaming and not getattr(response, 'is_redirect', False):
            # 如果是普通HttpResponse
            from django.template.response import SimpleTemplateResponse
            admin_messages = request.session.pop('admin_messages', [])
            
            # 判断响应是否是render生成的模板响应
            if hasattr(response, 'content') and b'<!DOCTYPE html>' in response.content:
                import re
                content = response.content.decode('utf-8')
                # 在</nav>后面插入消息部分
                admin_messages_html = ""
                if admin_messages:
                    admin_messages_html = '<div class="container mt-3">'
                    for msg_type, msg in admin_messages:
                        admin_messages_html += f'<div class="alert alert-{msg_type} alert-dismissible fade show" role="alert">'
                        admin_messages_html += f'{msg}'
                        admin_messages_html += '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>'
                        admin_messages_html += '</div>'
                    admin_messages_html += '</div>'
                
                # 在</nav>后面插入消息
                new_content = re.sub(r'</nav>', r'</nav>' + admin_messages_html, content)
                response.content = new_content.encode('utf-8')
        
        return response
    
    return _wrapped_view

# 添加一个用户消息装饰器，类似于admin_message
def user_message(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 定义自定义的消息方法
        def error(message):
            request.session.setdefault('user_messages', []).append(('error', message))
        
        def success(message):
            request.session.setdefault('user_messages', []).append(('success', message))
        
        def info(message):
            request.session.setdefault('user_messages', []).append(('info', message))
        
        def warning(message):
            request.session.setdefault('user_messages', []).append(('warning', message))
        
        # 将自定义消息方法添加到request对象
        request.user_messages = type('', (), {
            'error': error,
            'success': success,
            'info': info,
            'warning': warning,
        })
        
        # 执行原始视图函数
        response = view_func(request, *args, **kwargs)
        
        # 处理Django render返回的响应
        if hasattr(response, 'context_data'):
            # 如果是TemplateResponse
            user_messages = request.session.pop('user_messages', [])
            response.context_data['user_messages'] = user_messages
        elif response.__class__.__name__ == 'HttpResponse' and not response.streaming and not getattr(response, 'is_redirect', False):
            # 如果是普通HttpResponse
            from django.template.response import SimpleTemplateResponse
            user_messages = request.session.pop('user_messages', [])
            
            # 判断响应是否是render生成的模板响应
            if hasattr(response, 'content') and b'<!DOCTYPE html>' in response.content:
                import re
                content = response.content.decode('utf-8')
                # 在</nav>后面插入消息部分
                user_messages_html = ""
                if user_messages:
                    user_messages_html = '<div class="container mt-3">'
                    for msg_type, msg in user_messages:
                        user_messages_html += f'<div class="alert alert-{msg_type} alert-dismissible fade show" role="alert">'
                        user_messages_html += f'{msg}'
                        user_messages_html += '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>'
                        user_messages_html += '</div>'
                    user_messages_html += '</div>'
                
                # 在</nav>后面插入消息
                new_content = re.sub(r'</nav>', r'</nav>' + user_messages_html, content)
                response.content = new_content.encode('utf-8')
        
        return response
    
    return _wrapped_view

@admin_message
def admin_dashboard(request):
    """Admin Dashboard"""
    # Check if the admin is logged in
    operator_id = request.session.get('admin_info')
    if not operator_id:
        messages.error(request, 'Please log in first')
        return redirect('/operation/login/')

    # Generate sample data (if no data exists)
    order_count = Order.objects.count()
    if order_count == 0:
        generate_sample_data(request)

    # Statistics
    user_count = User.objects.count()
    product_count = Product.objects.count()
    order_count = Order.objects.count()
    admin_count = Operator.objects.filter(is_operator=True).count()

    # Pending orders (orders with status "pending")
    pending_orders = Order.objects.filter(order_status='pending').order_by('-timestamp')[:10]
    pending_count = Order.objects.filter(order_status='pending').count()
    
    # Orders to be shipped (orders with status "paid")
    to_ship_orders = Order.objects.filter(order_status='paid').order_by('-timestamp')[:10]
    to_ship_count = Order.objects.filter(order_status='paid').count()
    
    # Orders to be delivered (orders with status "shipped")
    to_deliver_orders = Order.objects.filter(order_status='shipped').order_by('-timestamp')[:10]
    to_deliver_count = Order.objects.filter(order_status='shipped').count()
    
    # Recent orders (last 10 orders)
    recent_orders = Order.objects.order_by('-timestamp')[:10]
    
    # Monthly sales records (last 6 months)
    sales_data = []
    month_names = []
    now = timezone.now()
    
    for i in range(5, -1, -1):
        month_start = now.replace(day=1) - datetime.timedelta(days=30*i)
        month_end = (month_start.replace(month=month_start.month % 12 + 1, day=1) if month_start.month < 12 
                     else month_start.replace(year=month_start.year + 1, month=1, day=1)) - datetime.timedelta(days=1)
        
        # Calculate sales and order count for the month
        month_orders = Order.objects.filter(
            Q(order_status='delivered') | Q(order_status='completed'),
            timestamp__gte=month_start, 
            timestamp__lte=month_end
        )
        month_sales = month_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        month_order_count = month_orders.count()
        
        sales_data.append({
            'month': month_start.strftime('%Y-%m'),
            'sales': month_sales,
            'orders': month_order_count
        })
        month_names.append(month_start.strftime('%Y-%m'))
    
    # Return records
    return_orders = Order.objects.filter(order_status='refunded').order_by('-timestamp')[:5]
    return_count = Order.objects.filter(order_status='refunded').count()
    
    # Count of return requests pending review - only count those with status "pending"
    pending_returns_count = OrderItem.objects.filter(return_status='pending').count()
    
    # Total count of return records in all statuses (excluding "none" and "rejected")
    return_items_count = OrderItem.objects.filter(
        return_status__in=['pending', 'approved', 'shipped', 'received', 'refunded']
    ).count()
    
    # Product review statistics
    top_rated_products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).filter(review_count__gt=0).order_by('-avg_rating')[:10]
    
    avg_rating = Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Rating distribution
    rating_distribution = []
    for i in range(1, 6):
        count = Review.objects.filter(rating=i).count()
        rating_distribution.append({
            'rating': i,
            'count': count
        })
        
    # To maintain backward compatibility, keep the previous variable name
    pending_and_paid_orders = list(pending_orders) + list(to_ship_orders)
    
    context = {
        'user_count': user_count,
        'product_count': product_count,
        'order_count': order_count,
        'admin_count': admin_count,
        'pending_orders': pending_orders,
        'pending_count': pending_count,
        'to_ship_orders': to_ship_orders,
        'to_ship_count': to_ship_count,
        'to_deliver_orders': to_deliver_orders,
        'to_deliver_count': to_deliver_count,
        'recent_orders': recent_orders,
        'monthly_sales': sales_data,
        'month_names': month_names,
        'return_orders': return_orders,
        'return_count': return_count,
        'return_items_count': return_items_count,
        'pending_returns_count': pending_returns_count,
        'top_rated_products': top_rated_products,
        'avg_rating': avg_rating,
        'rating_distribution': rating_distribution,
        # Old variable name, kept for compatibility
        'pending_and_paid_orders': pending_and_paid_orders
    }

    return render(request, 'operation/admin_dashboard.html', context)

@admin_message
def admin_review_list(request):
    """Admin view and manage user reviews"""
    # Check if the admin is logged in
    operator_id = request.session.get('admin_info')
    if not operator_id:
        messages.error(request, 'Please log in first')
        return redirect('/operation/login/')

    # Verify if the user is an admin
    operator = Operator.objects.filter(id=operator_id['employee_id'], is_operator=True).first()
    if not operator:
        messages.error(request, 'Insufficient permissions')
        return redirect('/operation/login/')

    # Get all reviews
    reviews = Review.objects.select_related('user', 'product').all().order_by('-created_time')

    # Filter functionality
    product_id = request.GET.get('product_id')
    rating = request.GET.get('rating')
    
    if product_id:
        reviews = reviews.filter(product_id=product_id)
    
    if rating:
        reviews = reviews.filter(rating=rating)

    # Pagination
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews = paginator.get_page(page)

    # Get all products for filtering
    products = Product.objects.all()

    return render(request, 'operation/admin_review_list.html', {
        'reviews': reviews,
        'products': products,
        'operator': operator
    })

@admin_message
def admin_review_delete(request, review_id):
    """Admin delete review"""
    # Check if the admin is logged in
    operator_id = request.session.get('admin_info')
    if not operator_id:
        messages.error(request, 'Please log in first')
        return redirect('/operation/login/')

    # Verify if the user is an admin
    operator = Operator.objects.filter(id=operator_id['employee_id'], is_operator=True).first()
    if not operator:
        messages.error(request, 'Insufficient permissions')
        return redirect('/operation/login/')

    # Get the review
    review = get_object_or_404(Review, id=review_id)

    # Delete the review
    if request.method == 'POST':
        review.delete()
        request.admin_messages.success('Review deleted')
        return redirect('/operation/homepage/reviews/')

    return render(request, 'operation/admin_review_delete.html', {
        'review': review,
        'operator': operator
    })

def generate_sample_data(request):
    """Generate sample data"""
    try:
        # Check if data already exists
        if User.objects.count() > 5 and Product.objects.count() > 10:
            return
        
        # Create users (if not enough users)
        if User.objects.count() < 5:
            for i in range(5):
                User.objects.create(
                    name=f'Test User {i+1}',
                    email=f'user{i+1}@example.com',
                    address=f'Test Address {i+1}',
                    phone=f'1234567890{i}',
                    account=f'user{i+1}',
                    password='password'
                )

        
        # Create orders
        users = list(User.objects.all())
        products = list(Product.objects.all())
        
        # Create orders with different statuses
        for status in ['pending', 'paid', 'shipped', 'delivered', 'completed', 'refunded']:
            # Create 5 orders for each status
            for i in range(5):
                # Randomly select a user
                user = random.choice(users)
                
                # Create order
                order_date = timezone.now() - timedelta(days=random.randint(0, 180))
                order = Order.objects.create(
                    user=user,
                    order_status=status,
                    shipping_address=user.address,
                    contact_name=user.name,
                    contact_email=user.email,
                    timestamp=order_date
                )
                
                # Add order items
                subtotal = 0
                for _ in range(random.randint(1, 3)):
                    product = random.choice(products)
                    quantity = random.randint(1, 3)
                    price = product.price
                    item_total = price * quantity
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=price,
                        item_subtotal=item_total
                    )
                    
                    subtotal += item_total
                
                # Update order amount
                shipping_fee = Decimal('0') if subtotal >= 30 else Decimal('5')
                vat = (subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
                total = subtotal + shipping_fee + vat
                
                order.subtotal_amount = subtotal
                order.shipping_fee = shipping_fee
                order.vat = vat
                order.total_amount = total
                order.final_amount = total
                
                # Set completion time (for completed orders)
                if status in ['delivered', 'completed', 'refunded']:
                    order.complete_time = order_date + timedelta(days=random.randint(1, 7))
                
                # Set payment status
                if status != 'pending':
                    order.payment_status = True
                    order.paid_time = order_date + timedelta(hours=random.randint(1, 24))
                
                order.save()
        
        if hasattr(request, 'admin_messages'):
            request.admin_messages.success('Sample data generated')
        else:
            # For compatibility, keep the original message system
            messages.success(request, 'Sample data generated')
    except Exception as e:
        error_message = f'Error generating sample data: {str(e)}'
        if hasattr(request, 'admin_messages'):
            request.admin_messages.error(error_message)
        else:
            # For compatibility, keep the original message system
            messages.error(request, error_message)
