from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from decimal import Decimal
import re
from datetime import timedelta

from main_system.views.home_page import subscribe
from django.http import HttpRequest

from main_system import models
from main_system.models import Order, OrderItem, Cart, CartItem, User, WalletTransaction, HistoryNew, Operator, Subscription, PaymentCard, PromoCode
from main_system.utils.pagination import PageNumberPagination
from main_system.views.admin_dashboard import admin_message, user_message


@user_message
def create_order(request):
    """Create order from cart"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        request.user_messages.error('Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    cart = Cart.objects.filter(user=user).first()
    if not cart or not cart.items.exists():
        request.user_messages.error('Cart is empty, cannot create order')
        return redirect('/customer/cart/')

    try:
        with transaction.atomic():
            # Generate order number
            order_number = timezone.now().strftime('%Y%m%d%H%M%S') + str(user.id).zfill(4)

            # Create order
            order = Order.objects.create(
                user=user,
                order_number=order_number,
                shipping_address=user.address or '',
                order_status='pending',
                subtotal_amount=cart.get_subtotal_amount(),
                shipping_fee=cart.get_shipping_fee(),
                vat=cart.get_vat(),
                total_amount=cart.get_total_amount(),
                final_amount=cart.get_total_amount()  # Initially, final_amount equals total_amount
            )

            # Create order items
            order_items = []
            for cart_item in cart.items.all():
                order_items.append(
                    OrderItem(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price,
                        item_subtotal=cart_item.get_item_subtotal()
                    )
                )

            # Bulk create order items
            OrderItem.objects.bulk_create(order_items)

            # Record history
            # HistoryNew.objects.create(
            #     user=user,
            #     order=order,
            #     history_type='order_created',
            #     amount=cart.get_total_amount(),
            #     details=f'Created order: {order.order_number}'
            # )

            # Store order ID in session
            request.session['current_order_id'] = order.id

            # Clear cart
            cart.items.all().delete()
            
            # Update cart count in session to 0
            request.session['cart_count'] = 0

            return redirect(f'/customer/order/{order.id}/shipping/')

    except Exception as e:
        messages.error(request, f'Order creation failed: {str(e)}')
        return redirect('/customer/cart/')


@user_message
def order_list(request):
    """Order list"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        request.user_messages.error('Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        request.user_messages.error('User does not exist')
        return redirect('/customer/register/')

    orders = Order.objects.filter(user=user).order_by('-timestamp')
    
    # Check if there are returned items and if all items are reviewed for each order
    for order in orders:
        order.has_returned_items = False
        order.all_reviewed = True
        order.has_refunded_items = False
        
        for item in order.items.all():
            # Check return status
            if item.return_status == 'refunded':
                order.has_refunded_items = True
            elif item.return_status != 'none' and item.return_status != 'rejected':
                order.has_returned_items = True
            
            # Check review status
            if not hasattr(item, 'review') or not item.review:
                order.all_reviewed = False

    # Pagination
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)

    return render(request, 'orders/order_list.html', {'orders': orders})


@user_message
def order_detail(request, order_id):
    """Order detail"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        request.user_messages.error('Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        request.user_messages.error('User does not exist')
        return redirect('/customer/register/')

    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        request.user_messages.error('Order does not exist')
        return redirect('/customer/order/list/')

    # Check if there are any items being returned or already returned
    has_returned_items = False
    for item in order.items.all():
        if item.return_status != 'none' and item.return_status != 'rejected':
            has_returned_items = True
            break

    # Prefetch related reviews for order items to optimize performance
    from django.db.models import Prefetch
    from main_system.models import Review
    order_with_reviews = Order.objects.prefetch_related(
        Prefetch('items__review', queryset=Review.objects.all())
    ).get(id=order_id)
    
    # Prepare order item data, only including basic information
    items_with_data = []
    for item in order_with_reviews.items.all():
        items_with_data.append({
            'item': item,
            'subtotal': float(item.price) * item.quantity
        })

    # Calculate all necessary values
    context = {
        'order': order_with_reviews,
        'points_value': float(order.points_used) * 0.01 if order.points_used else 0,
        'items_with_data': items_with_data,
        'has_returned_items': has_returned_items
    }

    if request.method == 'POST':
        # Handle order actions
        action = request.POST.get('action')

        if action == 'cancel':
            if order.order_status == 'pending':
                order.order_status = 'cancelled'
                order.save()

                # Record history
                HistoryNew.objects.create(
                    user=user,
                    order=order,
                    history_type='order_cancelled',
                    amount=order.total_amount,
                    details='User cancelled order'
                )

                messages.success(request, 'Order has been cancelled')
            else:
                messages.error(request, 'Current order status cannot be cancelled')

        elif action == 'pay':
            if order.order_status == 'pending':
                # Handle payment logic
                payment_method = request.POST.get('payment_method')
                if payment_method == 'wallet':
                    if user.wallet.balance >= order.total_amount:
                        with transaction.atomic():
                            # Deduct wallet balance
                            user.wallet.balance -= order.total_amount
                            user.wallet.save()

                            # Update order status
                            order.payment_method = 'wallet'
                            order.payment_status = True
                            order.order_status = 'paid'
                            order.paid_time = timezone.now()
                            order.save()

                            # Record history
                            HistoryNew.objects.create(
                                user=user,
                                order=order,
                                history_type='order_paid',
                                amount=order.total_amount,
                                details=f'Wallet payment for order: {order.order_number}'
                            )

                            # Record wallet transaction
                            WalletTransaction.objects.create(
                                wallet=user.wallet,
                                transaction_type='purchase',
                                amount=order.total_amount,
                                details=f'Order payment: {order.order_number}'
                            )

                            messages.success(request, 'Payment successful')
                    else:
                        messages.error(request, 'Insufficient wallet balance')
                else:
                    messages.error(request, 'Other payment methods are not supported yet')
            else:
                messages.error(request, 'Current order status cannot be paid')

    return render(request, 'orders/order_detail.html', context)


def history_list(request):
    """User history records"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    histories = HistoryNew.objects.filter(user=user).select_related('order').order_by('-timestamp')

    # Pagination
    paginator = Paginator(histories, 10)
    page = request.GET.get('page')
    histories = paginator.get_page(page)

    return render(request, 'orders/history_list.html', {'histories': histories})


def shipping(request, order_id):
    """Order shipping information page"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    # Get order
    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        messages.error(request, 'Order does not exist')
        return redirect('/customer/cart/')

    if request.method == 'POST':
        # Check if it is a cancel order request
        if request.POST.get('action') == 'cancel':
            try:
                with transaction.atomic():
                    # Restore cart items
                    cart = Cart.objects.get_or_create(user=user)[0]
                    for order_item in order.items.all():
                        CartItem.objects.create(
                            cart=cart,
                            product=order_item.product,
                            quantity=order_item.quantity,
                            add_time=timezone.now()
                        )

                    # Delete order and order items
                    order.delete()

                    # Clear order ID from session
                    if 'current_order_id' in request.session:
                        del request.session['current_order_id']

                    messages.success(request, 'Returned to cart')
                    return redirect('/customer/cart/')
            except Exception as e:
                messages.error(request, f'Operation failed: {str(e)}')
                return redirect(f'/customer/order/{order.id}/shipping/')

        # Handle address selection
        address_choice = request.POST.get('address_choice')

        # Get contact information
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')

        # Validate required fields
        if not all([first_name, last_name, email]):
            messages.error(request, 'Please fill in complete contact information')
            return redirect(f'/customer/order/{order.id}/shipping/')

        # Handle address information
        if address_choice == 'existing' and user.address:
            # Use existing address
            shipping_address = user.address
        else:
            # Get new address information
            shipping_address = request.POST.get('shipping_address')
            city = request.POST.get('city')
            postcode = request.POST.get('postcode')
            country = request.POST.get('country')

            # Validate required fields
            if not all([shipping_address, city, postcode, country]):
                messages.error(request, 'Please fill in complete address information')
                return redirect(f'/customer/order/{order.id}/shipping/')

            # Combine complete address
            shipping_address = f"{shipping_address}, {city}, {postcode}, {country}"

            # If user chooses to save address (optional)
            if request.POST.get('save_info'):
                user.address = shipping_address
                user.save()

        # Update order information
        order.shipping_address = shipping_address
        order.contact_name = f"{first_name} {last_name}".strip()
        order.contact_email = email
        order.save()

        # Handle subscription (optional)
        if request.POST.get('newsletter'):
            Subscription.objects.get_or_create(
                email=email,
                defaults={'name': f"{first_name} {last_name}".strip()}
            )

        return redirect(f'/customer/order/{order.id}/payment/')

    # Recalculate order amount
    order.subtotal_amount = sum(item.item_subtotal for item in order.items.all())
    order.shipping_fee = Decimal('0') if order.subtotal_amount >= Decimal('30') else Decimal('5')
    order.vat = order.subtotal_amount * Decimal('0.05')
    order.total_amount = order.subtotal_amount + order.shipping_fee + order.vat
    order.final_amount = order.total_amount
    order.save()

    return render(request, 'orders/shipping.html', {
        'user': user,
        'order': order
    })


def payment(request, order_id):
    """Handle order payment"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    # Get order
    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        messages.error(request, 'Order does not exist')
        return redirect('/customer/cart/')

    # Get or create wallet
    wallet, _ = models.Wallet.objects.get_or_create(
        user=user,
        defaults={'balance': Decimal('0'), 'points': 0}
    )

    # Calculate if points can be used for payment
    points_needed = order.final_amount * 100  # Assume 1 unit = 100 points
    can_use_points = wallet.points >= points_needed

    # Get user's saved payment cards
    saved_cards = models.PaymentCard.objects.filter(user=user)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')

        try:
            if payment_method == 'wallet':
                if wallet.balance >= order.final_amount:
                    # Wallet payment logic
                    with transaction.atomic():
                        wallet.balance -= order.final_amount
                        wallet.save()

                        order.payment_method = 'wallet'
                        order.payment_status = True
                        order.paid_time = timezone.now()
                        order.order_status = 'paid'
                        order.save()
                    # Record wallet transaction
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            transaction_type='purchase',
                            amount=order.final_amount,
                            details=f'Order payment: {order.order_number}'
                        )

                        # Record order history
                        HistoryNew.objects.create(
                            user=user,
                            order=order,
                            history_type='order_paid',
                            amount=order.final_amount,
                            details=f'Wallet payment for order: {order.order_number}'
                        )

                    messages.success(request, 'Payment successful!')
                    return redirect(f'/customer/order/{order.id}/detail/')
                else:
                    messages.error(request, 'Insufficient wallet balance')

            elif payment_method == 'points':
                if can_use_points:
                    # Points payment logic
                    with transaction.atomic():
                        wallet.points -= points_needed
                        wallet.save()

                        order.payment_method = 'points'
                        order.points_used = points_needed
                        order.payment_status = True
                        order.paid_time = timezone.now()
                        order.order_status = 'paid'
                        order.save()
                    # Record wallet transaction
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            transaction_type='points_decrease',
                            points=points_needed,
                            details=f'Points payment for order: {order.order_number}'
                        )

                        # Record order history
                        HistoryNew.objects.create(
                            user=user,
                            order=order,
                            history_type='order_paid',
                            points=points_needed,
                            details=f'Points payment for order: {order.order_number}'
                        )

                    messages.success(request, 'Points payment successful!')
                    return redirect(f'/customer/order/{order.id}/detail/')
                else:
                    messages.error(request, 'Insufficient points')

            elif payment_method == 'card':
                saved_card_id = request.POST.get('saved_card_id')

                if saved_card_id:
                    # Use saved card for payment
                    card = get_object_or_404(models.PaymentCard, id=saved_card_id, user=user)

                    # Handle saved card payment logic
                    with transaction.atomic():
                        order.payment_method = 'card'
                        order.payment_card = card
                        order.payment_status = True
                        order.paid_time = timezone.now()
                        order.order_status = 'paid'
                        order.save()

                        # Record order history
                        HistoryNew.objects.create(
                            user=user,
                            order=order,
                            history_type='order_paid',
                            amount=order.final_amount,
                            details=f'Credit card payment for order: {order.order_number}'
                        )
                        
                        # Record wallet transaction - add card payment record
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            transaction_type='card_payment',
                            amount=order.final_amount,
                            payment_card=order.payment_card,
                            details=f'Credit card payment for order: {order.order_number}'
                        )
                else:
                    # Handle new card payment
                    nickname = request.POST.get('nickname')
                    card_number = request.POST.get('card_number')
                    expiry_date = request.POST.get('expiry_date')
                    cvv = request.POST.get('cvv')
                    country = request.POST.get('country')
                    postcode = request.POST.get('postcode')
                    save_card = request.POST.get('save_card') == 'on'

                    # Validate card information
                    if not all([card_number, expiry_date, cvv, country, postcode]):
                        messages.error(request, 'Please fill in complete card information')
                        return redirect(f'/customer/order/{order.id}/payment/')

                    # Validate card number format
                    if not re.match(r'^\d{16}$', card_number.replace(' ', '')):
                        messages.error(request, 'Invalid card number')
                        return redirect(f'/customer/order/{order.id}/payment/')

                    # Validate expiry date format
                    if not re.match(r'^\d{2}/\d{2}$', expiry_date):
                        messages.error(request, 'Invalid expiry date format')
                        return redirect(f'/customer/order/{order.id}/payment/')

                    # Validate CVV format
                    if not re.match(r'^\d{3}$', cvv):
                        messages.error(request, 'Invalid CVV code')
                        return redirect(f'/customer/order/{order.id}/payment/')

                    with transaction.atomic():
                        if save_card:
                            # Save new card
                            card = models.PaymentCard.objects.create(
                                user=user,
                                nickname=nickname or 'Unnamed card',
                                card_number=card_number.replace(' ', ''),
                                expiry_date=expiry_date,
                                country=country,
                                postcode=postcode.upper()
                            )
                            order.payment_card = card
                        else:
                            # Create temporary card object but do not save to database
                            card = models.PaymentCard(
                                user=user,
                                nickname='One-time card',
                                card_number=card_number.replace(' ', ''),
                                expiry_date=expiry_date,
                                country=country,
                                postcode=postcode.upper()
                            )
                            if save_card:
                                card.save()
                            order.payment_card = card if save_card else None

                        order.payment_method = 'card'
                        order.payment_status = True
                        order.paid_time = timezone.now()
                        order.order_status = 'paid'
                        order.save()

                        # Record order history
                        HistoryNew.objects.create(
                            user=user,
                            order=order,
                            history_type='order_paid',
                            amount=order.final_amount,
                            details=f'Credit card payment for order: {order.order_number}'
                        )
                        
                        # Record wallet transaction - add card payment record
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            transaction_type='card_payment',
                            amount=order.final_amount,
                            payment_card=card if save_card else None,
                            details=f'Credit card payment for order: {order.order_number}'
                        )

                messages.success(request, 'Payment successful!')
                return redirect(f'/customer/order/{order.id}/detail/')

        except Exception as e:
            messages.error(request, f'Payment failed: {str(e)}')
            return redirect(f'/customer/order/{order.id}/payment/')

    context = {
        'order': order,
        'wallet': wallet,
        'can_use_points': can_use_points,
        'points_needed': points_needed,
        'saved_cards': saved_cards,
    }

    return render(request, 'orders/payment.html', context)


@user_message
def order_cancel(request, order_id):
    """Cancel order (supports unpaid and paid orders)"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        request.user_messages.error('Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        request.user_messages.error('User does not exist')
        return redirect('/customer/register/')

    order = Order.objects.get(id=order_id, user=user)

    # Check order status
    if order.order_status not in ['pending', 'paid', 'shipped']:
        request.user_messages.error('Current order status cannot be cancelled')
        return redirect('/customer/order/{{ order.id }}/detail/')

    try:
        with transaction.atomic():
            if order.order_status == 'pending':
                # Unpaid orders are directly cancelled
                order.order_status = 'cancelled'
                order.save()

                messages.success(request, 'Order has been cancelled')
            else:
                # Paid orders require a created_time
                if order.payment_method == 'wallet':
                    # Wallet refund
                    user.wallet.balance += order.final_amount
                    user.wallet.save()

                    # Record refund transaction
                    WalletTransaction.objects.create(
                        wallet=user.wallet,
                        transaction_type='refund',
                        amount=order.final_amount,
                        details=f'Order {order.order_number} cancellation refund'
                    )
                elif order.payment_method == 'points':
                    # Points refund
                    user.wallet.points += order.points_used
                    user.wallet.save()

                    # Record points refund
                    WalletTransaction.objects.create(
                        wallet=user.wallet,
                        transaction_type='points_refund',
                        points=order.points_used,
                        details=f'Order {order.order_number} cancellation points refund'
                    )
                elif order.payment_method == 'card':
                    # Credit card refund logic (requires integration with payment gateway refund API)
                    pass

                # Restore product stock
                for item in order.items.all():
                    item.product.stock += item.quantity
                    item.product.save()

                # If the order is completed, deduct the previously earned points
                if order.points_earned > 0 and order.order_status == 'completed':
                    # Ensure points do not become negative
                    points_to_deduct = min(user.wallet.points, order.points_earned)
                    if points_to_deduct > 0:
                        user.wallet.points -= points_to_deduct
                        user.wallet.save()
                        
                        # Record points deduction transaction
                        WalletTransaction.objects.create(
                            wallet=user.wallet,
                            transaction_type='points_used',
                            points=points_to_deduct,
                            details=f'Order {order.order_number} cancellation points deduction'
                        )

                # Update order status
                order.order_status = 'refunded'
                order.save()

                messages.success(request, 'Order has been cancelled, refund will be processed within 3-5 business days')

            # Record order history
            HistoryNew.objects.create(
                user=user,
                order=order,
                history_type='order_cancelled',
                amount=order.final_amount if order.payment_status else None,
                points=order.points_used if order.payment_method == 'points' else None,
                details=f'User cancelled order: {order.order_number}'
            )

    except Exception as e:
        messages.error(request, f'Order cancellation failed: {str(e)}')

    return redirect('/customer/order/')

@user_message
def order_confirm_receipt(request, order_id):
    """Confirm receipt"""
     # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        request.user_messages.error('Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        request.user_messages.error('User does not exist')
        return redirect('/customer/register/')

    order = Order.objects.get(id=order_id, user=user)

    if order.order_status != 'delivered':
        request.user_messages.error('Current order status cannot confirm receipt')
        return redirect('order_detail', order_id=order_id)

    order.order_status = 'completed'
    order.complete_time = timezone.now()
    order.save()

    request.user_messages.success('Receipt confirmed')
    return redirect('/customer/order/')

@user_message
def order_review(request, order_id):
    """Order review"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        request.user_messages.error('Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        request.user_messages.error('User does not exist')
        return redirect('/customer/register/')

    order = get_object_or_404(Order, id=order_id, user=user)

    if order.order_status != 'completed':
        messages.error(request, 'Only completed orders can be reviewed')
        return redirect('/customer/order/')

    # Get reviewed and unreviewed order items
    reviewed_items = []
    unreviewed_items = []

    for item in order.items.all():
        if hasattr(item, 'review'):
            reviewed_items.append(item)
        else:
            unreviewed_items.append(item)
    
    # If there are no unreviewed items, inform the user and return to order list
    if not unreviewed_items:
        messages.info(request, 'All items in this order have been reviewed, no need to review again')
        return redirect('/customer/order/')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                for item in unreviewed_items:
                    rating = request.POST.get(f'rating_{item.id}')
                    comment = request.POST.get(f'comment_{item.id}')

                    if rating and comment:
                        item.add_review(int(rating), comment)

                messages.success(request, 'Review submitted successfully')
                return redirect('/customer/order/')
        except Exception as e:
            messages.error(request, f'Review submission failed: {str(e)}')

    context = {
        'order': order,
        'reviewed_items': reviewed_items,
        'unreviewed_items': unreviewed_items,
    }

    return render(request, 'orders/order_review.html', context)

def order_return(request, order_id):
    """Request return"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    order = get_object_or_404(Order, id=order_id, user=user)

    if order.order_status != 'completed':
        messages.error(request, 'Only completed orders can request return')
        return redirect('/customer/order/')

    if request.method == 'POST':
        try:
            return_items = request.POST.getlist('return_items')
            return_reason = request.POST.get('return_reason')
            return_details = request.POST.get('return_details')

            if not return_items:
                messages.error(request, 'Please select items to return')
                return redirect('order_return', order_id=order_id)

            with transaction.atomic():
                # Update return status of order items
                for item_id in return_items:
                    item = get_object_or_404(OrderItem, id=item_id, order=order)
                    item.apply_return(return_reason, return_details)

                messages.success(request, 'Return request submitted, please wait for review')
                return redirect('/customer/order/')

        except Exception as e:
            messages.error(request, f'Return request failed: {str(e)}')

    return render(request, 'orders/order_return.html', {'order': order})

def order_delete(request, order_id):
    """Delete order record"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        messages.error(request, 'Order does not exist')
        return redirect('/customer/order/')

    if order.order_status == 'pending':
        messages.error(request, 'Unpaid orders cannot be deleted, please cancel the order first')
        return redirect('/customer/order/')

    order.delete()
    messages.success(request, 'Order record has been deleted')
    return redirect('/customer/order/')


# Admin port 1
@admin_message
def admin_order_list(request):
    """Admin view all orders"""
    # Check if admin is logged in
    operator_info = request.session.get('admin_info')
    if not operator_info:
        messages.error(request, 'Please log in first')
        return redirect('/operation/login/')

    # Verify if it is an admin
    operator = Operator.objects.filter(id=operator_info['employee_id']).first()
    if not operator or not operator.is_operator:
        messages.error(request, 'Insufficient permissions')
        return redirect('/operation/login/')

    # Get filter parameters
    order_status = request.GET.get('order_status')
    return_status = request.GET.get('return_status')

    # Basic query
    order_items_query = OrderItem.objects.select_related('order', 'order__user', 'product').all()
    
    # Apply order status filter
    if order_status:
        order_items_query = order_items_query.filter(order__order_status=order_status)
    
    # Apply return status filter
    if return_status:
        order_items_query = order_items_query.filter(return_status=return_status)
    
    # Sort
    order_items = order_items_query.order_by('-order__timestamp')
    
    # Calculate return record count
    total_returns = OrderItem.objects.filter(return_status__in=['pending', 'approved', 'shipped', 'received', 'refunded']).count()

    # Pagination
    paginator = Paginator(order_items, 20)
    page = request.GET.get('page')
    order_items = paginator.get_page(page)

    return render(request, 'orders/admin_order_list.html', {
        'order_items': order_items,
        'operator': operator,
        'order_status': order_status,
        'return_status': return_status,
        'total_returns': total_returns,
    })


@admin_message
def update_order_status(request, order_id):
    """Admin update order status"""
    # Check if admin is logged in
    operator_info = request.session.get('admin_info')
    if not operator_info:
        messages.error(request, 'Please log in first')
        return redirect('/operation/login/')

    # Verify if it is an admin
    operator = Operator.objects.filter(id=operator_info['employee_id'], is_operator=True).first()
    if not operator:
        messages.error(request, 'Insufficient permissions')
        return redirect('/operation/login/')

    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')

        # Allowed status updates
        allowed_statuses = ['paid', 'shipped', 'delivered', 'completed', 'cancelled']
        
        if new_status in allowed_statuses:
            with transaction.atomic():
                # Save original status for recording
                old_status = order.order_status
                
                # Update order status
                order.order_status = new_status
                
                # If completing the order, set completion time and update points
                if new_status == 'completed':
                    order.complete_time = timezone.now()
                    # Calculate and add points
                    points_earned = int(order.final_amount * 10)  # Earn 10 points for every 1 unit spent
                    order.points_earned = points_earned
                    
                    # Update user wallet points - ensure wallet exists
                    wallet, created = models.Wallet.objects.get_or_create(
                        user=order.user,
                        defaults={'balance': Decimal('0'), 'points': 0}
                    )
                    wallet.points += points_earned
                    wallet.save()
                
                # If cancelling the order
                if new_status == 'cancelled':
                    # If the order is paid, handle refund
                    if old_status in ['paid', 'shipped', 'delivered']:
                        with transaction.atomic():
                            # Refund based on payment method
                            if order.payment_method == 'wallet':
                                # Refund to wallet
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                wallet.balance += order.final_amount
                                wallet.save()

                                # Record wallet refund transaction
                                WalletTransaction.objects.create(
                                    wallet=wallet,
                                    transaction_type='refund',
                                    amount=order.final_amount,
                                    details=f'Order {order.order_number} cancellation refund'
                                )
                            elif order.payment_method == 'points':
                                # Points refund
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                wallet.points += order.points_used
                                wallet.save()

                                # Record points refund transaction
                                WalletTransaction.objects.create(
                                    wallet=wallet,
                                    transaction_type='points_refund',
                                    points=order.points_used,
                                    details=f'Order {order.order_number} cancellation points refund'
                                )
                            elif order.payment_method == 'card':
                                # Credit card refund processing
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                
                                # Record credit card refund transaction
                                WalletTransaction.objects.create(
                                    wallet=wallet,
                                    transaction_type='refund',
                                    amount=order.final_amount,
                                    payment_card=order.payment_card,
                                    details=f'Order {order.order_number} cancellation refund to credit card'
                                )
                            
                            # Promo code handling: if the order used a promo code and this is the only item in the order or a full refund
                            if order.promo_code:
                                # Delete promo code usage record, allowing the user to use it again
                                HistoryNew.objects.filter(
                                    user=order.user,
                                    promo_code=order.promo_code,
                                    history_type='promo_code_used',
                                    order=order
                                ).delete()
                                
                                # Record promo code return operation
                                HistoryNew.objects.create(
                                    user=order.user,
                                    order=order,
                                    history_type='promo_code_returned',
                                    promo_code=order.promo_code,
                                    details=f'Order {order.order_number} cancellation, return promo code {order.promo_code.code}'
                                )
                            
                            # Restore all product stock
                            for item in order.items.all():
                                item.product.stock += item.quantity
                                item.product.save()

                            # Deduct previously earned points (if any)
                            if order.points_earned > 0 and old_status == 'completed':
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                # Ensure points do not become negative
                                points_to_deduct = min(wallet.points, order.points_earned)
                                if points_to_deduct > 0:
                                    wallet.points -= points_to_deduct
                                    wallet.save()
                                    
                                    # Record points deduction transaction
                                    WalletTransaction.objects.create(
                                        wallet=wallet,
                                        transaction_type='points_used',
                                        points=points_to_deduct,
                                        details=f'Order {order.order_number} cancellation points deduction'
                                    )

                            # Update order status to refunded
                            order.order_status = 'refunded'

                # Finally save the order status
                order.save()

                # Record history
                status_display = dict(Order.ORDER_STATUS_CHOICES).get(new_status, new_status)
                HistoryNew.objects.create(
                    user=order.user,
                    order=order,
                    history_type=f'order_{new_status}',
                    details=f'Order status updated from 【{dict(Order.ORDER_STATUS_CHOICES).get(old_status, old_status)}】 to 【{status_display}】'
                )

                messages.success(request, f'Order status has been updated to: {status_display}')
        else:
            messages.error(request, 'Invalid order status')

        # Redirect back to order detail page
        return redirect(f'/operation/homepage/orders/detail/{order_id}/')
    
    # If not a POST request, redirect to order list
    return redirect('/operation/homepage/orders/')


@admin_message
def process_return(request, order_id, item_id):
    """Admin process return request"""
    # Check if admin is logged in
    operator_id = request.session.get('admin_info')
    if not operator_id:
        messages.error(request, 'Please log in first')
        return redirect('/operation/login/')

    # Verify if it is an admin
    operator = Operator.objects.filter(id=operator_id['employee_id'], is_operator=True).first()
    if not operator:
        messages.error(request, 'Insufficient permissions')
        return redirect('/operation/login/')

    item = OrderItem.objects.filter(id=item_id, order_id=order_id).first()
    if not item:
        messages.error(request, 'Order item does not exist')
        return redirect(f'/operation/homepage/orders/detail/{order_id}/')

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['approved', 'rejected', 'received', 'refunded']:
            try:
                with transaction.atomic():
                    if status == 'refunded':
                        # Calculate refund amount
                        refund_amount = item.item_subtotal

                        # Handle refund
                        if item.order.payment_method == 'wallet':
                            # Ensure user has a wallet
                            wallet, created = models.Wallet.objects.get_or_create(
                                user=item.order.user,
                                defaults={'balance': Decimal('0'), 'points': 0}
                            )
                            wallet.balance += refund_amount
                            wallet.save()

                            # Record refund transaction
                            WalletTransaction.objects.create(
                                wallet=wallet,
                                transaction_type='refund',
                                amount=refund_amount,
                                details=f'Order {item.order.order_number} item return refund'
                            )
                        elif item.order.payment_method == 'points':
                            # Points refund
                            points_to_refund = int(refund_amount * 100)  # 1 unit = 100 points conversion
                            wallet, created = models.Wallet.objects.get_or_create(
                                user=item.order.user,
                                defaults={'balance': Decimal('0'), 'points': 0}
                            )
                            wallet.points += points_to_refund
                            wallet.save()

                            # Record points refund transaction
                            WalletTransaction.objects.create(
                                wallet=wallet,
                                transaction_type='points_refund',
                                points=points_to_refund,
                                details=f'Order {item.order.order_number} item return points refund'
                            )
                        elif item.order.payment_method == 'card':
                            # Credit card refund - record in wallet
                            wallet, created = models.Wallet.objects.get_or_create(
                                user=item.order.user,
                                defaults={'balance': Decimal('0'), 'points': 0}
                            )
                            
                            # Record credit card refund transaction
                            WalletTransaction.objects.create(
                                wallet=wallet,
                                transaction_type='refund',
                                amount=refund_amount,
                                payment_card=item.order.payment_card,
                                details=f'Order {item.order.order_number} item return refund to credit card'
                            )

                        # Restore product stock
                        item.product.stock += item.quantity
                        item.product.save()

                        # Update return status
                        item.process_return(status, refund_amount)
                        
                        # Record order history
                        HistoryNew.objects.create(
                            user=item.order.user,
                            order=item.order,
                            history_type='order_refunded',
                            amount=refund_amount,
                            details=f'Order item refund: {item.product.name} x {item.quantity}'
                        )

                        # Check if all order items are refunded or not returned, if so update the entire order status to refunded
                        all_items_refunded = True
                        for order_item in item.order.items.all():
                            if order_item.return_status not in ['refunded', 'none', 'rejected']:
                                all_items_refunded = False
                                break
                        
                        if all_items_refunded:
                            # Update order status to refunded
                            item.order.order_status = 'refunded'
                            
                            # If the order previously earned points, deduct those points
                            if item.order.points_earned > 0:
                                wallet, created = models.Wallet.objects.get_or_create(
                                    user=item.order.user,
                                    defaults={'balance': Decimal('0'), 'points': 0}
                                )
                                
                                # Ensure points do not become negative
                                points_to_deduct = min(wallet.points, item.order.points_earned)
                                if points_to_deduct > 0:
                                    wallet.points -= points_to_deduct
                                    wallet.save()
                                    
                                    # Record points deduction transaction
                                    WalletTransaction.objects.create(
                                        wallet=wallet,
                                        transaction_type='points_used',
                                        points=points_to_deduct,
                                        details=f'Order {item.order.order_number} refund deduct previously earned points'
                                    )
                            
                            item.order.save()

                        # Promo code handling: if the order used a promo code and this is the only item in the order or a full refund
                        if item.order.promo_code and (item.order.items.count() == 1 or all(i.return_status == 'refunded' for i in item.order.items.all())):
                            # Delete promo code usage record, allowing the user to use it again
                            HistoryNew.objects.filter(
                                user=item.order.user,
                                promo_code=item.order.promo_code,
                                history_type='promo_code_used',
                                order=item.order
                            ).delete()
                            
                            # Record promo code return operation
                            HistoryNew.objects.create(
                                user=item.order.user,
                                order=item.order,
                                history_type='promo_code_returned',
                                promo_code=item.order.promo_code,
                                details=f'Order {item.order.order_number} item return, return promo code {item.order.promo_code.code}'
                            )
                        # If the order has multiple items and used a promo code, the discount amount needs to be refunded proportionally
                        elif item.order.promo_code and item.order.promo_discount > 0:
                            # Calculate the proportion of the current item to the total order price
                            total_subtotal = sum(i.item_subtotal for i in item.order.items.all())
                            item_percentage = item.item_subtotal / total_subtotal if total_subtotal > 0 else 0
                            
                            # Calculate the discount amount to be refunded
                            refund_discount = item.order.promo_discount * item_percentage
                            
                            # Add the discount proportion to the refund amount
                            refund_amount += refund_discount

                    else:
                        item.process_return(status)
                        
                        # Record order history
                        action_map = {
                            'approved': 'Approved return request',
                            'rejected': 'Rejected return request',
                            'received': 'Confirmed return receipt'
                        }
                        HistoryNew.objects.create(
                            user=item.order.user,
                            order=item.order,
                            history_type='order_refunded' if status == 'refunded' else 'order_cancelled',
                            details=f'{action_map.get(status, status)}: {item.product.name} x {item.quantity}'
                        )

                    messages.success(request, f'Return status has been updated to: {dict(OrderItem.RETURN_STATUS_CHOICES).get(status, status)}')

            except Exception as e:
                messages.error(request, f'Processing failed: {str(e)}')
        else:
            messages.error(request, 'Invalid status')

    return redirect(f'/operation/homepage/orders/detail/{order_id}/')

@admin_message
def admin_order_detail(request, order_id):
    """Admin view order details"""
    # Check if admin is logged in
    operator_info = request.session.get('admin_info')
    if not operator_info:
        messages.error(request, 'Please log in first')
        return redirect('/operation/login/')

    # Verify if it is an admin
    operator = Operator.objects.filter(id=operator_info['employee_id'], is_operator=True).first()
    if not operator:
        messages.error(request, 'Insufficient permissions')
        return redirect('/operation/login/')

    # Get order information
    order = get_object_or_404(Order, id=order_id)
    
    return render(request, 'orders/admin_order_detail.html', {
        'order': order,
        'operator': operator
    })