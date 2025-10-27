from django.contrib import admin
from . import models


class OutflowItemInline(admin.TabularInline):
    model = models.OutflowItem
    extra = 0
    readonly_fields = ('unit_price', 'unit_cost')


@admin.register(models.Outflow)
class OutflowAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'total_items', 'total_amount', 'created_at')
    list_filter = ('created_at', 'customer')
    search_fields = ('customer__full_name', 'items__product__title')
    inlines = [OutflowItemInline]


@admin.register(models.OutflowItem)
class OutflowItemAdmin(admin.ModelAdmin):
    list_display = ('outflow', 'product', 'quantity', 'unit_price', 'created_at')
    list_filter = ('product',)
    search_fields = ('product__title', 'outflow__customer__full_name')
