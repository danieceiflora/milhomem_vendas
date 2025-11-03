from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView
from rest_framework import generics
from . import forms, models, serializers


class OutflowListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Outflow
    template_name = 'outflow_list.html'
    context_object_name = 'outflows'
    paginate_by = 15
    permission_required = 'outflows.view_outflow'

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        product = self.request.GET.get('product')
        outflow_type = self.request.GET.get('outflow_type')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if product:
            queryset = queryset.filter(items__product__title__icontains=product)
        
        if outflow_type:
            queryset = queryset.filter(outflow_type=outflow_type)
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        queryset = queryset.select_related('created_by').prefetch_related(
            Prefetch(
                'items',
                queryset=models.OutflowItem.objects.select_related('product__brand', 'product__category'),
            ),
        ).distinct().order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adicionar totais computados para cada saída
        outflows = context['outflows']
        for outflow in outflows:
            outflow.computed_total_items = outflow.total_items
            outflow.computed_total_cost = outflow.total_cost
            outflow.computed_total_value = outflow.total_value
            outflow.computed_impact_amount = outflow.impact_amount

        # Adicionar opções de filtro
        context['outflow_types'] = models.Outflow.OutflowType.choices
        context['filter_product'] = self.request.GET.get('product', '')
        context['filter_outflow_type'] = self.request.GET.get('outflow_type', '')
        context['filter_date_from'] = self.request.GET.get('date_from', '')
        context['filter_date_to'] = self.request.GET.get('date_to', '')
        
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
                    outflow.created_by = request.user
                    outflow.save()

                    items_formset.instance = outflow
                    self._save_items(items_formset, outflow)
            except ValidationError as error:
                for message in getattr(error, 'messages', [str(error)]):
                    form.add_error(None, message)
                transaction.set_rollback(True)
            else:
                messages.success(request, self._get_success_message(outflow))
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
                raise ValidationError('Não foi possível registrar a saída por falta de estoque.')

            # Capturar preços do produto
            item.unit_cost = product.cost_price
            item.unit_price = product.selling_price

            # Reduzir estoque
            product.quantity -= item.quantity
            product.save(update_fields=['quantity'])

            item.outflow = outflow
            item.save()
            saved = True

        if not saved:
            raise ValidationError('Adicione ao menos um produto válido à saída.')

    def _render(self, request, form, items_formset):
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'items_formset': items_formset,
                'outflow_types': models.Outflow.OutflowType.choices,
            },
        )

    def _get_success_message(self, outflow):
        type_label = outflow.get_outflow_type_display()
        return f'Saída não faturada registrada com sucesso ({type_label}).'


class OutflowDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Outflow
    template_name = 'outflow_detail.html'
    permission_required = 'outflows.view_outflow'

    def get_queryset(self):
        return super().get_queryset().select_related('created_by').prefetch_related(
            Prefetch(
                'items',
                queryset=models.OutflowItem.objects.select_related('product__brand', 'product__category'),
            ),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = list(self.object.items.all())
        context['total_items'] = self.object.total_items
        context['total_cost'] = self.object.total_cost
        context['total_value'] = self.object.total_value
        context['impact_amount'] = self.object.impact_amount
        return context


class OutflowCreateListAPIView(generics.ListCreateAPIView):
    queryset = models.Outflow.objects.all().prefetch_related('items__product').select_related('created_by')
    serializer_class = serializers.OutflowSerializer


class OutflowRetrieveAPIView(generics.RetrieveAPIView):
    queryset = models.Outflow.objects.all().prefetch_related('items__product').select_related('created_by')
    serializer_class = serializers.OutflowSerializer
