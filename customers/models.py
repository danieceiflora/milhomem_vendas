from django.core.validators import RegexValidator
from django.db import models


class Customer(models.Model):
    # Campos obrigatórios
    full_name = models.CharField('Nome completo', max_length=255)
    phone = models.CharField(
        'Telefone',
        max_length=15,  # Permite máscara (00) 00000-0000
        unique=True,
        help_text='Telefone com DDD (apenas números)'
    )
    
    # Campos opcionais
    date_of_birth = models.DateField('Data de nascimento', blank=True, null=True)
    email = models.EmailField('E-mail', blank=True)
    cpf = models.CharField(
        'CPF',
        max_length=14,  # Permite máscara 000.000.000-00
        blank=True,
        help_text='CPF (apenas números)'
    )
    
    # Campos de endereço
    zip_code = models.CharField('CEP', max_length=9, blank=True)
    street = models.CharField('Logradouro', max_length=255, blank=True)
    number = models.CharField('Número', max_length=20, blank=True)
    complement = models.CharField('Complemento', max_length=100, blank=True)
    neighborhood = models.CharField('Bairro', max_length=100, blank=True)
    city = models.CharField('Cidade', max_length=100, blank=True)
    state = models.CharField('Estado', max_length=2, blank=True)
    
    # Campos de controle
    
    # Campos de controle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self) -> str:
        return f'{self.full_name} - {self.phone}'

    @property
    def formatted_cpf(self) -> str:
        if not self.cpf:
            return ''
        numbers = ''.join(filter(str.isdigit, self.cpf))
        if len(numbers) != 11:
            return self.cpf
        return f'{numbers[:3]}.{numbers[3:6]}.{numbers[6:9]}-{numbers[9:]}'
    
    @property
    def formatted_phone(self) -> str:
        if not self.phone:
            return ''
        numbers = ''.join(filter(str.isdigit, self.phone))
        if len(numbers) == 11:
            return f'({numbers[:2]}) {numbers[2:7]}-{numbers[7:]}'
        elif len(numbers) == 10:
            return f'({numbers[:2]}) {numbers[2:6]}-{numbers[6:]}'
        return self.phone
    
    @property
    def full_address(self) -> str:
        parts = []
        if self.street:
            parts.append(self.street)
        if self.number:
            parts.append(f'nº {self.number}')
        if self.complement:
            parts.append(self.complement)
        if self.neighborhood:
            parts.append(self.neighborhood)
        if self.city and self.state:
            parts.append(f'{self.city}/{self.state}')
        if self.zip_code:
            parts.append(f'CEP: {self.zip_code}')
        return ', '.join(parts) if parts else ''
