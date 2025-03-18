from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect, HttpResponse

class EmployeeAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Check if the current request is related to employee paths
        if not request.path_info.startswith('/operation/'):
            return None  # If it's not an employee-related request, skip processing

        # Allowed pages, such as the employee login page
        allowed_paths = ['/operation/login/']
        if request.path_info in allowed_paths:
            return None

        # Check if the user is logged in
        employee_info = request.session.get('admin_info')
        print(employee_info)
        print("Entered EmployeeAuthMiddleware")

        # If the user is not logged in, redirect to the employee login page
        if not employee_info:
            return redirect('/operation/login/')
