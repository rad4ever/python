from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('agents/', views.agents_dashboard, name='agents_dashboard'),
    path('providers/', views.providers_dashboard, name='providers_dashboard'),
    path('sales-officers/', views.sales_officers_dashboard, name='sales_officers_dashboard'),
      path('activities/', views.activities_dashboard, name='activities_dashboard'),
    path('api/activities-data/', views.activities_data, name='activities_data'),  # تم تصحيح المسار
   
    #path('api/chart-data/', views.chart_data, name='chart_data'),

]
