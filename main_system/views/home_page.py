from django.shortcuts import render, redirect
from main_system.models import Product, Subscription
from django.http import JsonResponse
from django.contrib import  messages

def homepage(request):
    """主页视图"""
    categories = Product.CATEGORY_CHOICES
    new_releases = Product.objects.filter(status='active').order_by('-created_time')[:6]  # 最新发布的6个商品

    return render(request, 'main/home.html',{
        'categories': categories,
        'new_releases': new_releases,
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