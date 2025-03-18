from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect


class CustomerAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Check if the current request is related to customer paths
        if not request.path_info.startswith('/customer/'):
            return None  # If it's not a customer-related request, skip processing

        # Allowed pages, such as the customer login page
        allowed_paths = ['/customer/login/', '/customer/register/']
        if request.path_info in allowed_paths:
            return None

        # Check if the user is logged in
        customer_info = request.session.get('user_info')
        # print("customer auth middleware")
        print(dict(request.session))
        # If the user is not logged in, redirect to the customer login page
        if not customer_info:
            return redirect('/customer/login/')

        # If logged in, continue processing the request
        return None
