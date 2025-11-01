from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.generic import ListView
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
import json

from . import services
from .models import Sale, SaleItem, SalePayment, LedgerEntry
from .serializers import (
    SaleSerializer, SaleItemSerializer, SalePaymentSerializer,
    LedgerEntrySerializer
)
from customers.models import Customer
from products.models import Product
from outflows.models import PaymentMethod


class POSNewView(LoginRequiredMixin, View):
    """View principal do PDV - cria/carrega venda em rascunho."""
    template_name = 'pos/new.html'
    
    def get(self, request):
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        # Busca ou cria venda em rascunho
        sale = services.get_or_create_draft_sale(
            user=request.user,
            session_key=session_key
        )
        
        # Serializa dados para o template
        serializer = SaleSerializer(sale)
        
        # Busca métodos de pagamento ativos
        payment_methods = PaymentMethod.objects.filter(is_active=True)
        payment_methods_data = [
            {
                'id': pm.id,
                'name': pm.name,
                'discount_percentage': str(pm.discount_percentage)
            }
            for pm in payment_methods
        ]
        
        context = {
            'sale': sale,
            'sale_data': serializer.data,
            'payment_methods': payment_methods,
            'payment_methods_data': payment_methods_data,
        }
        
        return render(request, self.template_name, context)


@login_required
@require_http_methods(["POST"])
def add_item_view(request):
    """Adiciona um item à venda em rascunho."""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        session_key = request.session.session_key
        sale = services.get_or_create_draft_sale(request.user, session_key)
        
        item = services.add_item(sale, product_id, quantity)
        
        # Atualiza sale para pegar os dados recalculados
        sale.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'item': SaleItemSerializer(item).data,
            'sale': SaleSerializer(sale).data
        })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Erro ao adicionar item'}, status=500)


@login_required
@require_http_methods(["POST"])
def update_item_view(request):
    """Atualiza a quantidade de um item."""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 0))
        
        session_key = request.session.session_key
        sale = services.get_or_create_draft_sale(request.user, session_key)
        
        item = services.update_item(sale, item_id, quantity)
        
        sale.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'item': SaleItemSerializer(item).data if item else None,
            'sale': SaleSerializer(sale).data
        })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Erro ao atualizar item'}, status=500)


@login_required
@require_http_methods(["POST"])
def remove_item_view(request):
    """Remove um item da venda."""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        session_key = request.session.session_key
        sale = services.get_or_create_draft_sale(request.user, session_key)
        
        services.remove_item(sale, item_id)
        
        sale.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'sale': SaleSerializer(sale).data
        })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Erro ao remover item'}, status=500)


@login_required
@require_http_methods(["POST"])
def add_payment_view(request):
    """Adiciona um pagamento à venda."""
    try:
        data = json.loads(request.body)
        payment_method_id = data.get('payment_method_id')
        amount = data.get('amount')
        cash_tendered = data.get('cash_tendered')
        
        # Converte para Decimal se fornecido
        amount = Decimal(str(amount)) if amount else None
        cash_tendered = Decimal(str(cash_tendered)) if cash_tendered else None
        
        session_key = request.session.session_key
        sale = services.get_or_create_draft_sale(request.user, session_key)
        
        payment = services.add_payment(sale, payment_method_id, amount, cash_tendered)
        
        sale.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'payment': SalePaymentSerializer(payment).data,
            'sale': SaleSerializer(sale).data
        })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Erro ao adicionar pagamento'}, status=500)


@login_required
@require_http_methods(["POST"])
def remove_payment_view(request):
    """Remove um pagamento da venda."""
    try:
        data = json.loads(request.body)
        payment_id = data.get('payment_id')
        
        session_key = request.session.session_key
        sale = services.get_or_create_draft_sale(request.user, session_key)
        
        services.remove_payment(sale, payment_id)
        
        sale.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'sale': SaleSerializer(sale).data
        })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Erro ao remover pagamento'}, status=500)


@login_required
@require_http_methods(["POST"])
def set_customer_view(request):
    """Define ou altera o cliente da venda."""
    try:
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        
        session_key = request.session.session_key
        sale = services.get_or_create_draft_sale(request.user, session_key)
        
        sale = services.set_customer(sale, customer_id)
        
        return JsonResponse({
            'success': True,
            'sale': SaleSerializer(sale).data
        })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Erro ao definir cliente'}, status=500)


@login_required
@require_http_methods(["POST"])
def finalize_view(request):
    """Finaliza a venda."""
    try:
        data = json.loads(request.body)
        resolution = data.get('resolution')  # 'apply_discount', 'generate_debit', 'generate_credit', etc
        
        session_key = request.session.session_key
        sale = services.get_or_create_draft_sale(request.user, session_key)
        
        result = services.finalize_sale(sale, resolution)
        
        if result['status'] == 'success':
            return JsonResponse({
                'success': True,
                'message': 'Venda finalizada com sucesso!',
                'sale_id': result['sale_id']
            })
        elif result['status'] == 'diff':
            return JsonResponse({
                'success': False,
                'requires_resolution': True,
                'difference': str(result['difference']),
                'type': result['type']
            })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Erro ao finalizar venda'}, status=500)


class LedgerListView(LoginRequiredMixin, ListView):
    """Lista de lançamentos (créditos/débitos)."""
    model = LedgerEntry
    template_name = 'pos/ledger_list.html'
    context_object_name = 'entries'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = LedgerEntry.objects.select_related('customer', 'sale')
        
        # Filtros
        type_filter = self.request.GET.get('type')
        status_filter = self.request.GET.get('status')
        customer_filter = self.request.GET.get('customer')
        
        if type_filter:
            queryset = queryset.filter(type=type_filter)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if customer_filter:
            queryset = queryset.filter(customer_id=customer_filter)
        
        return queryset


@login_required
@require_http_methods(["POST"])
def reassign_ledger_view(request):
    """Reatribui um lançamento para outro cliente."""
    try:
        data = json.loads(request.body)
        entry_id = data.get('entry_id')
        customer_id = data.get('customer_id')
        
        entry = services.reassign_ledger_entry(entry_id, customer_id)
        
        return JsonResponse({
            'success': True,
            'entry': LedgerEntrySerializer(entry).data
        })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Erro ao reatribuir lançamento'}, status=500)
