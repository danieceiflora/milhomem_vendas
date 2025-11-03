from django.contrib import admin
from django.utils.html import format_html
from . import models


class OutflowItemInline(admin.TabularInline):
    model = models.OutflowItem
    extra = 1
    fields = ('product', 'quantity', 'unit_cost', 'unit_price', 'notes')
    autocomplete_fields = ['product']


@admin.register(models.Outflow)
class OutflowAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'outflow_type_badge',
        'description_short',
        'recipient',
        'total_items',
        'impact_badge',
        'created_at',
        'created_by',
    )
    list_filter = ('outflow_type', 'created_at', 'created_by')
    search_fields = ('description', 'recipient', 'items__product__title')
    readonly_fields = ('created_at', 'updated_at', 'total_items', 'total_cost', 'total_value', 'impact_amount')
    inlines = [OutflowItemInline]
    
    fieldsets = (
        ('Informações da Saída', {
            'fields': ('outflow_type', 'description', 'recipient', 'created_by')
        }),
        ('Resumo Financeiro', {
            'fields': ('total_items', 'total_cost', 'total_value', 'impact_amount'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def outflow_type_badge(self, obj):
        colors = {
            'expiration': 'warning',
            'gift': 'info',
            'damage': 'danger',
            'defect': 'danger',
            'personal_use': 'primary',
            'loss': 'danger',
            'sample': 'success',
            'other': 'secondary',
        }
        color = colors.get(obj.outflow_type, 'secondary')
        return format_html(
            '<span style="background-color: var(--{}-fg); color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_outflow_type_display()
        )
    outflow_type_badge.short_description = 'Tipo'
    
    def description_short(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
    description_short.short_description = 'Descrição'
    
    def impact_badge(self, obj):
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">-R$ {:.2f}</span>',
            obj.impact_amount
        )
    impact_badge.short_description = 'Impacto'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(models.OutflowItem)
class OutflowItemAdmin(admin.ModelAdmin):
    list_display = ('outflow', 'product', 'quantity', 'unit_cost', 'impact', 'created_at')
    list_filter = ('product', 'created_at')
    search_fields = ('product__title', 'outflow__description', 'notes')
    readonly_fields = ('total_cost', 'total_value', 'impact')
    autocomplete_fields = ['product', 'outflow']

