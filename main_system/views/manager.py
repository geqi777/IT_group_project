from django.shortcuts import render
#Gloris programmes here
def manager(request):
    return render(request, 'manager/manager_homepage.html')