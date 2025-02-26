from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect, HttpResponse

class EmployeeAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 检查当前请求是否属于 employee 相关的路径
        if not request.path_info.startswith('/operation/'):
            return None  # 如果不是 employee 相关的请求，直接跳过处理

        # 允许访问的页面，比如 employee 登录页面
        allowed_paths = ['/operation/login/']
        if request.path_info in allowed_paths:
            return None

        # 检查用户是否已登录
        employee_info = request.session.get('info')
        print("进入了 EmployeeAuthMiddleware")

        # 如果用户未登录，则重定向到 employee 登录页面
        if not employee_info or not employee_info.get('is_employee'):
            return redirect('/operation/login/')

