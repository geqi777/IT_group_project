from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
from django.db.utils import IntegrityError

from main_system import models
from main_system.models import User, Wallet, PaymentCard, WalletTransaction

def wallet_view(request):
    """Wallet details page, showing balance, points, and payment card list"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    # Get or create wallet
    wallet, created = Wallet.objects.get_or_create(
        user=user,
        defaults={
            'balance': Decimal('0'),
            'points': 0
        }
    )

    # Get payment card list
    payment_cards = PaymentCard.objects.filter(user=user)

    # Get recent transactions
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-timestamp')[:5]

    return render(request, 'wallet/wallet_view.html', {
        'wallet': wallet,
        'payment_cards': payment_cards,
        'transactions': transactions
    })

def payment_card_list(request):
    """Payment card list page"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    # Get payment card list
    payment_cards = PaymentCard.objects.filter(user=user)

    return render(request, 'wallet/payment_card.html', {
        'payment_cards': payment_cards
    })

def payment_card_add(request):
    """Add new payment card"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    if request.method == 'POST':
        try:
            # Get form data
            card_number = request.POST.get('card_number').replace(' ', '')  # Remove spaces
            
            # Check if card number already exists
            if PaymentCard.objects.filter(card_number=card_number).exists():
                messages.error(request, 'This card number is already in use')
                return redirect('/customer/wallet/cards/add/')
                
            # Create new payment card
            card = PaymentCard.objects.create(
                user=user,
                nickname=request.POST.get('nickname') or 'Unnamed Card',
                card_number=card_number,
                expiry_date=request.POST.get('expiry_date'),
                cvv=request.POST.get('cvv'),
                country=request.POST.get('country'),
                postcode=request.POST.get('postcode').upper()
            )
            messages.success(request, 'Payment card added successfully')
            return redirect('/customer/wallet/cards/')
            
        except IntegrityError:
            messages.error(request, 'This card number is already in use')
            return redirect('/customer/wallet/cards/add/')
        except Exception as e:
            messages.error(request, f'Failed to add: {str(e)}')
            return redirect('/customer/wallet/cards/add/')

    return render(request, 'wallet/card_add.html')

def payment_card_edit(request, card_id):
    """Edit payment card"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    try:
        # Get payment card, use get() instead of filter()
        card = PaymentCard.objects.get(id=card_id, user=user)

        if request.method == 'POST':
            try:
                # Update payment card information
                card.nickname = request.POST.get('nickname')
                card.expiry_date = request.POST.get('expiry_date')
                card.country = request.POST.get('country')
                card.postcode = request.POST.get('postcode')
                card.save()

                messages.success(request, 'Payment card updated successfully')
                return redirect('/customer/wallet/cards/')
            except Exception as e:
                messages.error(request, f'Failed to update: {str(e)}')

        return render(request, 'wallet/card_edit.html', {'card': card})
        
    except PaymentCard.DoesNotExist:
        messages.error(request, 'Payment card does not exist or has been deleted')
        return redirect('/customer/wallet/cards/')

def payment_card_delete(request, card_id):
    """Delete payment card"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    # Get and delete payment card
    try:
        card = PaymentCard.objects.get(id=card_id, user=user)
        card.delete()  # Directly delete the record
        messages.success(request, 'Payment card deleted successfully')
    except PaymentCard.DoesNotExist:
        messages.error(request, 'Payment card does not exist')
    
    return redirect('/customer/wallet/cards/')

def wallet_top_up(request):
    """Wallet top-up"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    # Get wallet
    wallet = get_object_or_404(Wallet, user=user)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            payment_card_id = request.POST.get('payment_card_id')

            if amount <= 0:
                messages.error(request, 'Top-up amount must be greater than 0')
                return redirect('/customer/wallet/top-up/')

            # Validate payment card
            card = get_object_or_404(PaymentCard, id=payment_card_id, user=user)

            with transaction.atomic():
                # Update wallet balance
                wallet.balance += amount
                wallet.save()

                # Record transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='top up',
                    amount=amount,
                    payment_card=card,
                    details=f'Top-up via card {card.card_number[-4:]}'
                )

                messages.success(request, f'Successfully topped up £{amount}')
                return redirect('/customer/wallet/')

        except Exception as e:
            messages.error(request, f'Failed to top up: {str(e)}')

    # Get user's payment card list
    payment_cards = PaymentCard.objects.filter(user=user)
    return render(request, 'wallet/top_up.html', {
        'wallet': wallet,
        'payment_cards': payment_cards
    })

def transaction_history(request):
    """Transaction history"""
    # Check if user is logged in
    user_info = request.session.get('user_info')
    if not user_info:
        messages.error(request, 'Please log in first')
        return redirect('/customer/login/')

    user = User.objects.filter(id=user_info['id']).first()
    if not user:
        messages.error(request, 'User does not exist')
        return redirect('/customer/register/')

    # Get wallet
    wallet = get_object_or_404(Wallet, user=user)

    # Get all transaction records
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-timestamp')

    # Pagination
    paginator = Paginator(transactions, 10)
    page = request.GET.get('page')
    transactions = paginator.get_page(page)

    return render(request, 'wallet/transactions.html', {
        'wallet': wallet,
        'transactions': transactions
    })
