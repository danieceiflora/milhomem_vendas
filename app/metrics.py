"""
Módulo de métricas do sistema.

Funções disponíveis:
- get_product_metrics(): Métricas de produtos em estoque
- get_sales_metrics(): Métricas de vendas do PDV (app pos)
- get_daily_sales_data(): Gráfico de valor de vendas dos últimos 7 dias
- get_daily_sales_quantity_data(): Gráfico de quantidade vendida dos últimos 7 dias
- get_graphic_product_category_metric(): Distribuição de produtos por categoria
- get_graphic_product_brand_metric(): Distribuição de produtos por marca

Nota: As métricas de vendas utilizam apenas o app 'pos' (PDV).
      O app 'outflows' é usado exclusivamente para saídas não faturadas (perdas).
"""
from decimal import Decimal
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Count
from django.utils.formats import number_format
from django.utils import timezone
from brands.models import Brand
from categories.models import Category
from products.models import Product
from pos.models import Sale, SaleItem, SalePayment


TWO_PLACES = Decimal('0.01')


def get_product_metrics():
    products = Product.objects.all()
    total_cost_price = sum(product.cost_price * product.quantity for product in products)
    total_selling_price = sum(product.selling_price * product.quantity for product in products)
    total_quantity = sum(product.quantity for product in products)
    total_profit = total_selling_price - total_cost_price

    return dict(
        total_cost_price=number_format(total_cost_price, decimal_pos=2, force_grouping=True),
        total_selling_price=number_format(total_selling_price, decimal_pos=2, force_grouping=True),
        total_quantity=total_quantity,
        total_profit=number_format(total_profit, decimal_pos=2, force_grouping=True),
    )


def get_sales_metrics():
    """Métricas de vendas do PDV (app pos)."""
    sales = Sale.objects.filter(status=Sale.Status.FINALIZED).prefetch_related('items', 'payments')

    total_sales = sales.count()
    total_products_sold = 0
    gross_total = Decimal('0')
    final_total = Decimal('0')
    profit_total = Decimal('0')

    for sale in sales:
        # Soma quantidade de produtos vendidos
        total_products_sold += sale.items_count
        
        # Soma valores
        gross_total += sale.subtotal
        final_total += sale.total
        
        # Calcula lucro (preço - custo) * quantidade
        for item in sale.items.all():
            profit_total += item.profit

    return dict(
        total_sales=total_sales,
        total_products_sold=total_products_sold,
        total_sales_value=number_format(gross_total, decimal_pos=2, force_grouping=True),
        total_sales_final_value=number_format(final_total, decimal_pos=2, force_grouping=True),
        total_sales_profit=number_format(profit_total, decimal_pos=2, force_grouping=True),
    )


def get_daily_sales_data():
    """Dados de vendas diárias (valor em R$) dos últimos 7 dias - PDV."""
    today = timezone.now().date()
    dates = [str(today - timezone.timedelta(days=i)) for i in range(6, -1, -1)]
    values = list()

    for date in dates:
        # Soma o total de vendas finalizadas neste dia
        sales_total = Sale.objects.filter(
            status=Sale.Status.FINALIZED,
            finalized_at__date=date
        ).aggregate(
            total_sales=Sum('total')
        )['total_sales'] or Decimal('0')
        values.append(float(sales_total))

    return dict(
        dates=dates,
        values=values,
    )


def get_daily_sales_quantity_data():
    """Dados de quantidade vendida por dia dos últimos 7 dias - PDV."""
    today = timezone.now().date()
    dates = [str(today - timezone.timedelta(days=i)) for i in range(6, -1, -1)]
    quantities = list()

    for date in dates:
        # Soma a quantidade de itens vendidos neste dia
        sales_quantity = SaleItem.objects.filter(
            sale__status=Sale.Status.FINALIZED,
            sale__finalized_at__date=date
        ).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        quantities.append(sales_quantity)

    return dict(
        dates=dates,
        values=quantities,
    )


def get_graphic_product_category_metric():
    categories = Category.objects.all()
    return {category.name: Product.objects.filter(category=category).count() for category in categories}


def get_graphic_product_brand_metric():
    brands = Brand.objects.all()
    return {brand.name: Product.objects.filter(brand=brand).count() for brand in brands}
