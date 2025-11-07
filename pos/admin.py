from django.contrib import admin
from django.utils.html import format_html
from .models import Sale, SaleItem, SalePayment, LedgerEntry, PaymentMethod, Return, ReturnItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['line_total', 'created_at']
    fields = ['product', 'quantity', 'unit_price', 'unit_cost', 'line_total']


class SalePaymentInline(admin.TabularInline):
    model = SalePayment
    extra = 0
    readonly_fields = ['created_at']
    fields = ['payment_method', 'amount_applied', 'cash_tendered', 'change_given']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'customer', 'user', 'status', 'total', 'total_paid',
        'items_count', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['customer__full_name', 'notes']
    readonly_fields = [
        'subtotal', 'total', 'total_paid', 'items_count',
        'change_total', 'remaining', 'created_at', 'updated_at', 'finalized_at'
    ]
    inlines = [SaleItemInline, SalePaymentInline]
    
    fieldsets = (
        ('Informações Principais', {
            'fields': ('customer', 'user', 'status', 'session_key')
        }),
        ('Valores', {
            'fields': (
                'subtotal', 'discount_total', 'total',
                'total_paid', 'remaining', 'change_total'
            )
        }),
        ('Observações', {
            'fields': ('notes',)
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at', 'finalized_at')
        }),
    )


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'customer', 'type_badge', 'status_badge', 'amount',
        'sale', 'created_at'
    ]
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['customer__full_name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'settled_at']
    actions = ['mark_as_settled', 'mark_as_cancelled']
    
    fieldsets = (
        ('Informações', {
            'fields': ('customer', 'sale', 'type', 'status', 'amount')
        }),
        ('Descrição', {
            'fields': ('description',)
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at', 'settled_at')
        }),
    )
    
    def type_badge(self, obj):
        colors = {
            'credit': 'green',
            'debit': 'red'
        }
        color = colors.get(obj.type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_type_display()
        )
    type_badge.short_description = 'Tipo'
    
    def status_badge(self, obj):
        colors = {
            'open': 'orange',
            'settled': 'green',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    @admin.action(description='Marcar como liquidado')
    def mark_as_settled(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status=LedgerEntry.Status.SETTLED, settled_at=timezone.now())
        self.message_user(request, f'{updated} lançamento(s) marcado(s) como liquidado(s).')
    
    @admin.action(description='Marcar como cancelado')
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status=LedgerEntry.Status.CANCELLED)
        self.message_user(request, f'{updated} lançamento(s) cancelado(s).')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'fee_display', 'fee_payer_badge',
        'is_active_badge', 'internal_badge', 'updated_at'
    )
    list_filter = ('is_active', 'fee_payer', 'is_internal')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'is_internal')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'description', 'is_active', 'is_internal')
        }),
        ('Configuração de Taxa', {
            'fields': ('fee_percentage', 'fee_payer'),
            'description': 'Configure se haverá desconto (lojista paga) ou acréscimo (cliente paga)'
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def fee_display(self, obj):
        if obj.fee_percentage > 0:
            return f'{obj.fee_percentage}%'
        return 'Sem taxa'
    fee_display.short_description = 'Taxa'
    
    def fee_payer_badge(self, obj):
        if obj.fee_payer == 'customer':
            return format_html(
                '<span style="background-color: #ef4444; color: white; padding: 3px 8px; border-radius: 3px;">↑ Cliente</span>'
            )
        return format_html(
            '<span style="background-color: #10b981; color: white; padding: 3px 8px; border-radius: 3px;">↓ Lojista</span>'
        )
    fee_payer_badge.short_description = 'Quem Paga'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 8px; border-radius: 3px;">✓ Ativo</span>'
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 3px 8px; border-radius: 3px;">✗ Inativo</span>'
        )
    is_active_badge.short_description = 'Status'

    def internal_badge(self, obj):
        if obj.is_internal:
            return format_html(
                '<span style="background-color: #4c1d95; color: white; padding: 3px 8px; border-radius: 3px;">Interno</span>'
            )
        return format_html(
            '<span style="background-color: #6b7280; color: white; padding: 3px 8px; border-radius: 3px;">Externo</span>'
        )
    internal_badge.short_description = 'Uso'


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0
    readonly_fields = ['line_total', 'created_at']
    fields = ['sale_item', 'product', 'quantity', 'unit_price', 'line_total']


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'original_sale', 'customer', 'status_badge', 'total_amount',
        'refund_method', 'user', 'created_at'
    ]
    list_filter = ['status', 'refund_method', 'created_at']
    search_fields = ['customer__full_name', 'reason', 'notes']
    readonly_fields = [
        'total_amount', 'items_count', 'ledger_entry',
        'created_at', 'updated_at', 'approved_at', 'completed_at'
    ]
    inlines = [ReturnItemInline]
    
    fieldsets = (
        ('Informações Principais', {
            'fields': ('original_sale', 'customer', 'user', 'approved_by', 'status')
        }),
        ('Detalhes da Devolução', {
            'fields': ('reason', 'refund_method', 'total_amount', 'items_count')
        }),
        ('Lançamento', {
            'fields': ('ledger_entry',)
        }),
        ('Observações', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at', 'approved_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'blue',
            'rejected': 'red',
            'completed': 'green'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

