from django.shortcuts import render, redirect
import requests

def get_user_location(request):
    return render(request, 'map/map_layout.html')
