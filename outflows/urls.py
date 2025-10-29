from django.urls import path
from . import views


urlpatterns = [
    path('payment-methods/', views.PaymentMethodListView.as_view(), name='payment_method_list'),
    path('outflows/list/', views.OutflowListView.as_view(), name='outflow_list'),
    path('outflows/create/', views.OutflowCreateView.as_view(), name='outflow_create'),
    path('outflows/<int:pk>/detail/', views.OutflowDetailView.as_view(), name='outflow_detail'),
    path('outflows/returns/', views.OutflowReturnLandingView.as_view(), name='outflow_returns'),

    path('api/v1/outflows/', views.OutflowCreateListAPIView.as_view(), name='outflow-create-list-api-view'),
    path('api/v1/outflows/<int:pk>/', views.OutflowRetrieveAPIView.as_view(), name='outflow-detail-api-view'),
]
