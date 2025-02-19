import requests
import random

api_key = 'AIzaSyBIWSxGqGliYcvqVAG1Daba143S98dofDE'


# 从经纬度获取地址
def get_address_from_latlng(latitude, longitude):
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'latlng': f'{latitude},{longitude}', 'key': api_key}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            return data['results'][0]['formatted_address']
        else:
            return "No address found"
    else:
        return f"Error: {response.status_code}"


# 从地址获取经纬度
def get_lat_lng_from_address(address):
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'address': address, 'key': api_key}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        geocode_data = response.json()
        if 'results' in geocode_data and len(geocode_data['results']) > 0:
            location = geocode_data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    return None, None


# 获取方向数据
def get_directions(start, end, mode):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {'origin': start, 'destination': end, 'mode': mode, 'key': api_key}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            return data
        else:
            return f"Error: {data['status']}"
    else:
        return f"Error: {response.status_code}"


# 提取路线坐标
def extract_route_points(directions_data):
    if directions_data and directions_data['status'] == 'OK':
        route = directions_data['routes'][0]
        steps = route['legs'][0]['steps']
        lat_lngs = []
        for step in steps:
            lat_lngs.append((step['start_location']['lat'], step['start_location']['lng']))
            lat_lngs.append((step['end_location']['lat'], step['end_location']['lng']))
        return lat_lngs
    return []


def snap_to_road(latitude, longitude):
    """ 使用Google Roads API捕捉最近的道路 """
    snap_url = f"https://roads.googleapis.com/v1/snapToRoads?path={latitude},{longitude}&key={api_key}"
    response = requests.get(snap_url)
    if response.status_code == 200:
        snapped_points = response.json().get('snappedPoints', [])
        if snapped_points:
            snapped_location = snapped_points[0]['location']
            return snapped_location['latitude'], snapped_location['longitude']
    return latitude, longitude  # 如果API调用失败，使用原始随机点


def get_random_location_in_glasgow():
    """ 生成格拉斯哥市中心附近的随机经纬度 """
    latitude = round(random.uniform(55.83, 55.88), 4)
    longitude = round(random.uniform(-4.30, -4.20), 4)
    latitude, longitude = snap_to_road(latitude, longitude)
    return latitude, longitude


def get_bicycle_route_duration_and_distance(start_latitude, start_longitude, end_latitude, end_longitude):
    """ 获取起始点到终点的自行车路线的时长和距离 """
    directions_url = (
        f"https://maps.googleapis.com/maps/api/directions/json?origin={start_latitude},{start_longitude}"
        f"&destination={end_latitude},{end_longitude}&mode=bicycling&key={api_key}"
    )

    response = requests.get(directions_url)

    if response.status_code == 200:
        directions_data = response.json()
        if directions_data.get('routes'):
            # 获取第一个路线
            route = directions_data['routes'][0]
            leg = route['legs'][0]  # 获取第一个路线段

            # 获取路线时长和距离
            duration = leg['duration']['text']  # 人类可读的时长 (例如 "15 mins")
            distance = leg['distance']['text']  # 人类可读的距离 (例如 "3.5 km")

            return duration, distance  # 返回时长和距离
        else:
            return None, None  # 如果没有找到路线，返回 None
    else:
        print(f"Error: {response.status_code}")
        return None, None  # 如果请求失败，返回 None

def get_walking_route_duration_and_distance(start_latitude, start_longitude, end_latitude, end_longitude):
    """ 获取起始点到终点的自行车路线的时长和距离 """
    directions_url = (
        f"https://maps.googleapis.com/maps/api/directions/json?origin={start_latitude},{start_longitude}"
        f"&destination={end_latitude},{end_longitude}&mode=walking&key={api_key}"
    )

    response = requests.get(directions_url)

    if response.status_code == 200:
        directions_data = response.json()
        if directions_data.get('routes'):
            # 获取第一个路线
            route = directions_data['routes'][0]
            leg = route['legs'][0]  # 获取第一个路线段

            # 获取路线时长和距离
            duration = leg['duration']['text']  # 人类可读的时长 (例如 "15 mins")
            distance = leg['distance']['text']  # 人类可读的距离 (例如 "3.5 km")

            return duration, distance  # 返回时长和距离
        else:
            return None, None  # 如果没有找到路线，返回 None
    else:
        print(f"Error: {response.status_code}")
        return None, None  # 如果请求失败，返回 None
