from django import forms
from django.core.exceptions import ValidationError
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['full_name', 'date_of_birth', 'phone', 'email', 'address', 'cpf']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'type': 'date',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'type': 'tel',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
            }),
            'address': forms.Textarea(attrs={
                'class': 'flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'rows': 3,
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
            }),
        }
        labels = {
            'full_name': 'Nome completo',
            'date_of_birth': 'Data de nascimento',
            'phone': 'Telefone',
            'email': 'E-mail',
            'address': 'Endereço',
            'cpf': 'CPF',
        }

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '').strip()
        numbers = ''.join(filter(str.isdigit, cpf))

        if len(numbers) != 11:
            raise ValidationError('O CPF deve conter 11 dígitos.')

        return f'{numbers[:3]}.{numbers[3:6]}.{numbers[6:9]}-{numbers[9:]}'
