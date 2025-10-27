from decimal import Decimal
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.utils.formats import number_format
from django.utils import timezone
from brands.models import Brand
from categories.models import Category
from products.models import Product
from outflows.models import Outflow, OutflowItem


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
    total_sales = Outflow.objects.count()
    items_qs = OutflowItem.objects.all()

    total_products_sold = items_qs.aggregate(total=Sum('quantity'))['total'] or 0

    value_expr = ExpressionWrapper(
        F('quantity') * F('unit_price'),
        output_field=DecimalField(max_digits=20, decimal_places=2),
    )
    cost_expr = ExpressionWrapper(
        F('quantity') * F('unit_cost'),
        output_field=DecimalField(max_digits=20, decimal_places=2),
    )

    total_sales_value = items_qs.aggregate(total=Sum(value_expr))['total'] or Decimal('0')
    total_sales_cost = items_qs.aggregate(total=Sum(cost_expr))['total'] or Decimal('0')
    total_sales_profit = total_sales_value - total_sales_cost

    return dict(
        total_sales=total_sales,
        total_products_sold=total_products_sold,
        total_sales_value=number_format(total_sales_value, decimal_pos=2, force_grouping=True),
        total_sales_profit=number_format(total_sales_profit, decimal_pos=2, force_grouping=True),
    )


def get_daily_sales_data():
    today = timezone.now().date()
    dates = [str(today - timezone.timedelta(days=i)) for i in range(6, -1, -1)]
    values = list()

    value_expr = ExpressionWrapper(
        F('quantity') * F('unit_price'),
        output_field=DecimalField(max_digits=20, decimal_places=2),
    )

    for date in dates:
        sales_total = OutflowItem.objects.filter(
            outflow__created_at__date=date
        ).aggregate(
            total_sales=Sum(value_expr)
        )['total_sales'] or Decimal('0')
        values.append(float(sales_total))

    return dict(
        dates=dates,
        values=values,
    )


def get_daily_sales_quantity_data():
    today = timezone.now().date()
    dates = [str(today - timezone.timedelta(days=i)) for i in range(6, -1, -1)]
    quantities = list()

    for date in dates:
        sales_quantity = OutflowItem.objects.filter(outflow__created_at__date=date).aggregate(total=Sum('quantity'))['total'] or 0
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
