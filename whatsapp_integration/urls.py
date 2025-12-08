from django.urls import path
from . import views

app_name = 'whatsapp_integration'

urlpatterns = [
    path('webhook/', views.whatsapp_webhook, name='webhook'),
]
