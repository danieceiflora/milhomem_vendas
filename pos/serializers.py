from rest_framework import serializers
from .models import Sale, SaleItem, SalePayment, LedgerEntry
from customers.models import Customer
from products.models import Product
from outflows.models import PaymentMethod


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.title', read_only=True)
    product_code = serializers.IntegerField(source='product.id', read_only=True)
    
    class Meta:
        model = SaleItem
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'quantity', 'unit_price', 'line_total', 'unit_cost'
        ]
        read_only_fields = ['id', 'line_total', 'unit_cost']


class SalePaymentSerializer(serializers.ModelSerializer):
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    
    class Meta:
        model = SalePayment
        fields = [
            'id', 'payment_method', 'payment_method_name',
            'amount_applied', 'cash_tendered', 'change_given'
        ]
        read_only_fields = ['id', 'change_given']


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payments = SalePaymentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    change_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    overpaid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Sale
        fields = [
            'id', 'customer', 'customer_name', 'user', 'status',
            'subtotal', 'discount_total', 'total', 'total_paid',
            'items_count', 'change_total', 'remaining', 'overpaid',
            'notes', 'created_at', 'updated_at', 'finalized_at',
            'items', 'payments'
        ]
        read_only_fields = [
            'id', 'user', 'subtotal', 'total', 'total_paid',
            'created_at', 'updated_at', 'finalized_at'
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = LedgerEntry
        fields = [
            'id', 'customer', 'customer_name', 'sale', 'type', 'type_display',
            'status', 'status_display', 'amount', 'description',
            'created_at', 'updated_at', 'settled_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
