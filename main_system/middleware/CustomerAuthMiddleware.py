from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect


class CustomerAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 检查当前请求是否属于 customer 相关的路径
        if not request.path_info.startswith('/customer/'):
            return None  # 如果不是 customer 相关的请求，直接跳过处理

        # 允许访问的页面，比如 customer 登录页面
        allowed_paths = ['/customer/login/', '/customer/register/']
        if request.path_info in allowed_paths:
            return None

        # 检查用户是否已登录
        customer_info = request.session.get('user_info')
        # print("customer auth middleware")
        print(dict(request.session))
        # 如果用户未登录，则重定向到 customer 登录页面
        if not customer_info:
            return redirect('/customer/login/')

        # 已登录，继续处理请求
        return None

