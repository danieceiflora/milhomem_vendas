from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView
from rest_framework import generics
from app import metrics
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

        queryset = queryset.select_related('customer').prefetch_related(
            Prefetch(
                'items',
                queryset=models.OutflowItem.objects.select_related('product__brand', 'product__category'),
            )
        ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        outflows = context['outflows']

        for outflow in outflows:
            items = list(outflow.items.all())
            outflow.computed_total_items = sum(item.quantity for item in items)
            outflow.computed_total_amount = sum((item.quantity * item.unit_price for item in items), Decimal('0'))

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
        formset = forms.OutflowItemFormSet(prefix='items')
        return self._render(request, form, formset)

    def post(self, request, *args, **kwargs):
        form = forms.OutflowForm(request.POST)
        formset = forms.OutflowItemFormSet(request.POST, prefix='items')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    outflow = form.save()
                    self._save_items(formset, outflow)
            except ValidationError as error:
                for message in getattr(error, 'messages', [str(error)]):
                    form.add_error(None, message)
                transaction.set_rollback(True)
            else:
                messages.success(request, 'Venda registrada com sucesso.')
                return redirect(self.success_url)

        return self._render(request, form, formset)

    def _save_items(self, formset, outflow):
        saved = False

        for form in formset.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
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
            raise ValidationError('Adicione ao menos um produto válido à venda.')

    def _render(self, request, form, formset):
        return render(request, self.template_name, {'form': form, 'formset': formset})


class OutflowDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Outflow
    template_name = 'outflow_detail.html'
    permission_required = 'outflows.view_outflow'

    def get_queryset(self):
        return super().get_queryset().select_related('customer').prefetch_related(
            Prefetch(
                'items',
                queryset=models.OutflowItem.objects.select_related('product__brand', 'product__category'),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = list(self.object.items.all())
        context['items'] = items
        context['total_items'] = sum(item.quantity for item in items)
        context['total_amount'] = sum((item.quantity * item.unit_price for item in items), Decimal('0'))
        context['total_cost'] = sum((item.quantity * item.unit_cost for item in items), Decimal('0'))
        context['total_profit'] = context['total_amount'] - context['total_cost']
        return context


class OutflowCreateListAPIView(generics.ListCreateAPIView):
    queryset = models.Outflow.objects.all().prefetch_related('items__product').select_related('customer')
    serializer_class = serializers.OutflowSerializer


class OutflowRetrieveAPIView(generics.RetrieveAPIView):
    queryset = models.Outflow.objects.all().prefetch_related('items__product').select_related('customer')
    serializer_class = serializers.OutflowSerializer
