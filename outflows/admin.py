from django.contrib import admin
from . import models


class OutflowItemInline(admin.TabularInline):
    model = models.OutflowItem
    extra = 0
    readonly_fields = ('unit_price', 'unit_cost')


class OutflowReturnItemInline(admin.TabularInline):
    model = models.OutflowReturnItem
    extra = 0
    readonly_fields = ('product', 'unit_price', 'unit_cost')


@admin.register(models.Outflow)
class OutflowAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer',
        'operation_type',
        'payment_method',
        'total_items',
        'final_amount',
        'created_at',
    )
    list_filter = ('operation_type', 'payment_method', 'created_at', 'customer')
    search_fields = ('customer__full_name', 'items__product__title')
    inlines = [OutflowItemInline, OutflowReturnItemInline]


@admin.register(models.OutflowItem)
class OutflowItemAdmin(admin.ModelAdmin):
    list_display = ('outflow', 'product', 'quantity', 'unit_price', 'created_at')
    list_filter = ('product',)
    search_fields = ('product__title', 'outflow__customer__full_name')


@admin.register(models.OutflowReturnItem)
class OutflowReturnItemAdmin(admin.ModelAdmin):
    list_display = ('outflow', 'product', 'quantity', 'unit_price', 'created_at')
    list_filter = ('product',)
    search_fields = ('product__title', 'outflow__customer__full_name')


# PaymentMethod foi movido para pos.models
# Registrado em pos/admin.py
