from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json

from . import services, forms, return_services
from .models import Sale, SaleItem, SalePayment, LedgerEntry, PaymentMethod, Return, ReturnItem
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
        # Garante que os totais estejam recalculados antes de serializar
        sale = services.recalc_totals(sale)
        
        # Serializa dados para o template
        serializer = SaleSerializer(sale)
        
        # Busca crédito disponível do cliente
        available_credit = services.get_customer_available_credit(sale.customer, sale=sale)
        
        # Busca métodos de pagamento ativos
        payment_methods = PaymentMethod.objects.filter(is_active=True, is_internal=False)
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
            'available_credit': available_credit,
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
        
        # Busca crédito disponível do novo cliente
        available_credit = services.get_customer_available_credit(sale.customer, sale=sale)
        
        return JsonResponse({
            'success': True,
            'sale': SaleSerializer(sale).data,
            'available_credit': str(available_credit)
        })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Erro ao definir cliente'}, status=500)


@login_required
@require_http_methods(["POST"])
def cancel_sale_view(request):
    """Reinicia a venda em rascunho do usuário descartando itens e pagamentos."""
    try:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        sale = services.get_or_create_draft_sale(request.user, session_key)
        sale = services.cancel_sale(sale)
        available_credit = services.get_customer_available_credit(sale.customer, sale=sale)
        
        return JsonResponse({
            'success': True,
            'sale': SaleSerializer(sale).data,
            'available_credit': str(available_credit)
        })
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Erro ao cancelar venda'}, status=500)


@login_required
@require_http_methods(["POST"])
def apply_credit_view(request):
    """Aplica crédito disponível do cliente como pagamento."""
    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        
        # Valida se amount foi fornecido
        if amount is None or amount == '':
            return JsonResponse({'success': False, 'error': 'Valor do crédito é obrigatório'}, status=400)
        
        credit_amount = Decimal(str(amount))
        
        session_key = request.session.session_key
        sale = services.get_or_create_draft_sale(request.user, session_key)
        
        payment = services.apply_credit_to_sale(sale, credit_amount)
        
        sale.refresh_from_db()
        
        # Atualiza crédito disponível
        available_credit = services.get_customer_available_credit(sale.customer, sale=sale)
        
        return JsonResponse({
            'success': True,
            'payment': SalePaymentSerializer(payment).data,
            'sale': SaleSerializer(sale).data,
            'available_credit': str(available_credit)
        })
    
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Erro ao aplicar crédito: {str(e)}'}, status=500)


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['type_filter'] = self.request.GET.get('type', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['customer_filter'] = self.request.GET.get('customer', '')
        context['customers'] = Customer.objects.order_by('full_name')
        return context


@login_required
@require_http_methods(["POST"])
def reassign_ledger_view(request):
    """Reatribui um lançamento para outro cliente."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Apenas usuários staff podem transferir créditos.'}, status=403)

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
        payment_methods = PaymentMethod.objects.filter(is_internal=False)
        return self._render(request, form, payment_methods)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'create')

        if action == 'toggle':
            method_id = request.POST.get('payment_method_id')
            payment_method = PaymentMethod.objects.filter(pk=method_id, is_internal=False).first()

            if not payment_method:
                messages.error(request, 'Método de pagamento não encontrado.')
                return redirect('pos:payment_method_list')

            payment_method.is_active = not payment_method.is_active
            payment_method.save(update_fields=['is_active', 'updated_at'])
            status = 'ativado' if payment_method.is_active else 'desativado'
            messages.success(request, f'Método "{payment_method.name}" {status} com sucesso.')
            return redirect('pos:payment_method_list')

        form = forms.PaymentMethodForm(request.POST)
        payment_methods = PaymentMethod.objects.filter(is_internal=False)

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
        payment_method = get_object_or_404(PaymentMethod, pk=pk, is_internal=False)
        form = forms.PaymentMethodForm(instance=payment_method)
        return render(request, self.template_name, {'form': form, 'payment_method': payment_method})

    def post(self, request, pk):
        payment_method = get_object_or_404(PaymentMethod, pk=pk, is_internal=False)
        form = forms.PaymentMethodForm(request.POST, instance=payment_method)

        if form.is_valid():
            payment_method = form.save()
            messages.success(request, f'Método "{payment_method.name}" atualizado com sucesso.')
            return redirect('pos:payment_method_list')

        messages.error(request, 'Corrija os erros abaixo para continuar.')
        return render(request, self.template_name, {'form': form, 'payment_method': payment_method})


class SaleReceiptView(LoginRequiredMixin, View):
    """View para gerar o recibo não-fiscal de uma venda."""
    template_name = 'pos/receipt.html'

    def get(self, request, pk):
        sale = get_object_or_404(
            Sale.objects.prefetch_related('items__product', 'payments__payment_method'),
            pk=pk
        )
        
        # Apenas vendas finalizadas podem ter recibo
        if sale.status != Sale.Status.FINALIZED:
            messages.warning(request, 'Apenas vendas finalizadas podem ter recibo impresso.')
            return redirect('pos:new')
        
        from django.utils import timezone
        context = {
            'sale': sale,
            'now': timezone.now(),
        }
        
        return render(request, self.template_name, context)


# ============================================================================
# VIEWS DE DEVOLUÇÃO
# ============================================================================

class ReturnListView(UserPassesTestMixin, ListView):
    """Lista todas as devoluções (apenas para staff)."""
    model = Return
    template_name = 'pos/return_list.html'
    context_object_name = 'returns'
    paginate_by = 20
    
    def test_func(self):
        """Apenas usuários staff podem acessar."""
        return self.request.user.is_staff
    
    def get_queryset(self):
        queryset = Return.objects.select_related(
            'original_sale', 'customer', 'user', 'approved_by'
        ).prefetch_related('items')
        
        # Filtros
        status = self.request.GET.get('status')
        refund_method = self.request.GET.get('refund_method')
        search = self.request.GET.get('search')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if refund_method:
            queryset = queryset.filter(refund_method=refund_method)
        
        if search:
            queryset = queryset.filter(
                Q(customer__full_name__icontains=search) |
                Q(reason__icontains=search) |
                Q(original_sale__id__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas
        from django.db import models as db_models
        stats = Return.objects.aggregate(
            total_pending=Sum('total_amount', filter=Q(status=Return.Status.PENDING)),
            total_completed=Sum('total_amount', filter=Q(status=Return.Status.COMPLETED)),
            count_pending=db_models.Count('id', filter=Q(status=Return.Status.PENDING)),
            count_completed=db_models.Count('id', filter=Q(status=Return.Status.COMPLETED)),
        )
        
        context['stats'] = stats
        context['status_choices'] = Return.Status.choices
        context['refund_method_choices'] = Return.RefundMethod.choices
        
        return context


class ReturnDetailView(UserPassesTestMixin, DetailView):
    """Visualiza detalhes de uma devolução (apenas para staff)."""
    model = Return
    template_name = 'pos/return_detail.html'
    context_object_name = 'return_obj'
    
    def test_func(self):
        """Apenas usuários staff podem acessar."""
        return self.request.user.is_staff
    
    def get_queryset(self):
        return Return.objects.select_related(
            'original_sale', 'customer', 'user', 'approved_by', 'ledger_entry'
        ).prefetch_related('items__product', 'items__sale_item')


class ReturnCreateView(UserPassesTestMixin, View):
    """Cria uma nova devolução para uma venda (apenas para staff)."""
    template_name = 'pos/return_create.html'
    
    def test_func(self):
        """Apenas usuários staff podem acessar."""
        return self.request.user.is_staff
    
    def get(self, request, sale_pk):
        sale = get_object_or_404(
            Sale.objects.prefetch_related('items__product', 'items__return_items__return_instance'),
            pk=sale_pk
        )
        
        # Validar se a venda pode ter devolução
        if sale.status not in [Sale.Status.FINALIZED, Sale.Status.PARTIALLY_RETURNED]:
            messages.error(request, 'Apenas vendas finalizadas ou parcialmente devolvidas podem ter devoluções.')
            return redirect('pos:sale_detail', pk=sale_pk)
        
        # Preparar dados dos itens com quantidades disponíveis
        items_data = []
        for item in sale.items.all():
            # Calcular quantidade já devolvida
            already_returned = sum(
                ri.quantity
                for ri in item.return_items.filter(
                    return_instance__status__in=[Return.Status.APPROVED, Return.Status.COMPLETED]
                )
            )
            available = item.quantity - already_returned
            
            if available > 0:
                items_data.append({
                    'item': item,
                    'already_returned': already_returned,
                    'available': available
                })
        
        if not items_data:
            messages.warning(request, 'Todos os itens desta venda já foram devolvidos.')
            return redirect('pos:sale_detail', pk=sale_pk)
        
        context = {
            'sale': sale,
            'items_data': items_data,
            'refund_method_choices': Return.RefundMethod.choices,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, sale_pk):
        sale = get_object_or_404(Sale, pk=sale_pk)
        
        try:
            # Coletar dados do formulário
            reason = request.POST.get('reason', '').strip()
            refund_method = request.POST.get('refund_method', Return.RefundMethod.CREDIT)
            notes = request.POST.get('notes', '').strip()
            
            if not reason:
                raise return_services.ReturnValidationError('O motivo da devolução é obrigatório.')
            
            # Coletar itens selecionados
            items_data = []
            for key in request.POST:
                if key.startswith('item_'):
                    sale_item_id = key.replace('item_', '')
                    quantity_str = request.POST.get(key)
                    
                    if quantity_str:
                        try:
                            quantity = int(quantity_str)
                            if quantity > 0:
                                price_key = f'price_{sale_item_id}'
                                price_value = request.POST.get(price_key, '').strip()
                                unit_price = None
                                if price_value:
                                    try:
                                        unit_price = Decimal(price_value.replace(',', '.'))
                                    except (InvalidOperation, ValueError):
                                        raise return_services.ReturnValidationError(
                                            'Valor unitário inválido informado para um dos itens selecionados.'
                                        )
                                items_data.append({
                                    'sale_item_id': int(sale_item_id),
                                    'quantity': quantity,
                                    'unit_price': unit_price
                                })
                        except ValueError:
                            continue
            
            # Criar devolução
            return_instance = return_services.create_return(
                sale=sale,
                items_data=items_data,
                reason=reason,
                refund_method=refund_method,
                user=request.user,
                notes=notes
            )
            
            messages.success(
                request,
                f'Devolução #{return_instance.pk} criada com sucesso! '
                f'Aguardando aprovação.'
            )
            return redirect('pos:return_detail', pk=return_instance.pk)
            
        except return_services.ReturnValidationError as e:
            messages.error(request, str(e))
            return redirect('pos:return_create', sale_pk=sale_pk)


@login_required
@require_http_methods(['POST'])
def return_approve_view(request, pk):
    """Aprova uma devolução (apenas para staff)."""
    if not request.user.is_staff:
        messages.error(request, 'Apenas gerentes podem aprovar devoluções.')
        return redirect('pos:return_detail', pk=pk)
    
    return_instance = get_object_or_404(Return, pk=pk)
    
    try:
        return_services.approve_return(return_instance, request.user)
        messages.success(request, f'Devolução #{return_instance.pk} aprovada com sucesso!')
    except return_services.ReturnValidationError as e:
        messages.error(request, str(e))
    
    return redirect('pos:return_detail', pk=pk)


@login_required
@require_http_methods(['POST'])
def return_complete_view(request, pk):
    """Completa uma devolução aprovada (atualiza estoque e gera crédito)."""
    if not request.user.is_staff:
        messages.error(request, 'Apenas gerentes podem completar devoluções.')
        return redirect('pos:return_detail', pk=pk)
    
    return_instance = get_object_or_404(Return, pk=pk)
    
    try:
        return_services.complete_return(return_instance)
        messages.success(
            request,
            f'Devolução #{return_instance.pk} concluída! '
            f'Estoque atualizado e crédito gerado.'
        )
    except return_services.ReturnValidationError as e:
        messages.error(request, str(e))
    
    return redirect('pos:return_detail', pk=pk)


@login_required
@require_http_methods(['POST'])
def return_reject_view(request, pk):
    """Rejeita uma devolução (apenas para staff)."""
    if not request.user.is_staff:
        messages.error(request, 'Apenas gerentes podem rejeitar devoluções.')
        return redirect('pos:return_detail', pk=pk)
    
    return_instance = get_object_or_404(Return, pk=pk)
    rejection_reason = request.POST.get('rejection_reason', '').strip()
    
    try:
        return_services.reject_return(return_instance, request.user, rejection_reason)
        messages.warning(request, f'Devolução #{return_instance.pk} rejeitada.')
    except return_services.ReturnValidationError as e:
        messages.error(request, str(e))
    
    return redirect('pos:return_detail', pk=pk)


class ReturnReportView(UserPassesTestMixin, ListView):
    """Relatório de devoluções com filtros e totalizadores."""
    model = Return
    template_name = 'pos/return_report.html'
    context_object_name = 'returns'
    
    def test_func(self):
        """Apenas usuários staff podem acessar."""
        return self.request.user.is_staff
    
    def get_queryset(self):
        queryset = Return.objects.select_related(
            'original_sale', 'customer', 'user', 'approved_by'
        ).prefetch_related('items__product')
        
        # Filtros
        status = self.request.GET.get('status')
        refund_method = self.request.GET.get('refund_method')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        customer_id = self.request.GET.get('customer')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if refund_method:
            queryset = queryset.filter(refund_method=refund_method)
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        queryset = self.get_queryset()
        
        # Totalizadores
        from django.db import models as db_models
        totals = queryset.aggregate(
            total_amount=Sum('total_amount'),
            total_count=db_models.Count('id'),
        )
        
        # Calcula ticket médio
        average_ticket = 0
        if totals['total_count'] and totals['total_count'] > 0 and totals['total_amount']:
            average_ticket = totals['total_amount'] / totals['total_count']
        
        # Totais por status
        by_status = {}
        for status_code, status_label in Return.Status.choices:
            stats = queryset.filter(status=status_code).aggregate(
                total=Sum('total_amount'),
                count=db_models.Count('id')
            )
            by_status[status_label] = stats
        
        # Totais por método de reembolso
        by_method = {}
        for method_code, method_label in Return.RefundMethod.choices:
            stats = queryset.filter(refund_method=method_code).aggregate(
                total=Sum('total_amount'),
                count=db_models.Count('id')
            )
            by_method[method_label] = stats
        
        context['totals'] = totals
        context['average_ticket'] = average_ticket
        context['by_status'] = by_status
        context['by_method'] = by_method
        context['status_choices'] = Return.Status.choices
        context['refund_method_choices'] = Return.RefundMethod.choices
        context['customers'] = Customer.objects.order_by('full_name')
        
        return context
