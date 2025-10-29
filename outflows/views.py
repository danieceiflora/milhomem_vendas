from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from rest_framework import generics
from app import metrics
from customers.models import Customer
from . import forms, models, serializers


class OutflowListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Outflow
    template_name = 'outflow_list.html'
    context_object_name = 'outflows'
    paginate_by = 10
    permission_required = 'outflows.view_outflow'

    def get_queryset(self):
        queryset = super().get_queryset()
        product = self.request.GET.get('product')
        customer = self.request.GET.get('customer')

        if product:
            queryset = queryset.filter(items__product__title__icontains=product)
        if customer:
            queryset = queryset.filter(customer__full_name__icontains=customer)

        queryset = queryset.filter(operation_type=models.Outflow.OperationType.SALE)
        queryset = queryset.select_related('customer', 'payment_method').prefetch_related(
            Prefetch(
                'items',
                queryset=models.OutflowItem.objects.select_related('product__brand', 'product__category'),
            ),
        ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        outflows = context['outflows']

        for outflow in outflows:
            outflow.computed_total_items = outflow.total_items
            outflow.computed_total_amount = outflow.total_amount
            outflow.computed_final_amount = outflow.final_amount
            outflow.computed_discount_amount = outflow.payment_discount_amount

        context['product_metrics'] = metrics.get_product_metrics()
        context['sales_metrics'] = metrics.get_sales_metrics()
        context['filter_product'] = self.request.GET.get('product', '')
        context['filter_customer'] = self.request.GET.get('customer', '')
        return context


class OutflowCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'outflow_create.html'
    permission_required = 'outflows.add_outflow'
    success_url = reverse_lazy('outflow_list')

    def get(self, request, *args, **kwargs):
        form = forms.OutflowForm()
        items_formset = self._build_items_formset()
        return self._render(request, form, items_formset)

    def post(self, request, *args, **kwargs):
        form = forms.OutflowForm(request.POST)
        items_formset = self._build_items_formset(data=request.POST)

        if form.is_valid() and items_formset.is_valid():
            try:
                with transaction.atomic():
                    outflow = form.save(commit=False)
                    outflow.operation_type = models.Outflow.OperationType.SALE
                    outflow.related_outflow = None
                    outflow.payment_discount_percentage = Decimal('0')
                    if outflow.payment_method:
                        outflow.payment_discount_percentage = outflow.payment_method.discount_percentage
                    outflow.payment_discount_amount = Decimal('0')
                    outflow.final_amount = Decimal('0')
                    outflow.save()

                    items_formset.instance = outflow
                    self._save_items(items_formset, outflow)

                    outflow.refresh_financials()
                    outflow.save(update_fields=['payment_discount_amount', 'final_amount'])
            except ValidationError as error:
                for message in getattr(error, 'messages', [str(error)]):
                    form.add_error(None, message)
                transaction.set_rollback(True)
            else:
                messages.success(request, self._get_success_message())
                return redirect(self.success_url)

        return self._render(request, form, items_formset)

    def _build_items_formset(self, data=None):
        base_instance = models.Outflow()
        return forms.OutflowItemFormSet(data, prefix='items', instance=base_instance)

    def _save_items(self, formset, outflow):
        saved = False

        for form in formset.forms:
            if not getattr(form, 'cleaned_data', None) or form.cleaned_data.get('DELETE'):
                continue

            item = form.save(commit=False)
            product = item.product
            product.refresh_from_db()

            if item.quantity > product.quantity:
                form.add_error('quantity', f'Estoque insuficiente para {product}. Disponível: {product.quantity}.')
                raise ValidationError('Não foi possível registrar a venda por falta de estoque.')

            item.unit_cost = product.cost_price
            if item.unit_price in (None, Decimal('0')):
                item.unit_price = product.selling_price

            product.quantity -= item.quantity
            product.save(update_fields=['quantity'])

            item.outflow = outflow
            item.save()
            saved = True

        if not saved:
            raise ValidationError('Adicione ao menos um produto válido para a venda.')

    def _render(self, request, form, items_formset):
        form_data = getattr(form, 'data', None)
        customer_id = None

        if form_data and hasattr(form_data, 'get') and form_data.get('customer'):
            customer_id = form_data.get('customer')
        elif hasattr(form, 'initial') and form.initial.get('customer'):
            customer_id = form.initial.get('customer')
        selected_customer = None

        if customer_id:
            try:
                customer = Customer.objects.filter(pk=customer_id).first()
            except (TypeError, ValueError):
                customer = None

            if customer:
                selected_customer = {
                    'id': customer.id,
                    'name': customer.full_name,
                    'cpf': customer.formatted_cpf,
                    'phone': customer.formatted_phone,
                }

        payment_methods_queryset = form.fields['payment_method'].queryset
        payment_methods_data = [
            {
                'id': method.id,
                'name': method.name,
                'discount_percentage': str(method.discount_percentage),
            }
            for method in payment_methods_queryset
        ]

        return render(
            request,
            self.template_name,
            {
                'form': form,
                'items_formset': items_formset,
                'selected_customer': selected_customer,
                'payment_methods_data': payment_methods_data,
            },
        )

    def _get_success_message(self):
        return 'Venda registrada com sucesso.'


class PaymentMethodListView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'payment_method_list.html'
    permission_required = 'outflows.view_paymentmethod'

    def get(self, request, *args, **kwargs):
        form = forms.PaymentMethodForm()
        payment_methods = models.PaymentMethod.objects.all()
        return self._render(request, form, payment_methods)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'create')

        if action == 'toggle':
            if not request.user.has_perm('outflows.change_paymentmethod'):
                messages.error(request, 'Você não tem permissão para alterar métodos de pagamento.')
                return redirect('payment_method_list')

            method_id = request.POST.get('payment_method_id')
            payment_method = models.PaymentMethod.objects.filter(pk=method_id).first()

            if not payment_method:
                messages.error(request, 'Método de pagamento não encontrado.')
                return redirect('payment_method_list')

            payment_method.is_active = not payment_method.is_active
            payment_method.save(update_fields=['is_active', 'updated_at'])
            status = 'ativado' if payment_method.is_active else 'desativado'
            messages.success(request, f'Método "{payment_method.name}" {status} com sucesso.')
            return redirect('payment_method_list')

        if not request.user.has_perm('outflows.add_paymentmethod'):
            messages.error(request, 'Você não tem permissão para cadastrar métodos de pagamento.')
            return redirect('payment_method_list')

        form = forms.PaymentMethodForm(request.POST)
        payment_methods = models.PaymentMethod.objects.all()

        if form.is_valid():
            payment_method = form.save()
            messages.success(request, f'Método "{payment_method.name}" cadastrado com sucesso.')
            return redirect('payment_method_list')

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


class OutflowDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Outflow
    template_name = 'outflow_detail.html'
    permission_required = 'outflows.view_outflow'

    def get_queryset(self):
        return super().get_queryset().select_related('customer', 'payment_method').prefetch_related(
            Prefetch(
                'items',
                queryset=models.OutflowItem.objects.select_related('product__brand', 'product__category'),
            ),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = list(self.object.items.all())
        context['total_items'] = self.object.total_items
        context['total_amount'] = self.object.total_amount
        context['discount_amount'] = self.object.payment_discount_amount
        context['final_amount'] = self.object.final_amount
        context['total_cost'] = self.object.total_cost
        context['total_profit'] = self.object.total_profit
        return context


class OutflowReturnLandingView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'outflow_returns.html'
    permission_required = 'outflows.view_outflow'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'section_title': 'Trocas e Devoluções',
                'section_description': 'Gerencie solicitações de troca e devolução vinculadas às vendas.',
            },
        )
        return context


class OutflowCreateListAPIView(generics.ListCreateAPIView):
    queryset = models.Outflow.objects.all().prefetch_related('items__product').select_related('customer', 'payment_method')
    serializer_class = serializers.OutflowSerializer


class OutflowRetrieveAPIView(generics.RetrieveAPIView):
    queryset = models.Outflow.objects.all().prefetch_related('items__product').select_related('customer', 'payment_method')
    serializer_class = serializers.OutflowSerializer
