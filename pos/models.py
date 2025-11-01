from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from customers.models import Customer
from products.models import Product
from outflows.models import PaymentMethod


TWO_PLACES = Decimal('0.01')


class Sale(models.Model):
    """Venda realizada no PDV com suporte a múltiplos pagamentos."""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        FINALIZED = 'finalized', 'Finalizada'
        CANCELLED = 'cancelled', 'Cancelada'
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='pos_sales',
        verbose_name='Cliente'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='pos_sales',
        verbose_name='Vendedor'
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    session_key = models.CharField(
        'Chave de sessão',
        max_length=40,
        blank=True,
        help_text='Chave da sessão para identificar vendas em rascunho'
    )
    
    # Valores calculados
    subtotal = models.DecimalField(
        'Subtotal',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    discount_total = models.DecimalField(
        'Desconto total',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Desconto aplicado manualmente ou por diferença'
    )
    total = models.DecimalField(
        'Total',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    total_paid = models.DecimalField(
        'Total pago',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Metadados
    notes = models.TextField('Observações', blank=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    finalized_at = models.DateTimeField('Finalizado em', null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Venda PDV'
        verbose_name_plural = 'Vendas PDV'
        indexes = [
            models.Index(fields=['status', 'user', 'session_key']),
            models.Index(fields=['customer', 'status']),
        ]
    
    def __str__(self) -> str:
        return f'Venda #{self.pk} - {self.customer.full_name} - {self.get_status_display()}'
    
    @property
    def items_count(self) -> int:
        """Retorna a quantidade total de itens na venda."""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def change_total(self) -> Decimal:
        """Retorna o troco total dado em todos os pagamentos."""
        return self.payments.aggregate(
            total=models.Sum('change_given')
        )['total'] or Decimal('0')
    
    @property
    def remaining(self) -> Decimal:
        """Retorna o valor restante a pagar."""
        return max(Decimal('0'), self.total - self.total_paid)
    
    @property
    def overpaid(self) -> Decimal:
        """Retorna o valor pago a mais (excluindo troco já calculado)."""
        return max(Decimal('0'), self.total_paid - self.total)


class SaleItem(models.Model):
    """Item de uma venda no PDV."""
    
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Venda'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='pos_sale_items',
        verbose_name='Produto'
    )
    quantity = models.PositiveIntegerField(
        'Quantidade',
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        'Preço unitário',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    line_total = models.DecimalField(
        'Total do item',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Snapshot do custo para cálculo de lucro
    unit_cost = models.DecimalField(
        'Custo unitário',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Item da venda'
        verbose_name_plural = 'Itens da venda'
    
    def __str__(self) -> str:
        return f'{self.product.title} x{self.quantity}'
    
    def save(self, *args, **kwargs):
        """Calcula o total da linha antes de salvar."""
        self.line_total = (Decimal(str(self.quantity)) * self.unit_price).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        super().save(*args, **kwargs)
    
    @property
    def profit(self) -> Decimal:
        """Retorna o lucro deste item."""
        return (self.unit_price - self.unit_cost) * Decimal(str(self.quantity))


class SalePayment(models.Model):
    """Pagamento realizado em uma venda (suporta múltiplos pagamentos)."""
    
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Venda'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='pos_payments',
        verbose_name='Método de pagamento'
    )
    
    # Valor efetivamente aplicado no pagamento
    amount_applied = models.DecimalField(
        'Valor aplicado',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Valor que foi efetivamente usado no pagamento'
    )
    
    # Campos específicos para dinheiro
    cash_tendered = models.DecimalField(
        'Valor recebido',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Valor entregue pelo cliente (apenas para dinheiro)'
    )
    change_given = models.DecimalField(
        'Troco',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Troco devolvido ao cliente (apenas para dinheiro)'
    )
    
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
    
    def __str__(self) -> str:
        return f'{self.payment_method.name} - {self.amount_applied}'


class LedgerEntry(models.Model):
    """Lançamento de crédito ou débito de cliente."""
    
    class Type(models.TextChoices):
        CREDIT = 'credit', 'Crédito'
        DEBIT = 'debit', 'Débito'
    
    class Status(models.TextChoices):
        OPEN = 'open', 'Em aberto'
        SETTLED = 'settled', 'Liquidado'
        CANCELLED = 'cancelled', 'Cancelado'
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='ledger_entries',
        verbose_name='Cliente'
    )
    sale = models.ForeignKey(
        Sale,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ledger_entries',
        verbose_name='Venda relacionada'
    )
    type = models.CharField(
        'Tipo',
        max_length=10,
        choices=Type.choices
    )
    status = models.CharField(
        'Status',
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN
    )
    amount = models.DecimalField(
        'Valor',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    description = models.TextField(
        'Descrição',
        blank=True,
        help_text='Descrição do lançamento'
    )
    
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    settled_at = models.DateTimeField('Liquidado em', null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Lançamento'
        verbose_name_plural = 'Lançamentos'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['type', 'status']),
        ]
    
    def __str__(self) -> str:
        return f'{self.get_type_display()} - {self.customer.full_name} - R$ {self.amount}'
