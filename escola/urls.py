from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('escola/', views.CalendarioView.as_view(), name='calendario'),
    path('escola/toggle-dia/<str:data_str>/', views.toggle_dia_letivo, name='toggle_dia_letivo'),
    path('escola/upload-bncc/', views.upload_bncc, name='upload_bncc'),
]
