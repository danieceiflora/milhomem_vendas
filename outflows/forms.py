from collections import defaultdict
from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory
from . import models


class OutflowForm(forms.ModelForm):
    class Meta:
        model = models.Outflow
        fields = ['customer', 'description']
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
            }),
            'description': forms.Textarea(attrs={
                'class': 'flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'rows': 3,
            }),
        }
        labels = {
            'customer': 'Cliente',
            'description': 'Observações',
        }


class OutflowItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit_price'].required = False

    class Meta:
        model = models.OutflowItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'min': 1,
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Deixe em branco para usar o preço do produto',
            }),
        }
        labels = {
            'product': 'Produto',
            'quantity': 'Quantidade',
            'unit_price': 'Preço unitário (R$)',
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
            unit_price = cleaned_data.get('unit_price')

            if not product and not quantity:
                continue

            has_item = True

            if not product:
                form.add_error('product', 'Selecione um produto.')
                continue

            if not quantity or quantity <= 0:
                form.add_error('quantity', 'Informe uma quantidade maior que zero.')
                continue

            if unit_price is not None and unit_price < 0:
                form.add_error('unit_price', 'Informe um preço maior ou igual a zero.')
                continue

            totals_by_product[product] += quantity

        if not has_item:
            raise ValidationError('Adicione ao menos um produto à venda.')

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
