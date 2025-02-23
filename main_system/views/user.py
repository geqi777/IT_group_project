from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.shortcuts import HttpResponse, get_object_or_404
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime, timedelta
from groupProject import settings
from main_system import models
from main_system.utils.boostrapModelForm import Customer_ModelForm, Customer_Edit2Form, ResetPasswordForm, Customer_RegisterForm, HistoryModelForm
from main_system.utils.map_function import get_address_from_latlng, \
    get_bicycle_route_duration_and_distance, get_random_location_in_glasgow, get_walking_route_duration_and_distance
from main_system.utils.pagination import PageNumberPagination
import math

