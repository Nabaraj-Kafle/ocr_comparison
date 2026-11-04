from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload, name='upload'),
    path('result/<int:pk>/', views.result, name='result'),
    path('progress/<int:pk>/', views.progress, name='progress'),
    path('history/', views.history, name='history'),
    path('export/<int:pk>/<str:provider>/<str:format>/', views.export, name='export'),
]