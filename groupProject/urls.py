"""
URL configuration for groupProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views. home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
    test
"""
from django.conf import settings
from django.conf.urls.static import static
# Correct URL configuration
from django.urls import path
from django.shortcuts import redirect
from main_system.views import product
from main_system.views import admin_login, user_login
from main_system.views import home_page
from main_system.views import operator, user, product, cart, order, promo_code, wallet
from main_system.views.order import order_detail
from main_system.views import admin_dashboard, admin_login, user, product, operator

urlpatterns = [
    path('', home_page.homepage, name='home'),  # Homepage
    path('home/', home_page.homepage, name='home'),
    path('subscribe/', home_page.subscribe, name='subscribe'),  # Subscribe
    path('search/', home_page.search, name='search'),
    path('about/', home_page.about_us, name='about'),   # About Us
    path('contact/', home_page.contact, name='contact'),  # Contact Us
    path('story/1/', home_page.story1, name='story1'),
    path('story/2/', home_page.story2, name='story2'),
    path('story/3/', home_page.story3, name='story3'),

    # admin
    # Admin homepage (includes user, product, and admin management)
    path('operation/homepage/', admin_dashboard.admin_dashboard, name="admin_dashboard"),
    path('operation/profile/', admin_login.admin_profile, name='admin_profile'),
    path('operation/logout/', admin_login.admin_logout, name='admin_logout'),
    # User management
    path('operation/homepage/users/', user.user_list, name="admin_user_list"),
    path('operation/homepage/users/add/', user.user_add, name="user_add"),
    path('operation/homepage/users/edit/<int:nid>/', user.user_edit, name="user_edit"),
    path('operation/homepage/users/delete/<int:nid>/', user.user_delete, name="user_delete"),
    path('operation/login/', admin_login.admin_login, name='admin_login'),

    # Product management
    path('operation/homepage/products/', product.product_list, name="admin_product_list"),
    path('operation/homepage/products/add/', product.product_add, name="product_add"),
    path('operation/homepage/products/edit/<int:product_id>/', product.product_edit, name="product_edit"),
    path('operation/homepage/products/delete/<int:product_id>/', product.product_delete, name="product_delete"),

    # Admin management
    path('operation/homepage/admins/', operator.operator_list, name="admin_operator_list"),
    path('operation/homepage/admins/add/', operator.operator_add, name="operator_add"),
    path('operation/homepage/admins/edit/<int:nid>/', operator.operator_edit, name="operator_edit"),
    path('operation/homepage/admins/delete/<int:nid>/', operator.operator_delete, name="operator_delete"),

    # Promo code management
    path('operation/homepage/promo-codes/', promo_code.promo_code_list, name='promo_code_list'),
    path('operation/homepage/promo_codes/', lambda request: redirect('/operation/homepage/promo-codes/')),
    path('operation/homepage/promo_codes/list/', lambda request: redirect('/operation/homepage/promo-codes/')),
    path('operation/homepage/promo_codes/list/add/', promo_code.promo_code_add, name='promo_code_add'),
    path('operation/homepage/promo_codes/list/<int:code_id>/edit/', promo_code.promo_code_edit, name='promo_code_edit'),
    path('operation/homepage/promo_codes/list/<int:code_id>/delete/', promo_code.promo_code_delete, name='promo_code_delete'),

    # Order management
    path('operation/homepage/orders/', order.admin_order_list, name="admin_order_list"),
    path('operation/homepage/orders/update/<int:order_id>/', order.update_order_status, name="update_order_status"),
    path('operation/homepage/orders/return/<int:order_id>/<int:item_id>/', order.process_return, name="process_return"),
    path('operation/homepage/orders/detail/<int:order_id>/', order.admin_order_detail, name="admin_order_detail"),

    # Review management
    path('operation/homepage/reviews/', admin_dashboard.admin_review_list, name="admin_review_list"),
    path('operation/homepage/reviews/delete/<int:review_id>/', admin_dashboard.admin_review_delete, name="admin_review_delete"),

    # User
    path('customer/login/', user_login.user_login, name='customer_login'),
    path('customer/register/', user_login.user_register, name='customer_register'),
    path('customer/profile/', user_login.user_profile, name='customer_profile'),
    path('customer/logout/', user_login.user_logout, name='customer_logout'),

    path('products/product/collection/', product.product_page, name='product_page'),
    path('products/product/<int:product_id>/detail/', product.product_detail, name='product_detail'),
    # /products/product/25/detail/

    # Cart
    path("customer/cart/", cart.cart_view),
    path("customer/cart/<int:product_id>/add/", cart.cart_add, name="cart_add"),
    path("customer/cart/<int:cart_item_id>/edit/", cart.cart_edit),
    path("customer/cart/<int:cart_item_id>/delete/", cart.cart_delete),
    path("customer/cart/checkout/", cart.checkout, name="checkout"),

    # Order
    path('customer/order/', order.order_list, name='order_list'),
    path('customer/order/<int:order_id>/detail/', order.order_detail, name='order_detail'),
    path('customer/order/<int:order_id>/shipping/', order.shipping),  # New: Shipping information page
    path('customer/order/<int:order_id>/payment/', order.payment),  # New: Payment page
    path('customer/order/history/', order.history_list),
    path('customer/order/<int:order_id>/cancel/', order.order_cancel),
    path('customer/order/<int:order_id>/confirm-receipt/', order.order_confirm_receipt),
    path('customer/order/<int:order_id>/review/', order.order_review),
    path('customer/order/<int:order_id>/return/', order.order_return),
    path('customer/order/<int:order_id>/delete/', order.order_delete),

    # API
    path('api/apply-promo-code/', promo_code.apply_promo_code),

    # Wallet
    path('customer/wallet/', wallet.wallet_view, name='wallet_view'),
    path('customer/wallet/cards/', wallet.payment_card_list, name='payment_card_list'),
    path('customer/wallet/cards/add/', wallet.payment_card_add, name='payment_card_add'),
    path('customer/wallet/cards/<int:card_id>/edit/', wallet.payment_card_edit, name='payment_card_edit'),
    path('customer/wallet/cards/<int:card_id>/delete/', wallet.payment_card_delete, name='payment_card_delete'),
    path('customer/wallet/wallet-top-up/', wallet.wallet_top_up, name='wallet_top_up'),
    path('customer/wallet/transactions/', wallet.transaction_history, name='transaction_history'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
