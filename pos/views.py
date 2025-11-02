from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.views.generic import ListView
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
import json

from . import services, forms
from .models import Sale, SaleItem, SalePayment, LedgerEntry, PaymentMethod
from .serializers import (
    SaleSerializer, SaleItemSerializer, SalePaymentSerializer,
    LedgerEntrySerializer
)
from customers.models import Customer
from products.models import Product


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
                'fee_percentage': str(pm.fee_percentage),
                'fee_payer': pm.fee_payer,
                'discount_percentage': str(pm.discount_percentage),  # Para compatibilidade
                'charge_percentage': str(pm.charge_percentage),  # Novo: acréscimo
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


class SaleListView(LoginRequiredMixin, ListView):
    """Lista todas as vendas finalizadas."""
    model = Sale
    template_name = 'pos/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 20
    ordering = ['-finalized_at', '-created_at']
    
    def get_queryset(self):
        queryset = Sale.objects.filter(
            status=Sale.Status.FINALIZED
        ).select_related(
            'customer', 'user'
        ).prefetch_related(
            'items__product', 'payments__payment_method'
        )
        
        # Filtros
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(id__icontains=search) |
                Q(customer__full_name__icontains=search) |
                Q(customer__phone__icontains=search)
            )
        
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(finalized_at__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(finalized_at__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        # Estatísticas
        queryset = self.get_queryset()
        context['total_sales'] = queryset.count()
        context['total_amount'] = sum(sale.total for sale in queryset)
        
        return context


class SaleDetailView(LoginRequiredMixin, View):
    """Exibe detalhes completos de uma venda."""
    template_name = 'pos/sale_detail.html'
    
    def get(self, request, pk):
        sale = get_object_or_404(
            Sale.objects.select_related('customer', 'user').prefetch_related(
                'items__product',
                'payments__payment_method',
                'ledger_entries'
            ),
            pk=pk
        )
        
        context = {
            'sale': sale,
            'items': sale.items.all(),
            'payments': sale.payments.all(),
            'ledger_entries': sale.ledger_entries.all(),
        }
        
        return render(request, self.template_name, context)


class PaymentMethodListView(LoginRequiredMixin, View):
    """View para listar e criar métodos de pagamento."""
    template_name = 'pos/payment_method_list.html'

    def get(self, request, *args, **kwargs):
        form = forms.PaymentMethodForm()
        payment_methods = PaymentMethod.objects.all()
        return self._render(request, form, payment_methods)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'create')

        if action == 'toggle':
            method_id = request.POST.get('payment_method_id')
            payment_method = PaymentMethod.objects.filter(pk=method_id).first()

            if not payment_method:
                messages.error(request, 'Método de pagamento não encontrado.')
                return redirect('pos:payment_method_list')

            payment_method.is_active = not payment_method.is_active
            payment_method.save(update_fields=['is_active', 'updated_at'])
            status = 'ativado' if payment_method.is_active else 'desativado'
            messages.success(request, f'Método "{payment_method.name}" {status} com sucesso.')
            return redirect('pos:payment_method_list')

        form = forms.PaymentMethodForm(request.POST)
        payment_methods = PaymentMethod.objects.all()

        if form.is_valid():
            payment_method = form.save()
            messages.success(request, f'Método "{payment_method.name}" cadastrado com sucesso.')
            return redirect('pos:payment_method_list')

        messages.error(request, 'Corrija os erros abaixo para continuar.')
        return self._render(request, form, payment_methods)

    def _render(self, request, form, payment_methods):
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'payment_methods': payment_methods,
            },
        )


class PaymentMethodUpdateView(LoginRequiredMixin, View):
    """View para editar um método de pagamento."""
    template_name = 'pos/payment_method_update.html'

    def get(self, request, pk):
        payment_method = get_object_or_404(PaymentMethod, pk=pk)
        form = forms.PaymentMethodForm(instance=payment_method)
        return render(request, self.template_name, {'form': form, 'payment_method': payment_method})

    def post(self, request, pk):
        payment_method = get_object_or_404(PaymentMethod, pk=pk)
        form = forms.PaymentMethodForm(request.POST, instance=payment_method)

        if form.is_valid():
            payment_method = form.save()
            messages.success(request, f'Método "{payment_method.name}" atualizado com sucesso.')
            return redirect('pos:payment_method_list')

        messages.error(request, 'Corrija os erros abaixo para continuar.')
        return render(request, self.template_name, {'form': form, 'payment_method': payment_method})

