from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from main_system import models
from main_system.models import Cart, CartItem, Product, Order, OrderItem, User, HistoryNew
from django.utils import timezone

from main_system.views.order import create_order


# ==========================
# Shopping Cart
# ==========================
def cart_view(request):
    """Shopping Cart Page"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')
    
    try:
        # Get user information
        user = User.objects.filter(id=user_info['id']).first()
        if not user:
            messages.error(request, 'User does not exist')
            return redirect('/customer/register/')
        
        # Get or create shopping cart
        cart = Cart.objects.filter(user=user).first()
        if not cart:
            cart = Cart.objects.create(user=user)
        
        # Update cart count in session
        request.session['cart_count'] = cart.items.count()
        
        return render(request, 'cart/cart_view.html', {
            'cart': cart,
            'user_info': user_info  # Pass user information to template
        })
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('/')


def cart_add(request, product_id):
    """Add product to shopping cart"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        # Get product
        product = get_object_or_404(Product, id=product_id, status='active')
        
        # Check stock
        if quantity > product.stock:
            quantity = product.stock
            messages.warning(request, f'Insufficient stock, quantity adjusted to maximum available stock: {product.stock}')
        
        # Get or create shopping cart
        user = User.objects.filter(id=user_info['id']).first()
        if not user:
            messages.error(request, 'User does not exist')
            return redirect('/customer/register/')
            
        cart = Cart.objects.filter(user=user).first()
        if not cart:
            cart = Cart.objects.create(user=user)
        
        # Check if product is already in the cart
        cart_item = CartItem.objects.filter(cart=cart, product=product).first()
        if cart_item:
            # Update quantity, ensure it does not exceed stock
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock:
                new_quantity = product.stock
                messages.warning(request, f'Insufficient stock, quantity adjusted to maximum available stock: {product.stock}')
            cart_item.quantity = new_quantity
            cart_item.save()
            messages.success(request, 'Product quantity updated')
        else:
            # Create new cart item
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity
            )
            messages.success(request, 'Product added to cart')
        
        # Update cart count in session
        cart_count = cart.items.count()
        request.session['cart_count'] = cart_count
        
        # If AJAX request, return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Product added to cart',
                'cart_count': cart_count
            })
        
        # Return to previous page
        return redirect(request.META.get('HTTP_REFERER', '/products/product/collection/'))
    
    return redirect('/products/product/collection/')


def cart_edit(request, cart_item_id):
    """Edit product quantity in shopping cart"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        user = User.objects.filter(id=user_info['id']).first()
        if not user:
            messages.error(request, 'User does not exist')
            return redirect('/customer/register/')
        
        # Get cart item
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=user)
        
        # Check stock
        if quantity > cart_item.product.stock:
            quantity = cart_item.product.stock
            messages.warning(request, f'Insufficient stock, quantity adjusted to maximum available stock: {cart_item.product.stock}')
        
        if quantity > 0:
            # Update quantity
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Product quantity updated')
        else:
            # Delete product
            cart_item.delete()
            messages.success(request, 'Product removed from cart')
            
        # Get updated cart data
        cart = Cart.objects.get(user=user)
        
        # Update cart count in session
        cart_count = cart.items.count()
        request.session['cart_count'] = cart_count
        
        # If AJAX request, return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Cart updated',
                'cart_count': cart_count,
                'cart_total': float(cart.get_total_amount())
            })
            
        return redirect('/customer/cart/')


def cart_delete(request, cart_item_id):
    """Remove product from shopping cart"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')
    
    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')
    
    # Get cart item
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=user)
    cart_item.delete()
    messages.success(request, 'Product removed from cart')
    
    # Get updated cart data
    cart = Cart.objects.get(user=user)
    
    # Update cart count in session
    cart_count = cart.items.count()
    request.session['cart_count'] = cart_count
    
    # If AJAX request, return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': 'Product removed from cart',
            'cart_count': cart_count,
            'cart_total': float(cart.get_total_amount())
        })
        
    return redirect('/customer/cart/')


def checkout(request):
    """Create order from shopping cart and redirect to shipping information page"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    cart = Cart.objects.filter(user=user).first()
    if not cart or not cart.items.exists():
        messages.error(request, 'Shopping cart is empty')
        return redirect('/customer/cart/')

    # Call create_order to create order
    return create_order(request)