from django.urls import path
from . import views

urlpatterns = [
    path('budget/', views.budget_forecast, name='forecast-budget'),
]
