from django.urls import path
from . import views

urlpatterns = [
    path('analyse/', views.analyse, name='analyse'),
    path('analyse/direct/', views.analyse_direct, name='analyse_direct'),
]