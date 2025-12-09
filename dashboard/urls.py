from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('link-whatsapp/', views.link_whatsapp, name='link_whatsapp'),
    path('verify-whatsapp/', views.verify_whatsapp, name='verify_whatsapp'),
    path('categories/', views.categories, name='categories'),
    path('expenses/', views.expenses_list, name='expenses'),
    path('send-spend-reminder/', views.send_spend_reminder, name='send_spend_reminder'),
]
