from django.urls import path
from . import views


urlpatterns = [
    path('', views.OutflowListView.as_view(), name='outflow_list'),
    path('create/', views.OutflowCreateView.as_view(), name='outflow_create'),
    path('<int:pk>/', views.OutflowDetailView.as_view(), name='outflow_detail'),

    path('api/v1/', views.OutflowCreateListAPIView.as_view(), name='outflow-create-list-api-view'),
    path('api/v1/<int:pk>/', views.OutflowRetrieveAPIView.as_view(), name='outflow-detail-api-view'),
]
