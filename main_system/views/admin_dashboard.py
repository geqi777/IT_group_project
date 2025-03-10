from django.shortcuts import render

def admin_dashboard(request):
    return render(request, 'operation/admin_dashboard.html')
