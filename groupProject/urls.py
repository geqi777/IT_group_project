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
# 正确的 URL 配置
from django.urls import path
from main_system.views import product
from main_system.views import admin_login, user_login
from main_system.views.customer import customer_register, customer_verify, customer_wallet
from main_system.views import department, employee, vehicle, login, home_page, manager, customer, maps
from main_system.views.customer import customer_register
from main_system.views import operator, user, product, cart, order
from main_system.views.order import order_detail

urlpatterns = [
    path('', home_page.homepage, name='home'),  # 首页
    path('home/', home_page.homepage, name='home'),
    path('subscribe/', home_page.subscribe, name='subscribe'),  # 订阅
    path('search/', product.search_products),    # 商品搜索

    #admin
    # 后台管理首页（包含用户、商品、管理员的管理）
    path('operation/homepage/', operator.operator_list),

    # 用户管理
    path('operation/homepage/users/', user.user_list, name="admin_user_list"),
    path('operation/homepage/users/add/', user.user_add, name="user_add"),
    path('operation/homepage/users/edit/<int:nid>/', user.user_edit, name="user_edit"),
    path('operation/homepage/users/delete/<int:nid>/', user.user_delete, name="user_delete"),
    path('operation/login/', admin_login.admin_login, name='admin_login'),

    # 商品管理
    path('operation/homepage/products/', product.product_list, name="admin_product_list"),
    path('operation/homepage/products/add/', product.product_add, name="product_add"),
    path('operation/homepage/products/edit/<int:product_id>/', product.product_edit, name="product_edit"),
    path('operation/homepage/products/delete/<int:product_id>/', product.product_delete, name="product_delete"),

    # 管理员管理
    path('operation/homepage/admins/', operator.operator_list, name="admin_operator_list"),
    path('operation/homepage/admins/add/', operator.operator_add, name="operator_add"),
    path('operation/homepage/admins/edit/<int:nid>/', operator.operator_edit, name="operator_edit"),
    path('operation/homepage/admins/delete/<int:nid>/', operator.operator_delete, name="operator_delete"),

    # User
    path('customer/login/', user_login.user_login, name='customer_login'),
    path('customer/register/', user_login.user_register, name='customer_register'),
    path('customer/profile/', user_login.user_profile, name='customer_profile'),
    # operator system
    path('operator/product/list/', product.product_list),
    path('operator/product/list/add/', product.product_add),
    path('operator/product/list/<int:product_id>/delete/', product.product_delete),
    path('operator/product/list/<int:product_id>/edit/', product.product_edit),

    path('products/product/collection/', product.product_page),
    path('products/product/<int:product_id>/detail/', product.product_detail),
    # /products/product/25/detail/

    # Cart
    path("customer/cart/", cart.cart_view),
    path("customer/cart/<int:product_id>/add/", cart.cart_add),
    path("customer/cart/<int:cart_item_id>/edit/", cart.cart_edit),
    path("customer/cart/<int:cart_item_id>/delete/", cart.cart_delete),
    path("customer/checkout/", cart.checkout),

    # Order
    path('customer/order/', order.order_list),
    path('customer/order/<int:order_id>/', order.order_detail),
    path('customer/order/history/', order.history_list),
    path('operator/orders/', order.admin_order_list),
    path('operator/orders/<int:order_id>/update-status/', order.update_order_status),


    # Employee_login
    path('operation/employee/login/', login.employee_login),
    # Employee_logout
    path('logout/', login.logout),


    # department system
    path('operation/department/list/', department.department_list),
    path('operation/department/list/add/', department.department_add),
    path('operation/department/list/<int:nid>/delete/', department.department_delete),
    path('operation/department/list/<int:nid>/edit/', department.department_edit),

    # employee system
    path('operation/employee/list/', employee.employee_list),
    path('operation/employee/list/add/', employee.employee_add),
    path('operation/employee/list/<int:nid>/edit/', employee.employee_edit),
    path('operation/employee/list/<int:nid>/delete/', employee.employee_delete),
    path('operation/resetpassword/<int:nid>/', employee.reset_password),
    path('operation/employee/profile/', employee.employee_profile),

    # vehicle system
    path('operation/vehicle/list/', vehicle.vehicle_list),
    path('operation/vehicle/list/add/', vehicle.vehicle_add),
    path('operation/vehicle/list/<int:nid>/edit/', vehicle.vehicle_edit),
    path('operation/vehicle/list/<int:nid>/delete/', vehicle.vehicle_delete),
    path('operation/vehicle/list/repair/', vehicle.vehicle_repair, name='vehicle_repair'),
    path('operation/vehicle/list/repair/perform/', vehicle.vehicle_repair_perform, name='vehicle_repair_perform'),
    path('operation/vehicle/list/recharge/', vehicle.vehicle_recharge, name='vehicle_recharge'),
    path('operation/vehicle/list/recharge/perform/', vehicle.vehicle_recharge_perform, name='vehicle_recharge_perform'),
    path('operation/vehicle/list/move/', vehicle.vehicle_move, name='vehicle_move'),
    path('operation/vehicle/list/move/perform/', vehicle.vehicle_move_perform, name='vehicle_move_perform'),

    # manager page
    path('operation/manager/page/', manager.manager),

    # path('vehicle/available/', maps.get_available_vehicles),

    # customer
    path('customer/home/', customer.home_page, name='customer_homepage'),
    path('customer/login/', login.customer_login),
    path('customer/register/', customer.customer_register),
    # path('customer/customer_vertified/', customer.customer_verified),

    path('customer/help/', customer.customer_help),
    path('customer/profile/', customer.customer_profile, name='customer_profile'),
    path('customer/verify/', customer.customer_verify, name='customer_verify'),

    path('customer/rent/', customer.rent_homepage),
    path('customer/rent/rent_ing/<int:vehicle_id>/', customer.rent_ing, name='rent_ing'),
    path('customer/order_page/', customer.customer_order_page),
    path('customer/order_history/', customer.order_history),
    path('customer/wallet/history/', customer.wallet_history),

    path('customer/rent/rent_ing/<int:history_id>/<int:vehicle_id>/return_vehicle', customer.return_vehicle,
         name='return_vehicle'),
    path('customer/rent/rent_ing/<int:history_id>/<int:vehicle_id>/report_vehicle', customer.report_vehicle,
         name='report_vehicle'),
    # path('customer/rent/rent_ing/<int:vehicle_id>/return_vehicle', customer.return_vehicle, name='return_vehicle'),
    #path('customer/redirect_to_order/', customer.redirect_to_order, name='redirect_to_order'),
    # 其他路径...
    path('customer/wallet/', customer.customer_wallet),
    path('customer/wallet/top_up/', customer.top_up_wallet),
    path('customer/wallet/coupon/', customer.apply_coupon),
    path('customer/wallet/card', customer.cards_list),
    path('customer/wallet/card_add/', customer.cards_add),
    path('customer/wallet/card/<int:card_id>/edit/', customer.cards_edit),
    path('customer/wallet/card/<int:card_id>/delete/', customer.cards_delete),
    path('customer/wallet/exchange_points/', customer.exchange_points),
    path('customer/wallet/del_expired_coupons/', customer.del_expired_coupons),

    # path('customer/list/', customer.customer_list),
    # path('customer/list/add/', customer.customer_add),
    path('customer/list/<int:nid>/edit/', customer.customer_edit),
    # path('customer/list/<int:nid>/delete/', customer.customer_delete),
    path('customer/list/<int:nid>/customer_reset_password/', customer.customer_reset_password),

    path('operation/customer/list/', employee.o_customer_list),
    # path('operation/customer/list/add/', customer.customer_add),
    path('operation/customer/list/<int:nid>/edit/', employee.o_customer_edit),
    path('operation/customer/list/<int:nid>/delete/', employee.o_customer_delete),
    path('operation/customer/list/<int:nid>/resetpassword/', employee.o_customer_reset_password),
    path('operation/customer/list/<int:nid>/verified/', employee.o_customer_verified),

    path('operation/coupon/list/', employee.coupons_list),
    path('operation/coupon/list/add/', employee.coupon_add),
    path('operation/coupon/list/<int:coupon_id>/edit/', employee.coupon_edit),
    path('operation/coupon/list/<int:coupon_id>/delete/', employee.coupon_delete),

    path('map/', maps.get_user_location)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
