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
from main_system.views.customer import customer_register, customer_verify, customer_wallet
from main_system.views import department, employee, vehicle, login, home_page, manager, customer, maps
from main_system.views.customer import customer_register

urlpatterns = [
    path('', home_page.homepage, name='home'),  # 首页
    path('home/', home_page.homepage, name='home'),
    path('subscribe/', home_page.subscribe, name='subscribe'),  # 订阅

# products system
    path('products/product/list/', product.product_list),
    path('products/product/list/add/', product.product_add),
    path('products/product/list/<int:nid>/delete/', product.product_delete),
    path('products/product/list/<int:nid>/edit/', product.product_edit),
    path('products/product/page/', product.product_page),
    path('products/product/<int:nid>/', product.product_detail),



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
