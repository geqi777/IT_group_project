import datetime
import random
import string
import re
import requests
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.shortcuts import HttpResponse, get_object_or_404
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime, timedelta
from groupProject import settings
from main_system import models
from main_system.models import Customer, Vehicle, Coupon, WalletHistory
from main_system.utils.boostrapModelForm import (Customer_ModelForm, Customer_Edit2Form, ResetPasswordForm, \
                                                 Customer_RegisterForm, HistoryModelForm)
from main_system.utils.map_function import get_address_from_latlng, \
    get_bicycle_route_duration_and_distance, get_random_location_in_glasgow, get_walking_route_duration_and_distance
from main_system.utils.pagination import PageNumberPagination
import math


def customer_help(request):
    return render(request, 'customer_help.html')
def convert_time_to_hours(time_string):
    # 解析小时和分钟的情况
    hours_match = re.search(r'(\d+)\s*hours?', time_string)
    mins_match = re.search(r'(\d+)\s*mins?', time_string)

    # 获取小时和分钟数
    hours = int(hours_match.group(1)) if hours_match else 0
    mins = int(mins_match.group(1)) if mins_match else 0

    # 计算总小时数
    total_hours = hours + mins / 60
    return round(total_hours, 2)  # 保留两位小数

def add_duration_to_start_time(start_time, duration):
    """
    解析duration（如"2 hours 8 mins"或"8 mins"）并将其加到start_time。
    返回datetime对象的end_time。
    """
    # 使用正则表达式解析小时和分钟
    hours = int(re.search(r'(\d+)\s*hours?', duration).group(1)) if 'hour' in duration else 0
    mins = int(re.search(r'(\d+)\s*mins?', duration).group(1)) if 'min' in duration else 0

    # 创建 timedelta 对象并加到 start_time 上
    duration_delta = timedelta(hours=hours, minutes=mins)
    end_time = start_time + duration_delta

    # 直接返回 datetime 对象
    return end_time

def parse_duration_to_timedelta(duration_str):
    hours_match = re.search(r'(\d+)\s*hours?', duration_str)
    mins_match = re.search(r'(\d+)\s*mins?', duration_str)

    hours = int(hours_match.group(1)) if hours_match else 0
    mins = int(mins_match.group(1)) if mins_match else 0

    return timedelta(hours=hours, minutes=mins)


def haversine(lat1, lon1, lat2, lon2):
    """计算两个经纬度之间的距离，返回值为公里"""
    R = 6371  # 地球半径，单位为公里
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def rent_homepage(request):
    customer_info = request.session.get('customer_info')
    customer_user_address = request.session.get('user_address')
    customer_longitude = request.session.get('longitude')
    customer_latitude = request.session.get('latitude')
    customer_chose_type = request.session.get('vehicle_type')
    # print(customer_info, customer_user_address, customer_longitude, customer_latitude)

    customer_detail = models.Customer.objects.get(pk=customer_info['customer_id'])

    if customer_detail.is_verified:
        if customer_chose_type == ['Scooter', 'E-bike']:
            data_list = models.Vehicle.objects.filter(is_available=True)
        # 否则，根据用户选择的具体类型筛选
        else:
            data_list = models.Vehicle.objects.filter(is_available=True, vehicle_type=customer_chose_type)
        # 第一步：计算每辆车的初步距离 v_distance，并存入列表
        vehicles_info = []
        for vehicle in data_list:
            v_distance = haversine(float(customer_latitude), float(customer_longitude),
                                   float(vehicle.latitude), float(vehicle.longitude))
            vehicles_info.append({
                'id': vehicle.id,
                'name': vehicle.name,
                'price': vehicle.price,
                'vehicle_type': vehicle.vehicle_type,
                'distance': v_distance,
                'latitude': vehicle.latitude,
                'longitude': vehicle.longitude,
                'location': vehicle.location,
                'power': vehicle.power,
                'situation': vehicle.situation,
            })

        closest_vehicles = sorted(vehicles_info, key=lambda x: x['distance'])[:30]

        for vehicle in closest_vehicles:
            duration, detailed_distance = get_walking_route_duration_and_distance(
                float(customer_latitude),
                float(customer_longitude),
                float(vehicle['latitude']),
                float(vehicle['longitude'])
            )
            vehicle['duration'] = duration
            vehicle['distance'] = detailed_distance

        # 将最近的车辆信息传递给模板
        return render(request, 'customer/rent_homepage.html', {
            'vehicles': closest_vehicles,
            'customer_address': customer_user_address,
            'customer_latitude': customer_latitude,
            'customer_longitude': customer_longitude,
            'available_car_nums': len(closest_vehicles),
        })
    else:
        return redirect('customer_profile')


def rent_ing(request, vehicle_id):
    customer_info = request.session.get('customer_info')
    customer_user_address = request.session.get('user_address')
    customer_longitude = request.session.get('longitude')
    customer_latitude = request.session.get('latitude')
    customer_detail = models.Customer.objects.get(pk=customer_info['customer_id'])
    print(customer_detail.name)
    # 如果账户余额不足，跳转到钱包页面
    if customer_detail.account_balance <= 0:
        request.session['show_balance_warning'] = True
        return redirect('/customer/wallet/')

    # 获取当前车辆信息
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
    except Vehicle.DoesNotExist:
        return HttpResponse('null')

    # 判断请求是否为 POST 请求
    if request.method == 'POST':
        if request.POST.get('book') == 'true':
            # 获取用户信息和车辆信息
            user_id = customer_info['customer_id']
            customer = models.Customer.objects.get(pk=user_id)

            # 设置车辆为租用状态
            vehicle.user_id = user_id
            vehicle.rental_time = timezone.now()
            vehicle.is_available = False
            vehicle.save()  # 保存车辆状态

            # 获取开始时间和车辆的位置信息
            start_time = timezone.now()
            start_location_name = vehicle.location  # 车辆位置（假设 vehicle 对象中有 location 信息）
            start_location_latitude = vehicle.latitude
            start_location_longitude = vehicle.longitude
            request.session['user_address'] = start_location_name
            request.session['latitude'] = start_location_latitude
            request.session['longitude'] = start_location_longitude
            print(request.session, dict(request.session))
            # 创建订单并写入 History 表
            history = models.History.objects.create(
                user=customer,
                vehicle=vehicle,
                start_time=start_time,
                start_location_name=start_location_name,
                start_location_latitude=start_location_latitude,
                start_location_longitude=start_location_longitude,
                cost=0  # 初始费用设置为 0
            )

            # 返回成功消息
            return JsonResponse({'message': 'rental started'})

    # 渲染页面
    return render(request, 'customer/rent_ing.html', {
        'vehicle': vehicle,
        'customer_user_address': customer_user_address,
        'customer_longitude': customer_longitude,
        'customer_latitude': customer_latitude,
        'vehicle_location': vehicle.location,
        'vehicle_latitude': vehicle.latitude,
        'vehicle_longitude': vehicle.longitude,
        'customer_name': customer_detail.name,
    })


def customer_order_page(request):
    customer_info = request.session.get('customer_info')
    customer_detail = models.Customer.objects.get(pk=customer_info['customer_id'])

    # 获取用户所有状态为 "ongoing" 的订单
    history = models.History.objects.filter(user=customer_detail, status='ongoing')

    # 为每个订单生成表单
    order_forms = []
    for order in history:
        form = HistoryModelForm(instance=order)  # 为每个订单生成一个表单
        order_forms.append({
            'form': form,
            'order': order
        })

    # 检查是否有订单
    has_orders = len(order_forms) > 0

    return render(request, 'customer/customer_ordered.html', {'order_forms': order_forms, 'has_orders': has_orders})


def return_vehicle(request, history_id, vehicle_id):
    # 获取指定的车辆、租赁历史记录和当前用户信息
    current_vehicle = models.Vehicle.objects.get(id=vehicle_id)
    history = models.History.objects.get(id=history_id, vehicle=current_vehicle)
    customer_info = request.session.get('customer_info')
    customer = models.Customer.objects.get(pk=customer_info['customer_id'])
    # 随机生成一个结束地址
    end_latitude, end_longitude = get_random_location_in_glasgow()
    end_location = get_address_from_latlng(end_latitude, end_longitude)
    duration, distance = get_bicycle_route_duration_and_distance(history.start_location_latitude, history.start_location_longitude, end_latitude, end_longitude)
    # 转换时间
    start_time = history.start_time
    end_time = add_duration_to_start_time(start_time, duration)
    transfer_time = convert_time_to_hours(duration)
    cost = round(transfer_time * current_vehicle.price, 2)

    # 电量情况
    start_power = current_vehicle.power
    end_power = int(start_power - 50*transfer_time)
    print(start_power, end_power)

    print(f'从当前位置{history.start_location_name}前往了随机生成地点{end_location},\n从{start_time}到{end_time},\n一共花费了{duration},转换成小时{transfer_time},\n行驶了{distance},\n花费{cost}')

    # 获取当前用户的激活优惠券
    activated_coupons = customer.coupons.all()
    print(activated_coupons)
    if request.method == 'POST' and request.POST.get('action') == 'pay_now':
        # 获取评分数据
        rating = int(request.POST.get('rating', 5))  # 默认评分为 5

        # 处理车辆评分
        current_vehicle.marks = rating
        current_vehicle.situation = (
            'Excellent' if rating == 5 else
            'Good' if rating == 4 else
            'Average' if rating == 3 else
            'Poor' if rating == 2 else
            'Very Poor'
        )
        current_vehicle.save()

        rental_cost = round(transfer_time * current_vehicle.price, 2)

        # 应用优惠券折扣
        coupon_applied = None
        selected_coupon_id = request.POST.get('coupon_id')
        if selected_coupon_id and selected_coupon_id != 'null':  # 检查是否有有效的优惠券ID
            try:
                # 查询优惠券对象
                coupon = models.Coupon.objects.get(id=int(selected_coupon_id))
                print(coupon)
                print(rental_cost, coupon.min_order_value)
                # 判断订单金额是否满足优惠券的最低订单金额
                if rental_cost >= coupon.min_order_value:
                    rental_cost = max(rental_cost - float(coupon.discount), 0)  # 确保费用不会为负数
                    coupon_applied = coupon  # Store the coupon used

                    # 将优惠券从用户激活列表中移除，并保存更改
                    customer.coupons.remove(coupon)
                    coupon.max_activations -= 1
                    coupon.save()
                    print('记录生成成功')
                    # Log coupon deduction in WalletHistory
                    models.WalletHistory.objects.create(
                        customer=customer,
                        transaction_type='Coupon Deduction',
                        amount=-float(coupon.discount),
                        date=end_time,
                        coupon=coupon,
                        details=f'Applied coupon {coupon.code} for a discount of {coupon.discount} pounds'
                    )
                    print('记录生成成功1')
                else:
                    print('2层')
            except models.Coupon.DoesNotExist:
                # 处理优惠券不存在的情况：记录日志或输出消息
                print(f"Coupon with ID {selected_coupon_id} does not exist or is invalid.")
        else:
            print('第一层')
        # 更新车辆情况
        current_vehicle.power = end_power
        current_vehicle.location = end_location
        current_vehicle.longitude = end_longitude
        current_vehicle.latitude = end_latitude
        current_vehicle.user = None
        current_vehicle.save()

        # 更新用户的实际地址
        request.session['user_address'] = end_location
        request.session['latitude'] = end_latitude
        request.session['longitude'] = end_longitude

        # 更新客户的账户余额
        customer.account_balance = round(customer.account_balance - rental_cost, 2)
        customer.trip_points = int(customer.trip_points + 10 * rental_cost)
        customer.save()
        # Log payment in WalletHistory
        models.WalletHistory.objects.create(
            customer=customer,
            transaction_type='Payment',
            amount=-rental_cost,
            date=end_time,
            details=f'Order payment of {rental_cost} pounds' + (f' with coupon {coupon_applied.code}' if coupon_applied else '')
        )

        # Update trip points and log in WalletHistory
        points_earned = int(10 * rental_cost)
        customer.trip_points += points_earned
        customer.save()
        # Log points increase in WalletHistory
        models.WalletHistory.objects.create(
            customer=customer,
            transaction_type='Points Increase',
            trip_points=points_earned,
            date=end_time,
            details=f'Points earned from order {history_id}'
        )

        # 更新租赁记录
        history.cost = rental_cost
        history.end_location_name = end_location
        history.end_location_latitude = end_latitude
        history.end_location_longitude = end_longitude
        history.duration = parse_duration_to_timedelta(duration)
        history.distance = distance

        history.status = 'Completed'
        print(type(end_time), end_time)
        history.end_time = end_time
        history.save()

        return JsonResponse({
            'message': 'Payment and rating submitted successfully!',
            'new_balance': customer.account_balance
        })

    rental_cost = round(transfer_time * current_vehicle.price, 2)
    points_earned = int(10 * rental_cost)

    return render(request, "customer/return_vehicle.html", {
        'history_id': history.id,
        'vehicle': current_vehicle,
        'rental_cost': rental_cost,
        'start_time': start_time,
        'end_time': end_time,
        'new_balance': customer.account_balance,
        'rental_duration': duration,
        'start_location': history.start_location_name,
        'activated_coupons': activated_coupons,  # 传递激活的优惠券到模板
        'end_location': end_location,
        'distance': distance,
        'points_earned': points_earned,
    })

def report_vehicle(request, history_id, vehicle_id):
    # 获取指定的车辆和历史记录
    current_vehicle = get_object_or_404(models.Vehicle, id=vehicle_id)
    history = get_object_or_404(models.History, id=history_id, vehicle=current_vehicle)

    if request.method == 'POST':

        # 之前的定位地址
        current_vehicle = models.Vehicle.objects.get(id=vehicle_id)
        history = models.History.objects.get(id=history_id, vehicle=current_vehicle)
        customer_info = request.session.get('customer_info')
        customer = models.Customer.objects.get(pk=customer_info['customer_id'])
        # 随机生成一个结束地址
        end_latitude, end_longitude = get_random_location_in_glasgow()
        end_location = get_address_from_latlng(end_latitude, end_longitude)
        duration, distance = get_bicycle_route_duration_and_distance(history.start_location_latitude,
                                                                     history.start_location_longitude, end_latitude,
                                                                     end_longitude)
        # 转换时间
        start_time = history.start_time
        end_time = add_duration_to_start_time(start_time, duration)
        transfer_time = convert_time_to_hours(duration)
        rental_cost = round(transfer_time * current_vehicle.price, 2)

        # 电量情况
        start_power = current_vehicle.power
        end_power = int(start_power - 50 * transfer_time)
        print(start_power, end_power)

        # 更新车辆情况
        current_vehicle.user = None
        current_vehicle.situation = 'Very Poor'
        current_vehicle.power = end_power
        current_vehicle.location = end_location
        current_vehicle.longitude = end_longitude
        current_vehicle.latitude = end_latitude
        current_vehicle.save()

        # 更新用户的实际地址
        request.session['user_address'] = end_location
        request.session['latitude'] = end_latitude
        request.session['longitude'] = end_longitude

        # 更新客户的账户余额
        customer.account_balance -= rental_cost
        customer.trip_points += 10 * rental_cost
        customer.save()

        # Log payment in WalletHistory
        models.WalletHistory.objects.create(
            customer=customer,
            transaction_type='Payment',
            amount=-rental_cost,
            date=end_time,
            details=f'Order payment of {rental_cost} pounds'
        )

        # Log points increase in WalletHistory
        models.WalletHistory.objects.create(
            customer=customer,
            transaction_type='Points Increase',
            trip_points=10 * rental_cost,
            date=end_time,
            details=f'Points earned from order {history_id}'
        )

        # 更新租赁记录
        history.cost = rental_cost
        history.end_location_name = end_location
        history.end_location_latitude = end_latitude
        history.end_location_longitude = end_longitude
        history.duration = parse_duration_to_timedelta(duration)
        history.distance = distance

        history.status = 'Completed'
        print(type(end_time), end_time)
        history.end_time = end_time
        history.save()
        # 从POST数据中获取用户的报告信息
        report_message = request.POST.get('report_message')
        if not report_message:
            return JsonResponse({'message': 'Report message cannot be empty'}, status=400)

        # 保存报告信息，假设你有一个 `Report` 模型来保存用户的报告
        report = models.VehicleReport.objects.create(
            vehicle=current_vehicle,
            history=history,
            description=report_message,
            created_at=timezone.now()
        )
        report.save()
        # 反馈成功信息给用户
        return JsonResponse({
            'message': 'Report submitted successfully! Redirecting...',
        })

    return render(request, 'customer/vehicle_report.html', {
        'vehicle': current_vehicle,
        'history_id': history_id,
    })

def order_history(request):
    customer_info = request.session.get('customer_info')
    customer_detail = models.Customer.objects.get(pk=customer_info['customer_id'])

    # 获取用户所有状态为 "completed" 的订单，并按时间排序
    history = models.History.objects.filter(user=customer_detail, status='Completed').order_by(
        '-start_time')  # 按开始时间降序排列

    # 为每个订单生成表单
    order_forms = []
    for order in history:
        form = HistoryModelForm(instance=order)  # 为每个订单生成一个表单
        order_forms.append({
            'form': form,
            'order': order
        })

    # 检查是否有订单
    has_orders = len(order_forms) > 0

    return render(request, 'customer/order_history.html', {'order_forms': order_forms, 'has_orders': has_orders})


def wallet_history(request):
    customer_info = request.session.get('customer_info')
    customer = Customer.objects.get(id=customer_info['customer_id'])

    # Fetch and sort different types of records
    balance_history = models.WalletHistory.objects.filter(customer=customer, transaction_type__in=['Top Up', 'Payment']).order_by('-date')
    points_history = models.WalletHistory.objects.filter(customer=customer, transaction_type__in=['Points Increase', 'Points Exchange']).order_by('-date')
    coupon_history = models.WalletHistory.objects.filter(customer=customer, coupon__isnull=False).order_by('-date')

    return render(request, 'customer/wallet_history.html', {
        'balance_history': balance_history,
        'points_history': points_history,
        'coupon_history': coupon_history,
    })

# 辅助函数，将时间字符串转换为秒数
def convert_to_seconds(time_str):
    """将类似 '15 mins' 这样的字符串转换为秒"""
    time_parts = time_str.split()
    time_value = int(time_parts[0])

    if 'min' in time_parts[1]:
        return time_value * 60
    elif 'hour' in time_parts[1]:
        return time_value * 3600
    else:
        raise ValueError("Unsupported time format")


def redirect_to_order(request):
    # 获取 session 中的客户信息
    customer_info = request.session.get('customer_info')
    if not customer_info:
        return redirect('login')

    customer_id = customer_info['customer_id']

    # 查询用户是否有进行中的订单
    ongoing_order = Vehicle.objects.filter(user_id=customer_id).first()

    if ongoing_order:
        # 如果有订单，重定向到租车页面并传递 from_navbar 参数
        return redirect(f'/customer/rent/rent_ing/{ongoing_order.id}?from_navbar=true')

    # 如果没有订单，重定向到提示页面或首页
    return redirect('homepage')  # 或者重定向到提示用户没有订单的页面


def home_page(request):
    # 如果会话中已有信息，则优先使用会话中的信息
    latitude = request.session.get('latitude')
    longitude = request.session.get('longitude')
    user_address = request.session.get('user_address')
    vehicle_type = request.session.get('vehicle_type', ['Scooter', 'E-bike'])  # 默认显示 "both"
    if request.method == "POST":
        # 从表单获取经纬度和地址
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        user_address = request.POST.get("pickup_location")
        type_v = request.POST.get('vehicle_type')
        if type_v == 'both':
            request.session['vehicle_type'] = ['Scooter', 'E-bike']
        elif type_v == 'Scooter':
            request.session['vehicle_type'] = 'Scooter'
        elif type_v == 'E-bike':
            request.session['vehicle_type'] = 'E-bike'
        request.session['latitude'] = latitude
        request.session['longitude'] = longitude
        request.session['user_address'] = user_address
        return redirect('/customer/rent/')
        # 处理或存储接收到的位置信息
        # print(f"Received location data: Address={user_address}, Latitude={latitude}, Longitude={longitude}")
    locations = models.Location.objects.all()  # 获取 Location 模型中的所有租车点

    # 将 locations 传递给模板
    # 将信息传递给模板，包括位置和车辆类型
    return render(request, 'customer/customer_home_page.html', {
        'locations': locations,
        'latitude': latitude,
        'longitude': longitude,
        'user_address': user_address,
        'vehicle_type': vehicle_type
    })


def customer_list(request):
    data = models.Customer.objects.all()

    # 从请求中获取 page_size，默认为 10
    page_size = request.GET.get('page_size', 5)
    if isinstance(page_size, str) and page_size.isdecimal():  # 确保 page 是字符串
        page_size = int(page_size)
    else:
        page_size = 5  # 设置默认值为 5

    # 创建分页对象并传递 page_size
    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {'page_obj': page_obj.queryset,
               'page_string': page_obj.html()}
    return render(request, 'customer/customer_list.html', context)


def customer_add(request):
    if request.method == 'GET':
        form = Customer_ModelForm()
        return render(request, 'main/customer_change.html', {'form': form})

    form = Customer_ModelForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect('/customer/list/')
    else:
        return render(request, 'main/customer_change.html', {'form': form})


def customer_edit(request, nid):
    row = models.Customer.objects.get(id=nid)  # 获取需要编辑的用户账户

    if request.method == 'GET':
        form = Customer_Edit2Form(instance=row)
        return render(request, 'main/customer_change.html', {'form': form})

    form = Customer_Edit2Form(request.POST, instance=row)
    if form.is_valid():
        form.save()
        return redirect('/customer/profile/')

    return render(request, 'main/customer_change.html', {'form': form})


def customer_delete(nid):
    models.Customer.objects.get(id=nid).delete()
    return redirect('/customer/list/')


def customer_reset_password(request, nid):
    row = models.Customer.objects.get(id=nid)  # 获取需要编辑的用户对象
    if row is None:
        return redirect('/customer/profile/')
    if request.method == 'GET':
        form = ResetPasswordForm()
        return render(request, 'main/customer_change.html', {'form': form})

    form = ResetPasswordForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        return redirect('/customer/profile/')

    return render(request, 'main/customer_change.html', {'form': form})


def customer_profile(request):
    # Retrieve customer information from the session
    customer_info = request.session.get('customer_info')

    # Fetch customer details from the database using the session info
    customer_detail = models.Customer.objects.filter(account=customer_info['customer_account']).first()
    # print(customer_detail)
    # customer = Customer.objects.get(account=request.user.username)

    # Prepare data to send to the template
    profile_info = {
        'id': customer_detail.id,
        'name': customer_detail.name,
        'email': customer_detail.email,
        'phone': customer_detail.phone,
        'date_of_birth': customer_detail.date_of_birth,
        'address': customer_detail.address,
        'is_verified': customer_detail.is_verified,
        'account': customer_detail.account,
        'account_balance': customer_detail.account_balance,
    }

    return render(request, 'customer/customer_profile.html', {'profile': profile_info})


def customer_register(request):
    if request.method == 'GET':
        form = Customer_RegisterForm()
        return render(request, 'main/customer_register.html', {'form': form})

    form = Customer_RegisterForm(request.POST)
    if form.is_valid():
        # 保存表单但不提交到数据库
        customer = form.save(commit=False)
        # 设置 is_verified 为 False
        customer.is_verified = False
        # 保存到数据库
        customer.save()
        return redirect('/customer/login/')
    else:
        return render(request, 'main/customer_register.html', {'form': form})


def customer_verify(request):
    if request.method == 'POST':
        # 打印所有接收到的文件
        print("Received files:", request.FILES)

        if request.FILES.get('license_image'):
            license_image = request.FILES['license_image']
            print("Uploaded image name:", license_image.name)

            # 将文件保存到正确的路径
            fs = FileSystemStorage(location=settings.MEDIA_ROOT + '/customer/license/')
            filename = fs.save(license_image.name, license_image)
            file_url = 'customer/license/' + filename  # 这是上传文件的 URL

            # 从会话中获取客户信息
            customer_info = request.session.get('customer_info')
            print("Customer info from session:", customer_info)

            if customer_info:
                customer = models.Customer.objects.get(account=customer_info['customer_account'])
                print("Retrieved customer:", customer)

                # 使用上传的文件 URL 更新驾照字段
                customer.driver_license = file_url  # 使用 driver_license 字段
                print("Driver license URL before saving:", customer.driver_license)  # 调试输出以验证 URL

                # 尝试保存客户对象并处理任何异常
                try:
                    customer.save()
                    messages.success(request, 'Your license image has been submitted successfully.')
                except Exception as e:
                    messages.error(request, f'Failed to save license image: {e}')
            else:
                messages.error(request, 'Customer info not found in session.')

        else:
            messages.error(request, 'Please upload a valid license image.')

        return redirect('/customer/profile/')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('/customer/profile/')


def customer_wallet(request):
    customer_info = request.session.get('customer_info')
    customer = models.Customer.objects.get(account=customer_info['customer_account'])

    balance = customer.account_balance
    points = customer.trip_points
    coupons = customer.coupons.all() # customer's coupons
    cards = customer.cards.all()  # all saved cards' information
    wallet_history = models.WalletHistory.objects.filter(customer=customer).order_by('-date')

    # Check for expired coupons and update their status
    for coupon in coupons:
        if coupon.expiry_date < timezone.now().date():
            coupon.is_active = False
            coupon.save()

    return render(request, 'customer/wallet.html', {
        'balance': balance,
        'points': points,
        'coupons': coupons,
        'cards': cards,
        'wallet_history': wallet_history,
    })


def top_up_wallet(request):
    if request.method == 'POST':
        selected_card_id = request.POST.get('selected_card')
        top_up_amount = int(request.POST.get('top_up_amount', 10))  # Default top-up is 10

        if selected_card_id == 'new_card':
            return redirect('/customer/wallet/card_add/')  # Redirect to add a new card
        elif selected_card_id.isnumeric():
            # Use existing card
            selected_card = models.Card.objects.get(id=selected_card_id)
            # 创建充值记录
            customer_id = request.session['customer_info'].get('customer_id')
            customer = get_object_or_404(Customer, id=customer_id)

            # 创建并保存 TopupHistory 记录
            top_up_record = models.TopupHistory.objects.create(
                customer=customer,
                amount=top_up_amount,
                card=selected_card  # 使用选择的卡
            )

            # 增加 WalletHistory 记录
            models.WalletHistory.objects.create(
                customer=customer,
                transaction_type='Top Up',
                amount=top_up_amount,
                date=timezone.now(),
                top_up=top_up_record,
                details=f'Top-up of {top_up_amount} using card {selected_card.nickname}'
            )

            # 添加逻辑处理支付（遵循PCI合规性）
            customer.account_balance += top_up_amount  # Apply the top_up amount
            customer.save()

            messages.success(request, 'Your wallet has been recharged successfully.')
            return redirect('/customer/wallet/')

        else:
            messages.error(request, 'Invalid card selection')
            return redirect('/customer/wallet/top_up/')

    # If GET request, render the top-up page
    customer_info = request.session.get('customer_info')
    customer = models.Customer.objects.get(id=customer_info['customer_id'])
    cards = customer.cards.all()

    return render(request, 'customer/top_up_wallet.html', {'cards': cards})


def cards_list(request):
    cards = request.customer.cards.all()
    return render(request, 'customer/cards_list.html', {'cards': cards})


def cards_add(request):
    if request.method == 'POST':
        card_number = request.POST['card_number']
        expiry_date = request.POST['expiry_date']
        cvv = request.POST['cvv']
        nickname = request.POST.get('nickname', '')

        customer_info = request.session.get('customer_info')
        customer = models.Customer.objects.get(account=customer_info['customer_account'])

        # save new card's information
        new_card = models.Card.objects.create(
            customer=customer,
            card_number=card_number,
            expiry_date=expiry_date,
            cvv=cvv,
            nickname=nickname
        )

        messages.success(request, 'New card added successfully')
        return redirect('/customer/wallet/')

    return render(request, 'customer/cards_add.html')


def cards_edit(request, card_id):
    card = models.Card.objects.get(id=card_id)

    if request.method == 'POST':
        # card_number = request.POST['card_number']
        expiry_date = request.POST['expiry_date']
        # cvv = request.POST['cvv']
        country = request.POST['country']
        postcode = request.POST['postcode']
        nickname = request.POST.get('nickname', card.nickname)

        # Update Card's Information
        card.expiry_date = expiry_date
        card.country = country
        card.postcode = postcode
        card.nickname = nickname
        card.save()

        messages.success(request, 'Card edited successfully')
        return redirect('/customer/wallet/')

    return render(request, 'customer/cards_edit.html', {'card': card})


def cards_delete(request, card_id):
    card = models.Card.objects.get(id=card_id)
    card.delete()

    messages.success(request, 'Card deleted successfully')
    return redirect('/customer/wallet/')

def apply_coupon(request):
    customer_info = request.session.get('customer_info')
    customer = models.Customer.objects.get(id=customer_info['customer_id'])
    used_coupons = models.WalletHistory.objects.filter(
        customer=customer,
        transaction_type='Coupon Addition'
    )
    unique_used_coupons =[]
    for used_coupon in used_coupons:
        if used_coupon.coupon_id not in unique_used_coupons:
            unique_used_coupons.append(used_coupon.coupon_id)
    print(unique_used_coupons)
    if request.method == 'POST':
        coupon_code = request.POST['coupon_code']

        # 验证优惠券并将其添加至用户优惠券列表中


        try:
            coupon = models.Coupon.objects.get(code=coupon_code)
            if coupon.is_valid():
                # Ensure the user hasn't activated this coupon yet
                if coupon.id not in unique_used_coupons:
                    customer.coupons.add(coupon)
                    coupon.activated_users.add(customer)
                    # Log coupon addition in WalletHistory
                    models.WalletHistory.objects.create(
                        customer=customer,
                        transaction_type='Coupon Addition',
                        date=timezone.now(),
                        coupon=coupon,
                        details=f'Add coupon {coupon.code} with discount {coupon.discount} pounds, expires on {coupon.expiry_date.strftime('%y/%m/%d - %H:%M')}'
                    )

                    messages.success(request, 'Coupon applied successfully')
                    return redirect('/customer/wallet/')
                else:
                    messages.error(request, 'You have already activated this coupon')
            else:
                messages.error(request, 'Coupon is no longer valid')
        except models.Coupon.DoesNotExist:
            messages.error(request, 'Invalid coupon code')

        return redirect('/customer/wallet/')

def del_expired_coupons(request):
    customer_info = request.session.get('customer_info')
    customer = models.Customer.objects.get(id=customer_info['customer_id'])

    coupons = customer.coupons.filter(expiry_date_gte=timezone.now())
    expired_coupons = coupons.filter(expiry_date_lt=timezone.now())

    for coupon in expired_coupons:
        # Log expired coupon in WalletHistory
        models.WalletHistory.objects.create(
            customer=customer,
            transaction_type='Coupon Expired',
            date=timezone.now(),
            coupon=coupon,
            details=f'Expired coupon {coupon.code} with discount {coupon.discount} pounds'
        )

    expired_coupons.delete()
    return render(request, 'customer/wallet.html', {'coupons': coupons})


def exchange_points(request):
    if request.method == 'POST':
        customer_info = request.session.get('customer_info')
        customer = models.Customer.objects.get(id=customer_info['customer_id'])

        points_to_deduct = int(request.POST['exchange_points'])
        coupon_value = 0
        min_order_value = 1
        if points_to_deduct == 500 and customer.trip_points >= 500:
            coupon_value = 5
            min_order_value = 10
        elif points_to_deduct == 1000 and customer.trip_points >= 1000:
            coupon_value = 12.5
            min_order_value = 15
        else:
            messages.error(request, 'Insufficient points for the selected coupon')
            return redirect('/customer/wallet/')

        # Deduct points and generate coupon
        customer.trip_points -= points_to_deduct
        customer.save()

        coupon_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        expiry_date = timezone.now() + timedelta(days=30)

        # Create and assign the coupon to the customer
        new_coupon = Coupon.objects.create(
            code=coupon_code,
            discount=coupon_value,
            expiry_date=expiry_date,
            max_activations=1,
            is_active=True,
            min_order_value = min_order_value,
            # activated_users=customer
        )
        customer.coupons.add(new_coupon)
        new_coupon.activated_users.add(customer)
        new_coupon.save()

        # Log points deduction in WalletHistory
        models.WalletHistory.objects.create(
            customer=customer,
            transaction_type='Points Exchange',
            trip_points=-points_to_deduct,
            date=timezone.now(),
            details=f'Exchanged {points_to_deduct} points for a {coupon_value} pounds coupon'
        )

        # Log coupon creation in WalletHistory
        models.WalletHistory.objects.create(
            customer=customer,
            transaction_type='Coupon Addition',
            date=timezone.now(),
            coupon=new_coupon,
            details=f'Added {coupon_value} pounds coupon with code {coupon_code}, expires on {expiry_date.strftime('%y/%m/%d - %H:%M')}'
        )
        
        messages.success(request, 'Exchanged points successfully')
        return redirect('/customer/wallet/')