from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from main_system import models
from main_system.utils.boostrapModelForm import Vehicle_ModelForm
from main_system.utils.pagination import PageNumberPagination
from django.utils import timezone
from main_system.utils.map_function import get_address_from_latlng
from math import radians, sin, cos, sqrt, atan2


def vehicle_list(request):
    if request.method == 'POST' and 'refresh' in request.POST:
        # Update vehicle data with reasonable defaults
        vehicles = models.Vehicle.objects.all()
        for vehicle in vehicles:
            vehicle.power = max(vehicle.power, 50)  # Set a reasonable power level
            vehicle.is_available = True if vehicle.power > 20 else False
            vehicle.needs_charging = True if vehicle.power < 20 else False
            vehicle.needs_repair = False if vehicle.situation not in ['very_poor', 'poor'] else True
            vehicle.rental_time = timezone.now() if not vehicle.is_available else None

            # Only fetch address if latitude and longitude are provided
            if vehicle.latitude and vehicle.longitude:
                vehicle.location = get_address_from_latlng(vehicle.latitude, vehicle.longitude)
            else:
                vehicle.location = "Location not available"  # Default if no lat/long
            vehicle.save()

        return redirect('/operation/vehicle/list/')  # Refresh the page after update

    data = models.Vehicle.objects.all()
    # 从请求中获取 page_size，默认为 20
    page_size = request.GET.get('page_size', 20)
    if isinstance(page_size, str) and page_size.isdecimal():  # 确保 page 是字符串
        page_size = int(page_size)
    else:
        page_size = 20  # 设置默认值为 20
    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {
        'page_obj': page_obj.queryset,
        'page_string': page_obj.html()
    }
    print(page_obj.queryset[0].latitude)
    return render(request, 'vehicles/vehicle_list.html', context)


def vehicle_add(request):
    if request.method == 'GET':
        form = Vehicle_ModelForm()
        return render(request, 'main/change.html', {"form": form})
    form = Vehicle_ModelForm(request.POST)
    if form.is_valid():
        form.save()
        print('成功传输')
        return redirect('/operation/vehicle/list/')
    else:
        print(form.errors)
        return render(request, 'main/change.html', {"form": form})


def vehicle_edit(request, nid):
    row = models.Vehicle.objects.filter(id=nid).first()  # 获取需要编辑的员工对象

    if request.method == 'GET':
        # 当 GET 请求时，使用 instance 参数加载现有数据
        form = Vehicle_ModelForm(instance=row)
        return render(request, 'main/change.html', {"form": form})

    # 如果是 POST 请求，则验证和保存提交的数据
    form = Vehicle_ModelForm(request.POST, instance=row)
    if form.is_valid():
        form.save()
        return redirect('/operation/vehicle/list/')

    return render(request, 'main/change.html', {"form": form})

def vehicle_delete(request, nid):
    models.Vehicle.objects.filter(id=nid).delete()
    return redirect('/operation/vehicle/list/')


def vehicle_repair(request):
    # 过滤需要维修的车辆：is_available 为 False 或 situation 为 'poor' 或 'very poor'
    data = models.Vehicle.objects.filter(
        is_available=False,
        # needs_repair=True,
        situation__in=['very_poor', 'Very Poor','poor','Poor']
    )

    page_size = request.GET.get('page_size', 20)
    if isinstance(page_size, str) and page_size.isdecimal():  # 确保 page 是字符串
        page_size = int(page_size)
    else:
        page_size = 20  # 设置默认值为 5


    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {'page_obj': page_obj.queryset,
               'page_string': page_obj.html(),
               }

    if not data.exists():
        context['no_vehicles'] = True  # 如果没有车辆需要维修，添加此标志
    else:
        context['no_vehicles'] = False

    # 渲染模板并返回
    return render(request, 'vehicles/repair_vehicles.html', context)


def vehicle_repair_perform(request):
    if request.method == 'POST':
        vehicle_ids = request.POST.get('vehicle_ids')
        if vehicle_ids:
            vehicle_ids = [int(id) for id in vehicle_ids.split(',')]

            # 获取支持维修的地点
            repair_locations = models.Location.objects.filter(supports_repair=True)

            for vehicle_id in vehicle_ids:
                # 获取需要维修的车辆
                vehicle = models.Vehicle.objects.get(id=vehicle_id)

                # 初始化最短距离为一个很大的数值
                nearest_location = None
                min_distance = float('inf')

                # 遍历支持维修的地点，找到距离最近的
                for location in repair_locations:
                    distance = calculate_distance(vehicle.latitude, vehicle.longitude, location.latitude,
                                                  location.longitude)
                    if distance < min_distance:
                        min_distance = distance
                        nearest_location = location

                # 如果找到了最近的维修地点，将车辆坐标更新到该地点
                if nearest_location:
                    vehicle.latitude = nearest_location.latitude
                    vehicle.longitude = nearest_location.longitude
                    if vehicle.power >= 20:
                        vehicle.is_available = True
                        vehicle.needs_charging = False
                    else:
                        vehicle.is_available = False
                        vehicle.needs_charging = True
                    vehicle.is_available = True
                    vehicle.situation = 'excellent'
                    vehicle.location = nearest_location.name
                    vehicle.save()

            remaining_vehicles = models.Vehicle.objects.filter(is_available=False, needs_repair=True)
            if not remaining_vehicles.exists():
                # 如果没有剩余需要维修的车辆，返回一个标志用于前端跳转
                return JsonResponse({'all_repaired': True})

            return JsonResponse({'all_repaired': False})

    return redirect('/operation/vehicle/list/repair/')

# 计算两个坐标之间的距离（Haversine公式）
def calculate_distance(lat1, lon1, lat2, lon2):
    # 将经纬度从度数转换为弧度
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine公式
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = 6371 * c  # 地球半径为6371公里

    return distance


def vehicle_recharge(request):
    # 过滤需要充电的车辆：is_available 为 False 且 needs_charging 为 True
    data = models.Vehicle.objects.filter(
        is_available=False,
        # needs_charging=True,
        power__lte=20,
    )

    # 从请求中获取 page_size，默认为 10
    page_size = request.GET.get('page_size', 20)
    if isinstance(page_size, str) and page_size.isdecimal():  # 确保 page 是字符串
        page_size = int(page_size)
    else:
        page_size = 20  # 设置默认值为 5

    # 分页逻辑
    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {'page_obj': page_obj.queryset,
               'page_string': page_obj.html(),
               }

    # 渲染模板并返回
    return render(request, 'vehicles/recharge_vehicles.html', context)

def vehicle_recharge_perform(request):
    if request.method == 'POST':
        vehicle_ids = request.POST.get('vehicle_ids')
        if vehicle_ids:
            vehicle_ids = [int(id) for id in vehicle_ids.split(',')]

            # 获取支持充电的地点
            recharge_locations = models.Location.objects.filter(supports_charging=True)

            for vehicle_id in vehicle_ids:
                # 获取需要充电的车辆
                vehicle = models.Vehicle.objects.get(id=vehicle_id)

                # 初始化最短距离为一个很大的数值
                nearest_location = None
                min_distance = float('inf')

                # 遍历支持充电的地点，找到距离最近的
                for location in recharge_locations:
                    distance = calculate_distance(vehicle.latitude, vehicle.longitude, location.latitude, location.longitude)
                    if distance < min_distance:
                        min_distance = distance
                        nearest_location = location

                # 如果找到了最近的充电地点，将车辆坐标更新到该地点
                if nearest_location:
                    vehicle.latitude = nearest_location.latitude
                    vehicle.longitude = nearest_location.longitude

                    vehicle.power = 100  # 充电后电量设为 100%
                    if vehicle.situation in {'Excellent', 'excellent','Good', 'good','Average','average'}:
                        vehicle.is_available = True
                        vehicle.needs_repair = False
                    else:
                        vehicle.is_available = False
                        vehicle.needs_repair = True
                    vehicle.needs_charging = False  # 标记为不再需要充电
                    vehicle.location = nearest_location.name
                    # print(vehicle.latitude, vehicle.longitude, vehicle.is_available, vehicle.power)
                    vehicle.save()

            return redirect('/operation/vehicle/list/recharge/')
    return redirect('/operation/vehicle/list/recharge/')


def vehicle_move(request):
    # 过滤可移动的车辆：needs_charging=False，needs_repair=False，is_available=True
    data = models.Vehicle.objects.filter(
        is_available=True,
        needs_charging=False,
        needs_repair=False,
    )

    # 获取分页大小，默认为20
    page_size = request.GET.get('page_size', 20)
    if isinstance(page_size, str) and page_size.isdecimal():
        page_size = int(page_size)
    else:
        page_size = 20

    # 分页逻辑
    page_obj = PageNumberPagination(request, data, page_size=page_size)
    context = {
        'page_obj': page_obj.queryset,
        'page_string': page_obj.html(),
    }

    # 获取所有地点，用于下拉框选择
    locations = models.Location.objects.all()
    context['locations'] = locations

    # 渲染模板并返回
    return render(request, 'vehicles/move_vehicles.html', context)

def vehicle_move_perform(request):
    if request.method == 'POST':
        vehicle_ids = request.POST.get('vehicle_ids')
        target_location_id = request.POST.get('location_id')
        custom_latitude = request.POST.get('custom_latitude')
        custom_longitude = request.POST.get('custom_longitude')

        if vehicle_ids:
            vehicle_ids = [int(id) for id in vehicle_ids.split(',')]

            # 如果选择了已有的地点
            if target_location_id and target_location_id != 'custom':
                location = models.Location.objects.get(id=target_location_id)
                target_latitude = location.latitude
                target_longitude = location.longitude
                location_name = location.name
            # 如果输入了自定义的经纬度
            elif custom_latitude and custom_longitude:
                try:
                    target_latitude = float(custom_latitude)
                    target_longitude = float(custom_longitude)
                    location_name = get_address_from_latlng(target_latitude, target_longitude)
                except ValueError:
                    # 如果经纬度格式不正确，返回错误信息
                    return HttpResponse("Invalid latitude or longitude format.")
            else:
                # 如果没有选择地点也没有输入经纬度，返回错误信息
                return HttpResponse("Please select a location or input custom coordinates.")

            # 更新选中车辆的位置
            for vehicle_id in vehicle_ids:
                vehicle = models.Vehicle.objects.get(id=vehicle_id)
                vehicle.latitude = target_latitude
                vehicle.longitude = target_longitude
                vehicle.location = location_name
                vehicle.save()

            return redirect('/operation/vehicle/list/move/')
    return redirect('/operation/vehicle/list/move/')