from django import forms
from django.core.exceptions import ValidationError
from .models import Customer


class CustomerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se estamos editando (instance existe e tem dados salvos), formata os campos
        if self.instance and self.instance.pk:
            # Formata CPF com máscara para exibição
            if self.instance.cpf:
                cpf = self.instance.cpf
                if len(cpf) == 11:
                    self.initial['cpf'] = f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'
            
            # Formata Telefone com máscara para exibição
            if self.instance.phone:
                phone = self.instance.phone
                if len(phone) == 11:
                    self.initial['phone'] = f'({phone[:2]}) {phone[2:7]}-{phone[7:]}'
                elif len(phone) == 10:
                    self.initial['phone'] = f'({phone[:2]}) {phone[2:6]}-{phone[6:]}'
    
    class Meta:
        model = Customer
        fields = [
            'full_name', 'phone', 'date_of_birth', 'email', 'cpf',
            'zip_code', 'street', 'number', 'complement', 'neighborhood', 'city', 'state'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'Nome completo do cliente',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'type': 'tel',
                'placeholder': '(00) 00000-0000',
                'maxlength': '15',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'type': 'date',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'email@exemplo.com',
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': '000.000.000-00',
                'maxlength': '14',
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': '00000-000',
                'id': 'id_zip_code',
            }),
            'street': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'Rua, Avenida, etc.',
                'id': 'id_street',
            }),
            'number': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'Número',
                'id': 'id_number',
            }),
            'complement': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'Apartamento, bloco, etc. (opcional)',
                'id': 'id_complement',
            }),
            'neighborhood': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'Bairro',
                'id': 'id_neighborhood',
            }),
            'city': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'Cidade',
                'id': 'id_city',
            }),
            'state': forms.TextInput(attrs={
                'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background '
                         'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 '
                         'focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                'placeholder': 'UF',
                'maxlength': '2',
                'id': 'id_state',
            }),
        }
        labels = {
            'full_name': 'Nome completo *',
            'phone': 'Telefone *',
            'date_of_birth': 'Data de nascimento',
            'email': 'E-mail',
            'cpf': 'CPF',
            'zip_code': 'CEP',
            'street': 'Logradouro',
            'number': 'Número',
            'complement': 'Complemento',
            'neighborhood': 'Bairro',
            'city': 'Cidade',
            'state': 'Estado',
        }

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '').strip()
        if not cpf:
            return ''
        
        # Remove máscara
        numbers = ''.join(filter(str.isdigit, cpf))
        
        if len(numbers) != 11:
            raise ValidationError('O CPF deve conter 11 dígitos.')
        
        # Validação de CPFs inválidos conhecidos
        if numbers == numbers[0] * 11:
            raise ValidationError('CPF inválido.')
        
        # Validação dos dígitos verificadores
        def calculate_digit(cpf_partial):
            total = sum(int(digit) * weight for digit, weight in zip(cpf_partial, range(len(cpf_partial) + 1, 1, -1)))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder
        
        first_digit = calculate_digit(numbers[:9])
        second_digit = calculate_digit(numbers[:10])
        
        if numbers[9:11] != f'{first_digit}{second_digit}':
            raise ValidationError('CPF inválido.')
        
        # Verifica se já existe outro cliente com este CPF
        from .models import Customer
        existing = Customer.objects.filter(cpf=numbers)
        
        # Se estamos editando, exclui o próprio registro da verificação
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise ValidationError('Já existe um cliente cadastrado com este CPF.')
        
        # Retorna apenas os números (sem máscara)
        return numbers
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise ValidationError('O telefone é obrigatório.')
        
        # Remove máscara
        numbers = ''.join(filter(str.isdigit, phone))
        
        if len(numbers) < 10 or len(numbers) > 11:
            raise ValidationError('Informe um telefone válido com DDD.')
        
        # Validação básica de DDD
        ddd = int(numbers[:2])
        valid_ddds = [
            11, 12, 13, 14, 15, 16, 17, 18, 19,  # SP
            21, 22, 24,  # RJ
            27, 28,  # ES
            31, 32, 33, 34, 35, 37, 38,  # MG
            41, 42, 43, 44, 45, 46,  # PR
            47, 48, 49,  # SC
            51, 53, 54, 55,  # RS
            61,  # DF
            62, 64,  # GO
            63,  # TO
            65, 66,  # MT
            67,  # MS
            68,  # AC
            69,  # RO
            71, 73, 74, 75, 77,  # BA
            79,  # SE
            81, 87,  # PE
            82,  # AL
            83,  # PB
            84,  # RN
            85, 88,  # CE
            86, 89,  # PI
            91, 93, 94,  # PA
            92, 97,  # AM
            95,  # RR
            96,  # AP
            98, 99,  # MA
        ]
        
        if ddd not in valid_ddds:
            raise ValidationError('DDD inválido.')
        
        # Retorna apenas os números (sem máscara)
        return numbers
    
    def clean_zip_code(self):
        zip_code = self.cleaned_data.get('zip_code', '').strip()
        if not zip_code:
            return ''
        
        # Remove máscara
        numbers = ''.join(filter(str.isdigit, zip_code))
        if len(numbers) != 8:
            raise ValidationError('O CEP deve conter 8 dígitos.')
        
        # Retorna com máscara para exibição
        return f'{numbers[:5]}-{numbers[5:]}'
    
    def clean_state(self):
        state = self.cleaned_data.get('state', '').strip().upper()
        return state[:2] if state else ''
