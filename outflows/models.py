from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from customers.models import Customer
from products.models import Product


TWO_PLACES = Decimal('0.01')


class Outflow(models.Model):
    class OperationType(models.TextChoices):
        SALE = 'sale', 'Venda'
        RETURN = 'return', 'Devolução'
        EXCHANGE = 'exchange', 'Troca'

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='outflows')
    description = models.TextField(null=True, blank=True)
    operation_type = models.CharField(
        max_length=20,
        choices=OperationType.choices,
        default=OperationType.SALE,
    )
    related_outflow = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='child_operations',
    )
    payment_method = models.ForeignKey(
        'outflows.PaymentMethod',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='outflows',
    )
    payment_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    payment_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    final_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.get_operation_type_display()} #{self.pk} - {self.customer.full_name}'

    def _aggregate_items(self, expression: ExpressionWrapper) -> Decimal:
        return self.items.aggregate(total=Sum(expression))['total'] or Decimal('0')

    def _aggregate_return_items(self, expression: ExpressionWrapper) -> Decimal:
        return self.return_items.aggregate(total=Sum(expression))['total'] or Decimal('0')

    @property
    def delivered_items_count(self) -> int:
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def returned_items_count(self) -> int:
        return self.return_items.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def total_items(self) -> int:
        if self.operation_type == self.OperationType.RETURN:
            return -(self.returned_items_count)
        return self.delivered_items_count - self.returned_items_count

    @property
    def delivered_amount(self) -> Decimal:
        expr = ExpressionWrapper(
            F('quantity') * F('unit_price'),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        return self._aggregate_items(expr)

    @property
    def returned_amount(self) -> Decimal:
        expr = ExpressionWrapper(
            F('quantity') * F('unit_price'),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        return self._aggregate_return_items(expr)

    @property
    def delivered_cost(self) -> Decimal:
        expr = ExpressionWrapper(
            F('quantity') * F('unit_cost'),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        return self._aggregate_items(expr)

    @property
    def returned_cost(self) -> Decimal:
        expr = ExpressionWrapper(
            F('quantity') * F('unit_cost'),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        return self._aggregate_return_items(expr)

    @property
    def total_amount(self) -> Decimal:
        if self.operation_type == self.OperationType.RETURN:
            return -(self.returned_amount)
        return self.delivered_amount - self.returned_amount

    @property
    def total_cost(self) -> Decimal:
        if self.operation_type == self.OperationType.RETURN:
            return -(self.returned_cost)
        return self.delivered_cost - self.returned_cost

    @property
    def discount_amount(self) -> Decimal:
        return self.payment_discount_amount

    @property
    def total_profit(self) -> Decimal:
        base_profit = self.total_amount - self.total_cost
        if self.operation_type == self.OperationType.SALE:
            return base_profit - self.discount_amount
        return base_profit

    def refresh_financials(self):
        """Recalcula campos derivados relacionados ao pagamento."""
        if self.operation_type != self.OperationType.SALE or not self.payment_method:
            self.payment_discount_amount = Decimal('0')
            self.final_amount = self.total_amount
            return

        gross_total = self.total_amount
        discount = (self.payment_discount_percentage / Decimal('100')) * gross_total
        discount = discount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        self.payment_discount_amount = discount
        self.final_amount = gross_total - discount


class PaymentMethod(models.Model):
    name = models.CharField('Nome', max_length=100, unique=True)
    description = models.TextField('Descrição', blank=True)
    discount_percentage = models.DecimalField(
        'Percentual de desconto', max_digits=5, decimal_places=2, default=Decimal('0')
    )
    is_active = models.BooleanField('Ativo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Método de pagamento'
        verbose_name_plural = 'Métodos de pagamento'

    def __str__(self) -> str:
        return self.name


class OutflowItem(models.Model):
    outflow = models.ForeignKey(Outflow, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='outflow_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=20, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self) -> str:
        return f'{self.product} ({self.quantity})'

    @property
    def subtotal(self) -> Decimal:
        return self.quantity * self.unit_price

    @property
    def profit(self) -> Decimal:
        return self.quantity * (self.unit_price - self.unit_cost)


class OutflowReturnItem(models.Model):
    outflow = models.ForeignKey(Outflow, on_delete=models.CASCADE, related_name='return_items')
    original_item = models.ForeignKey(
        OutflowItem,
        on_delete=models.PROTECT,
        related_name='return_records',
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='outflow_return_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=20, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Item devolvido'
        verbose_name_plural = 'Itens devolvidos'

    def __str__(self) -> str:
        return f'{self.product} - devolução ({self.quantity})'

    @property
    def subtotal(self) -> Decimal:
        return self.quantity * self.unit_price
