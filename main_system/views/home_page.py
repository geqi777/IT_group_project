from django.shortcuts import render, redirect
from main_system.models import Product, Subscription, Review, User
from django.http import JsonResponse
from django.contrib import  messages
from django.db.models import Q
import random

def homepage(request):
    """主页视图"""
    # 获取用户信息
    user_info = request.session.get('user_info')
    
    # 准备分类选项
    categories = [{'key': key, 'name': name} for key, name in Product.CATEGORY_CHOICES]
    
    # 获取最新商品
    new_releases = Product.objects.filter(status='active').order_by('-created_time')[:6]
    
    # 获取评论数据
    reviews = Review.objects.select_related('user', 'product').order_by('-created_time')[:10]
    
    # 如果没有足够的评论，创建一些示例评论数据
    if len(reviews) < 5:
        sample_reviews = []
        sample_comments = [
            "非常满意这个产品，质量很好，包装也很精美!",
            "设计独特，很有创意，收到后比我想象的还要好看!",
            "做工精细，细节处理得很到位，期待你们的新产品!",
            "朋友看到后也很喜欢，已经推荐给了她，下次还会再来购买!",
            "物流速度很快，客服态度也很好，整体购物体验很棒!",
            "收到货后马上试用了，效果超出预期，非常适合送礼!",
            "价格合理，性价比很高，是市场上同类产品中最好的选择!",
            "产品很实用，解决了我的很多问题，谢谢你们的用心制作!"
        ]
        
        sample_users = [
            {"name": "李明", "email": "liming@example.com"},
            {"name": "张华", "email": "zhanghua@example.com"},
            {"name": "王芳", "email": "wangfang@example.com"},
            {"name": "赵丽", "email": "zhaoli@example.com"},
            {"name": "刘伟", "email": "liuwei@example.com"}
        ]
        
        for i in range(5):
            rating = random.randint(4, 5)  # 随机4-5星评价
            comment = random.choice(sample_comments)
            user = sample_users[i % len(sample_users)]
            
            sample_reviews.append({
                'rating': rating,
                'comment': comment,
                'user': user,
                'created_time': '2023-12-' + str(random.randint(1, 28))
            })
        
        # 如果有真实评论，将它们与示例评论合并
        if reviews:
            real_reviews = [{
                'rating': review.rating,
                'comment': review.comment,
                'user': {
                    'name': review.user.name,
                    'email': review.user.email
                },
                'created_time': review.created_time.strftime("%Y-%m-%d")
            } for review in reviews]
            
            # 合并并限制总数为8
            all_reviews = real_reviews + sample_reviews
            reviews = all_reviews[:8]
        else:
            reviews = sample_reviews

    return render(request, 'main/home.html', {
        'categories': categories,
        'new_releases': new_releases,
        'user_info': user_info,  # 传递用户信息到模板
        'reviews': reviews,  # 传递评论数据到模板
    })

def subscribe(request):
    """订阅处理逻辑"""
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get("email")

        # 验证email是否已订阅
        if Subscription.objects.filter(email=email).exists():
            messages.error(request, "Email already subscribed")
            return redirect("home")

        # 创建新的订阅
        Subscription.objects.create(name=name, email=email)
        messages.success(request, "Successfully subscribed")
        return redirect("home")

    return JsonResponse({"error": "Invalid request"}, status=400)

def search(request):
    """搜索产品"""
    query = request.GET.get('q', '')
    
    if query:
        # 搜索产品名称或描述中包含查询词的产品
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(details__icontains=query)
        ).filter(status='active')
    else:
        products = Product.objects.filter(status='active')
    
    # 准备分类选项
    categories = [{'key': key, 'name': name} for key, name in Product.CATEGORY_CHOICES]
    
    return render(request, 'main/search_results.html', {
        'products': products,
        'search_query': query,
        'categories': categories
    })

def about_us(request):
    """关于我们页面"""
    return render(request, 'main/about_us.html')

def contact(request):
    """联系我们页面"""
    success = False
    
    if request.method == "POST":
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        message = request.POST.get('message', '')
        
        if name and email and message:
            # 这里可以添加发送邮件或保存联系信息的逻辑
            success = True
        else:
            messages.error(request, '请填写所有必填字段')
    
    return render(request, 'main/contact.html', {'success': success})

def story1(request):
    return render(request, 'main/story1.html')

def story2(request):
    return render(request, 'main/story2.html')

def story3(request):
    return render(request, 'main/story3.html')