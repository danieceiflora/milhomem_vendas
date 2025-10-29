from collections import defaultdict
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory
from . import models


class OutflowForm(forms.ModelForm):
    class Meta:
        model = models.Outflow
        fields = ['customer', 'payment_method', 'description']
        widgets = {
            'customer': forms.HiddenInput(),
            'payment_method': forms.Select(attrs={
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
            'payment_method': 'Forma de pagamento',
            'description': 'Observações',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].queryset = models.PaymentMethod.objects.filter(is_active=True)
        self.fields['payment_method'].required = True
        self.fields['payment_method'].widget.attrs.update({'data-role': 'payment-method-select'})

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        if not payment_method:
            self.add_error('payment_method', 'Selecione uma forma de pagamento.')
        return cleaned_data


class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = models.PaymentMethod
        fields = ['name', 'description', 'discount_percentage', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'Ex.: Cartão de crédito',
            }),
            'description': forms.Textarea(attrs={
                'class': 'flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'rows': 3,
                'placeholder': 'Detalhes adicionais sobre o método.',
            }),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border border-input text-primary focus:ring-primary',
            }),
        }
        labels = {
            'name': 'Nome do método',
            'description': 'Descrição',
            'discount_percentage': 'Percentual de desconto (%)',
            'is_active': 'Ativo',
        }

    def clean_discount_percentage(self):
        value = self.cleaned_data.get('discount_percentage')
        if value is None:
            return Decimal('0')
        if value < 0:
            raise ValidationError('Informe um percentual maior ou igual a zero.')
        if value > 100:
            raise ValidationError('O percentual não pode ultrapassar 100%.')
        return value


class OutflowItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit_price'].required = False

    class Meta:
        model = models.OutflowItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.HiddenInput(),
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
    require_items = True

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

        if self.require_items and not has_item:
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
