from django.urls import path
from . import views

urlpatterns = [
    path('budget/', views.budget_forecast, name='forecast-budget'),
    path('simulate/', views.simulate, name='forecast-simulate'),
    path('wants/', views.wants_envelopes, name='forecast-wants'),
]
