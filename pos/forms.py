from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from .models import PaymentMethod


class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['name', 'description', 'fee_percentage', 'fee_payer', 'is_active']
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
            'fee_percentage': forms.NumberInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': 'Ex.: 2.50',
            }),
            'fee_payer': forms.Select(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border border-input text-primary focus:ring-primary',
            }),
        }
        labels = {
            'name': 'Nome do método',
            'description': 'Descrição',
            'fee_percentage': 'Percentual (%)',
            'fee_payer': 'Quem paga a taxa?',
            'is_active': 'Ativo',
        }
        help_texts = {
            'fee_percentage': 'Percentual que será aplicado (desconto ou acréscimo)',
            'fee_payer': 'Lojista = desconto no valor final | Cliente = acréscimo no valor final',
        }

    def clean_fee_percentage(self):
        value = self.cleaned_data.get('fee_percentage')
        if value is None:
            return Decimal('0')
        if value < 0:
            raise ValidationError('Informe um percentual maior ou igual a zero.')
        if value > 100:
            raise ValidationError('O percentual não pode ultrapassar 100%.')
        return value
