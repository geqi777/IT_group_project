from main_system import models
from main_system.models import Product
from main_system.utils.pagination import PageNumberPagination
from main_system.utils.boostrapModelForm import Product_ModelForm, Product_EditForm
from django.shortcuts import render, redirect
from django.db.models import Q, Case, When, IntegerField

from django.contrib import messages
from django.core.paginator import Paginator
from main_system.views.admin_dashboard import admin_message

# ==========================
# Admin Functions
# ==========================
# 1-1
@admin_message
def product_list(request):
    """ View and manage product list """
    data = models.Product.objects.all()

    # Get page_size from request, default is 20
    page_size = request.GET.get('page_size', 20)
    if isinstance(page_size, str) and page_size.isdecimal():  # Ensure page_size is a number
        page_size = int(page_size)
    else:
        page_size = 20  # Set default value

    # Create pagination object and pass page_size
    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {'page_obj': page_obj.queryset,
               'page_string': page_obj.html(),
               }
    return render(request, 'operation/admin_product_list.html', context)


@admin_message
def product_add(request):
    """ Add new product """
    if request.method == 'GET':
        form = Product_ModelForm()
        return render(request, 'main/change.html', {"form": form})

    form = Product_ModelForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        messages.success(request, "Product added successfully.")
        return redirect('/operation/homepage/products/')

    return render(request, 'main/change.html', {"form": form})


@admin_message
def product_edit(request, product_id):
    """ Edit product information """
    row = models.Product.objects.filter(id=product_id).first()

    if request.method == 'GET':
        form = Product_EditForm(instance=row)
        return render(request, 'main/change.html', {"form": form})

    form = Product_EditForm(request.POST, request.FILES, instance=row)
    if form.is_valid():
        form.save()
        messages.success(request, "Product edited successfully.")
        return redirect('/operation/homepage/products/')

    return render(request, 'main/change.html', {"form": form})


@admin_message
def product_delete(request, product_id):
    """ Delete product """
    product = models.Product.objects.filter(id=product_id).first()
    product.delete()
    return redirect('/operation/homepage/products/')


# ==========================
# User Functions
# ==========================

def product_page(request):
    """ Product browsing page + filtering + sorting """
    # Get filter parameters
    query = request.GET.get('q', '')
    categories = request.GET.getlist('category', [])
    sort_by = request.GET.get('sort', 'newest')
    price_range = request.GET.get('price_range', 'any')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    # Basic query: only show active products
    products = Product.objects.filter(status='active')

    # Apply search filter
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    # Apply category filter
    if categories:
        products = products.filter(category__in=categories)

    # Apply price filter
    if price_range != 'any':
        if price_range == 'custom' and price_min and price_max:
            products = products.filter(price__gte=float(price_min), price__lte=float(price_max))
        elif price_range != 'custom':
            price_min, price_max = price_range.split(',')
            if price_min:
                products = products.filter(price__gte=float(price_min))
            if price_max:
                products = products.filter(price__lte=float(price_max))

    # Apply sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_time')
    elif sort_by == 'relevance' and query:  # Apply relevance sorting only if there is a search query
        products = products.annotate(
            relevance=Case(
                When(name__icontains=query, then=2),  # Higher weight for name match
                When(description__icontains=query, then=1),  # Lower weight for description match
                default=0,
                output_field=IntegerField(),
            )
        ).order_by('-relevance', '-created_time')
    else:  # Default to sorting by newest
        products = products.order_by('-created_time')

    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(products, 9)  # Show 9 products per page
    page_obj = paginator.get_page(page_number)

    # Prepare category options
    all_categories = [{'key': key, 'name': name} for key, name in Product.CATEGORY_CHOICES]

    context = {
        'products': page_obj,
        'categories': all_categories,
        'selected_categories': categories,
        'current_sort': sort_by,
        'selected_price_range': price_range,
    }

    return render(request, 'products/product_page.html', context)


def product_detail(request, product_id):
    """User view product details (including stock information)"""
    product = models.Product.objects.filter(id=product_id, status='active').first()
    quantity_range = range(1, product.stock + 1) if product.stock > 0 else []
    return render(request, 'products/product_detail.html', {'product': product, 'quantity_range': quantity_range})


def search_products(request):
    """Search products"""
    query = request.GET.get('q', '')
    if query:
        # Search from name and category
        products = Product.objects.filter(
            Q(name__icontains=query) |  # Name contains keyword
            Q(category__icontains=query)  # Category contains keyword
        ).filter(status='active').distinct()  # Only show active products
    else:
        products = Product.objects.filter(status='active')

    # Pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    products = paginator.get_page(page)

    return render(request, 'products/product_page.html', {
        'products': products,
        'search_query': query,
        'categories': [{'key': key, 'name': name} for key, name in Product.CATEGORY_CHOICES]  # Add category options
    })


