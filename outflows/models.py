from decimal import Decimal
from django.db import models
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from customers.models import Customer
from products.models import Product


class Outflow(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='outflows')
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Venda #{self.pk} - {self.customer.full_name}'

    @property
    def total_items(self) -> int:
        result = self.items.aggregate(total=Sum('quantity'))['total']
        return result or 0

    @property
    def total_amount(self) -> Decimal:
        value_expr = ExpressionWrapper(
            F('quantity') * F('unit_price'),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        result = self.items.aggregate(total=Sum(value_expr))['total']
        return result or Decimal('0')

    @property
    def total_cost(self) -> Decimal:
        cost_expr = ExpressionWrapper(
            F('quantity') * F('unit_cost'),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        result = self.items.aggregate(total=Sum(cost_expr))['total']
        return result or Decimal('0')

    @property
    def total_profit(self) -> Decimal:
        return self.total_amount - self.total_cost


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
