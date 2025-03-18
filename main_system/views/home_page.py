from django.shortcuts import render, redirect
from main_system.models import Product, Subscription, Review, User
from django.http import JsonResponse
from django.contrib import  messages
from django.db.models import Q
import random

def homepage(request):
    """Homepage view"""
    # Get user information
    user_info = request.session.get('user_info')
    
    # Prepare category options
    categories = [{'key': key, 'name': name} for key, name in Product.CATEGORY_CHOICES]
    
    # Get latest products
    new_releases = Product.objects.filter(status='active').order_by('-created_time')[:6]
    
    # Get review data
    reviews = Review.objects.select_related('user', 'product').order_by('-created_time')[:10]
    
    # If there are not enough reviews, create some sample review data
    if len(reviews) < 5:
        sample_reviews = []
        sample_comments = [
            "Very satisfied with this product, great quality and beautiful packaging!",
            "Unique design, very creative, looks even better than I imagined!",
            "Fine workmanship, details are well handled, looking forward to your new products!",
            "My friend liked it too, already recommended to her, will buy again next time!",
            "Fast logistics, good customer service, great overall shopping experience!",
            "Tried it immediately after receiving, exceeded expectations, perfect for gifts!",
            "Reasonable price, high cost performance, the best choice among similar products!",
            "Very practical product, solved many of my problems, thank you for your dedication!"
        ]
        
        sample_users = [
            {"name": "Li Ming", "email": "liming@example.com"},
            {"name": "Zhang Hua", "email": "zhanghua@example.com"},
            {"name": "Wang Fang", "email": "wangfang@example.com"},
            {"name": "Zhao Li", "email": "zhaoli@example.com"},
            {"name": "Liu Wei", "email": "liuwei@example.com"}
        ]
        
        for i in range(5):
            rating = random.randint(4, 5)  # Random 4-5 star rating
            comment = random.choice(sample_comments)
            user = sample_users[i % len(sample_users)]
            
            sample_reviews.append({
                'rating': rating,
                'comment': comment,
                'user': user,
                'created_time': '2023-12-' + str(random.randint(1, 28))
            })
        
        # If there are real reviews, merge them with sample reviews
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
            
            # Merge and limit total to 8
            all_reviews = real_reviews + sample_reviews
            reviews = all_reviews[:8]
        else:
            reviews = sample_reviews

    return render(request, 'main/home.html', {
        'categories': categories,
        'new_releases': new_releases,
        'user_info': user_info,  # Pass user information to template
        'reviews': reviews,  # Pass review data to template
    })

def subscribe(request):
    """Subscription handling logic"""
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get("email")

        # Verify if email is already subscribed
        if Subscription.objects.filter(email=email).exists():
            messages.error(request, "Email already subscribed")
            return redirect("home")

        # Create new subscription
        Subscription.objects.create(name=name, email=email)
        messages.success(request, "Successfully subscribed")
        return redirect("home")

    return JsonResponse({"error": "Invalid request"}, status=400)

def search(request):
    """Search products"""
    query = request.GET.get('q', '')
    
    if query:
        # Search for products containing the query in name or description
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(details__icontains=query)
        ).filter(status='active')
    else:
        products = Product.objects.filter(status='active')
    
    # Prepare category options
    categories = [{'key': key, 'name': name} for key, name in Product.CATEGORY_CHOICES]
    
    return render(request, 'main/search_results.html', {
        'products': products,
        'search_query': query,
        'categories': categories
    })

def about_us(request):
    """About Us page"""
    return render(request, 'main/about_us.html')

def contact(request):
    """Contact Us page"""
    success = False
    
    if request.method == "POST":
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        message = request.POST.get('message', '')
        
        if name and email and message:
            # Logic for sending email or saving contact information can be added here
            success = True
        else:
            messages.error(request, 'Please fill in all required fields')
    
    return render(request, 'main/contact.html', {'success': success})

def story1(request):
    return render(request, 'main/story1.html')

def story2(request):
    return render(request, 'main/story2.html')

def story3(request):
    return render(request, 'main/story3.html')