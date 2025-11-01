from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'pos'

urlpatterns = [
    # PDV principal
    path('', views.POSNewView.as_view(), name='new'),
    path('new/', views.POSNewView.as_view(), name='new_alt'),
    
    # Teste de API (apenas para debug)
    path('test-api/', TemplateView.as_view(template_name='pos/test_api.html'), name='test_api'),
    
    # Operações de itens (JSON API)
    path('add-item/', views.add_item_view, name='add_item'),
    path('update-item/', views.update_item_view, name='update_item'),
    path('remove-item/', views.remove_item_view, name='remove_item'),
    
    # Operações de pagamento (JSON API)
    path('add-payment/', views.add_payment_view, name='add_payment'),
    path('remove-payment/', views.remove_payment_view, name='remove_payment'),
    
    # Cliente e finalização
    path('set-customer/', views.set_customer_view, name='set_customer'),
    path('finalize/', views.finalize_view, name='finalize'),
    
    # Lançamentos (ledger)
    path('ledger/', views.LedgerListView.as_view(), name='ledger_list'),
    path('ledger/reassign/', views.reassign_ledger_view, name='reassign_ledger'),
]
