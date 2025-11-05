from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'pos'

urlpatterns = [
    # PDV principal
    path('', views.POSNewView.as_view(), name='new'),
    path('new/', views.POSNewView.as_view(), name='new_alt'),
    
    # Listagem e detalhes de vendas
    path('sales/', views.SaleListView.as_view(), name='sale_list'),
    path('sales/<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('sales/<int:pk>/receipt/', views.SaleReceiptView.as_view(), name='sale_receipt'),
    
    # Métodos de pagamento
    path('payment-methods/', views.PaymentMethodListView.as_view(), name='payment_method_list'),
    path('payment-methods/<int:pk>/edit/', views.PaymentMethodUpdateView.as_view(), name='payment_method_update'),
    
    # Teste de API (apenas para debug)
    path('test-api/', TemplateView.as_view(template_name='pos/test_api.html'), name='test_api'),
    
    # Operações de itens (JSON API)
    path('add-item/', views.add_item_view, name='add_item'),
    path('update-item/', views.update_item_view, name='update_item'),
    path('remove-item/', views.remove_item_view, name='remove_item'),
    
    # Operações de pagamento (JSON API)
    path('add-payment/', views.add_payment_view, name='add_payment'),
    path('remove-payment/', views.remove_payment_view, name='remove_payment'),
    path('apply-credit/', views.apply_credit_view, name='apply_credit'),
    
    # Cliente e finalização
    path('set-customer/', views.set_customer_view, name='set_customer'),
    path('finalize/', views.finalize_view, name='finalize'),
    
    # Lançamentos (ledger)
    path('ledger/', views.LedgerListView.as_view(), name='ledger_list'),
    path('ledger/reassign/', views.reassign_ledger_view, name='reassign_ledger'),
    
    # Devoluções (returns)
    path('returns/', views.ReturnListView.as_view(), name='return_list'),
    path('returns/<int:pk>/', views.ReturnDetailView.as_view(), name='return_detail'),
    path('returns/create/<int:sale_pk>/', views.ReturnCreateView.as_view(), name='return_create'),
    path('returns/<int:pk>/approve/', views.return_approve_view, name='return_approve'),
    path('returns/<int:pk>/complete/', views.return_complete_view, name='return_complete'),
    path('returns/<int:pk>/reject/', views.return_reject_view, name='return_reject'),
    path('returns/report/', views.ReturnReportView.as_view(), name='return_report'),
]
