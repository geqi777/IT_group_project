from django.shortcuts import render, redirect
from main_system.models import Product, Subscription
from django.http import JsonResponse
from django.contrib import  messages

def homepage(request):
    """主页视图"""
    # 获取用户信息
    user_info = request.session.get('info')
    
    # 准备分类选项
    categories = [{'key': key, 'name': name} for key, name in Product.CATEGORY_CHOICES]
    
    # 获取最新商品
    new_releases = Product.objects.filter(status='active').order_by('-created_time')[:6]

    return render(request, 'main/home.html', {
        'categories': categories,
        'new_releases': new_releases,
        'user_info': user_info,  # 传递用户信息到模板
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