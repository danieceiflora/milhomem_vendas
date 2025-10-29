from django.urls import path
from . import views


urlpatterns = [
    path('customers/list/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/detail/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/update/', views.CustomerUpdateView.as_view(), name='customer_update'),

    path('api/v1/customers/', views.CustomerListCreateAPIView.as_view(), name='customer-list-create-api'),
    path('api/v1/customers/<int:pk>/', views.CustomerRetrieveUpdateDestroyAPIView.as_view(), name='customer-detail-api'),
]
