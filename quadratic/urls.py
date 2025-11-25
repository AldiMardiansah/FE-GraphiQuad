from django.urls import path
from . import views

app_name = 'quadratic'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('app/', views.index, name='index'),
    path('calculate/', views.calculate, name='calculate'),
    path('send-contact/', views.send_contact_email, name='send_contact'),
]