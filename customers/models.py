from django.core.validators import RegexValidator
from django.db import models


class Customer(models.Model):
    full_name = models.CharField('Nome completo', max_length=255)
    date_of_birth = models.DateField('Data de nascimento')
    phone = models.CharField('Telefone', max_length=20, blank=True)
    email = models.EmailField('E-mail', unique=True)
    address = models.TextField('Endereço', blank=True)
    cpf = models.CharField(
        'CPF',
        max_length=14,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})$',
                message='Informe um CPF válido no formato 000.000.000-00 ou apenas números.'
            )
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self) -> str:
        return self.full_name

    @property
    def formatted_cpf(self) -> str:
        numbers = ''.join(filter(str.isdigit, self.cpf))
        if len(numbers) != 11:
            return self.cpf
        return f'{numbers[:3]}.{numbers[3:6]}.{numbers[6:9]}-{numbers[9:]}'
