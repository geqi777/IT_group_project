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

def admin_dashboard(request):
    """管理员首页"""
    # 检查管理员是否登录
    operator_id = request.session.get('admin_info')
    if not operator_id:
        messages.error(request, '请先登录')
        return redirect('/operation/login/')

    # 生成示例数据（如果没有数据）
    order_count = Order.objects.count()
    if order_count == 0:
        generate_sample_data(request)

    # 统计数据
    user_count = User.objects.count()
    product_count = Product.objects.count()
    order_count = Order.objects.count()
    admin_count = Operator.objects.filter(is_operator=True).count()

    # 待支付订单（状态为"pending"的订单）
    pending_orders = Order.objects.filter(order_status='pending').order_by('-timestamp')[:10]
    pending_count = Order.objects.filter(order_status='pending').count()
    
    # 待发货订单（状态为"paid"的订单）
    to_ship_orders = Order.objects.filter(order_status='paid').order_by('-timestamp')[:10]
    to_ship_count = Order.objects.filter(order_status='paid').count()
    
    # 待送达订单（状态为"shipped"的订单）
    to_deliver_orders = Order.objects.filter(order_status='shipped').order_by('-timestamp')[:10]
    to_deliver_count = Order.objects.filter(order_status='shipped').count()
    
    # 近期订单（最近10个订单）
    recent_orders = Order.objects.order_by('-timestamp')[:10]
    
    # 月度销售记录（最近6个月）
    sales_data = []
    month_names = []
    now = timezone.now()
    
    for i in range(5, -1, -1):
        month_start = now.replace(day=1) - datetime.timedelta(days=30*i)
        month_end = (month_start.replace(month=month_start.month % 12 + 1, day=1) if month_start.month < 12 
                     else month_start.replace(year=month_start.year + 1, month=1, day=1)) - datetime.timedelta(days=1)
        
        # 计算该月销售额和订单数
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
        month_names.append(month_start.strftime('%Y年%m月'))
    
    # 退货记录
    return_orders = Order.objects.filter(order_status='refunded').order_by('-timestamp')[:5]
    return_count = Order.objects.filter(order_status='refunded').count()
    
    # 商品评价统计
    top_rated_products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).filter(review_count__gt=0).order_by('-avg_rating')[:10]
    
    avg_rating = Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # 评分分布
    rating_distribution = []
    for i in range(1, 6):
        count = Review.objects.filter(rating=i).count()
        rating_distribution.append({
            'rating': i,
            'count': count
        })
        
    # 为了保持向后兼容，保留之前的变量名
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
        'top_rated_products': top_rated_products,
        'avg_rating': avg_rating,
        'rating_distribution': rating_distribution,
        # 旧变量名，为了兼容性保留
        'pending_and_paid_orders': pending_and_paid_orders
    }

    return render(request, 'operation/admin_dashboard.html', context)

def admin_review_list(request):
    """管理员查看和管理用户评价"""
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

    # 获取所有评价
    reviews = Review.objects.select_related('user', 'product').all().order_by('-created_time')

    # 过滤功能
    product_id = request.GET.get('product_id')
    rating = request.GET.get('rating')
    
    if product_id:
        reviews = reviews.filter(product_id=product_id)
    
    if rating:
        reviews = reviews.filter(rating=rating)

    # 分页
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews = paginator.get_page(page)

    # 获取所有产品用于过滤
    products = Product.objects.all()

    return render(request, 'operation/admin_review_list.html', {
        'reviews': reviews,
        'products': products,
        'operator': operator
    })

def admin_review_delete(request, review_id):
    """管理员删除评价"""
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

    # 获取评价
    review = get_object_or_404(Review, id=review_id)

    # 删除评价
    if request.method == 'POST':
        review.delete()
        messages.success(request, '评价已删除')
        return redirect('/operation/homepage/reviews/')

    return render(request, 'operation/admin_review_delete.html', {
        'review': review,
        'operator': operator
    })

def generate_sample_data(request):
    """生成示例数据"""
    try:
        # 检查是否已有数据
        if User.objects.count() > 5 and Product.objects.count() > 10:
            return
        
        # 创建用户（如果没有足够用户）
        if User.objects.count() < 5:
            for i in range(5):
                User.objects.create(
                    name=f'测试用户{i+1}',
                    email=f'user{i+1}@example.com',
                    address=f'测试地址{i+1}',
                    contact=f'1234567890{i}',
                    username=f'user{i+1}',
                    password='password'
                )

        
        # 创建订单
        users = list(User.objects.all())
        products = list(Product.objects.all())
        
        # 创建不同状态的订单
        for status in ['pending', 'paid', 'shipped', 'delivered', 'completed', 'refunded']:
            # 每种状态创建5个订单
            for i in range(5):
                # 随机选择用户
                user = random.choice(users)
                
                # 创建订单
                order_date = timezone.now() - timedelta(days=random.randint(0, 180))
                order = Order.objects.create(
                    user=user,
                    order_status=status,
                    shipping_address=user.address,
                    contact_name=user.name,
                    contact_email=user.email,
                    timestamp=order_date
                )
                
                # 添加订单商品
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
                
                # 更新订单金额
                shipping_fee = Decimal('0') if subtotal >= 30 else Decimal('5')
                vat = (subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
                total = subtotal + shipping_fee + vat
                
                order.subtotal_amount = subtotal
                order.shipping_fee = shipping_fee
                order.vat = vat
                order.total_amount = total
                order.final_amount = total
                
                # 设置完成时间（对于已完成订单）
                if status in ['delivered', 'completed', 'refunded']:
                    order.complete_time = order_date + timedelta(days=random.randint(1, 7))
                
                # 设置支付状态
                if status != 'pending':
                    order.payment_status = True
                    order.paid_time = order_date + timedelta(hours=random.randint(1, 24))
                
                order.save()
        
        messages.success(request, '示例数据已生成')
    except Exception as e:
        messages.error(request, f'生成示例数据时出错：{str(e)}')
