from collections import defaultdict
from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory
from . import models


class OutflowForm(forms.ModelForm):
    class Meta:
        model = models.Outflow
        fields = ['outflow_type', 'description', 'recipient']
        widgets = {
            'outflow_type': forms.Select(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
            }),
            'description': forms.Textarea(attrs={
                'class': 'flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'rows': 3,
                'placeholder': 'Descreva o motivo da saída e detalhes relevantes...',
            }),
            'recipient': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'Nome da pessoa ou entidade (opcional)',
            }),
        }
        labels = {
            'outflow_type': 'Tipo de Saída',
            'description': 'Descrição',
            'recipient': 'Destinatário',
        }
        help_texts = {
            'outflow_type': 'Selecione o motivo da saída não faturada',
            'description': 'Explique o motivo e circunstâncias da saída',
            'recipient': 'Quem recebeu os produtos (se aplicável)',
        }

    def clean(self):
        cleaned_data = super().clean()
        outflow_type = cleaned_data.get('outflow_type')
        description = cleaned_data.get('description')
        
        if not outflow_type:
            self.add_error('outflow_type', 'Selecione o tipo de saída.')
        
        if not description or len(description.strip()) < 10:
            self.add_error('description', 'A descrição deve ter pelo menos 10 caracteres.')
        
        return cleaned_data


class OutflowItemForm(forms.ModelForm):
    class Meta:
        model = models.OutflowItem
        fields = ['product', 'quantity', 'notes']
        widgets = {
            'product': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'min': 1,
            }),
            'notes': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'Observações específicas deste item (opcional)',
            }),
        }
        labels = {
            'product': 'Produto',
            'quantity': 'Quantidade',
            'notes': 'Observações',
        }


class BaseOutflowItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        totals_by_product = defaultdict(int)
        has_item = False

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue

            cleaned_data = form.cleaned_data

            if cleaned_data.get('DELETE'):
                continue

            product = cleaned_data.get('product')
            quantity = cleaned_data.get('quantity')

            if not product and not quantity:
                continue

            has_item = True

            if not product:
                form.add_error('product', 'Selecione um produto.')
                continue

            if not quantity or quantity <= 0:
                form.add_error('quantity', 'Informe uma quantidade maior que zero.')
                continue

            totals_by_product[product] += quantity

        if not has_item:
            raise ValidationError('Adicione ao menos um produto à saída.')

        for product, total in totals_by_product.items():
            if total > product.quantity:
                raise ValidationError(
                    f'Estoque insuficiente para o produto {product}. Disponível: {product.quantity} unidade(s).'
                )


OutflowItemFormSet = inlineformset_factory(
    parent_model=models.Outflow,
    model=models.OutflowItem,
    form=OutflowItemForm,
    formset=BaseOutflowItemFormSet,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
