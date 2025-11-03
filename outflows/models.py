from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from customers.models import Customer
from products.models import Product


TWO_PLACES = Decimal('0.01')


class Outflow(models.Model):
    """
    Modelo para registrar saídas de produtos não faturadas.
    Usado para: vencimento, doações, avarias, defeitos, uso próprio, etc.
    """
    class OutflowType(models.TextChoices):
        EXPIRATION = 'expiration', 'Vencimento'
        GIFT = 'gift', 'Presente/Doação'
        DAMAGE = 'damage', 'Avaria/Quebra'
        DEFECT = 'defect', 'Defeito de Fabricação'
        PERSONAL_USE = 'personal_use', 'Uso Próprio'
        LOSS = 'loss', 'Perda/Extravio'
        SAMPLE = 'sample', 'Amostra Grátis'
        OTHER = 'other', 'Outros'

    outflow_type = models.CharField(
        max_length=20,
        choices=OutflowType.choices,
        verbose_name='Tipo de Saída'
    )
    description = models.TextField(
        verbose_name='Descrição/Motivo',
        help_text='Descreva o motivo da saída'
    )
    recipient = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Destinatário',
        help_text='Pessoa ou entidade que recebeu (se aplicável)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última Atualização')
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='outflows_created',
        null=True,
        blank=True,
        verbose_name='Criado por'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Saída Não Faturada'
        verbose_name_plural = 'Saídas Não Faturadas'

    def __str__(self) -> str:
        return f'{self.get_outflow_type_display()} #{self.pk} - {self.created_at.strftime("%d/%m/%Y")}'

    @property
    def total_items(self) -> int:
        """Total de itens na saída"""
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def total_cost(self) -> Decimal:
        """Custo total dos produtos que saíram"""
        expr = ExpressionWrapper(
            F('quantity') * F('unit_cost'),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        return self.items.aggregate(total=Sum(expr))['total'] or Decimal('0')

    @property
    def total_value(self) -> Decimal:
        """Valor de venda total (referência)"""
        expr = ExpressionWrapper(
            F('quantity') * F('unit_price'),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        return self.items.aggregate(total=Sum(expr))['total'] or Decimal('0')
    
    @property
    def impact_amount(self) -> Decimal:
        """Valor do impacto financeiro (prejuízo)"""
        return self.total_cost


class OutflowItem(models.Model):
    """Item de uma saída não faturada"""
    outflow = models.ForeignKey(
        Outflow,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Saída'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='outflow_items',
        verbose_name='Produto'
    )
    quantity = models.PositiveIntegerField(verbose_name='Quantidade')
    unit_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Preço Unitário',
        help_text='Preço de venda de referência'
    )
    unit_cost = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Custo Unitário'
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name='Observações',
        help_text='Detalhes específicos deste item'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última Atualização')

    class Meta:
        ordering = ['id']
        verbose_name = 'Item de Saída'
        verbose_name_plural = 'Itens de Saída'

    def __str__(self) -> str:
        return f'{self.product} ({self.quantity})'

    @property
    def total_cost(self) -> Decimal:
        """Custo total do item"""
        return self.quantity * self.unit_cost

    @property
    def total_value(self) -> Decimal:
        """Valor de venda total (referência)"""
        return self.quantity * self.unit_price
    
    @property
    def impact(self) -> Decimal:
        """Impacto financeiro (prejuízo)"""
        return self.total_cost


# Remove OutflowReturnItem (não usado em saídas não faturadas)
