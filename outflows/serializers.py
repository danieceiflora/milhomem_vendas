from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from .models import Outflow, OutflowItem


class OutflowItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    subtotal = serializers.SerializerMethodField()
    cost_total = serializers.SerializerMethodField()

    class Meta:
        model = OutflowItem
        fields = (
            'id',
            'product',
            'product_title',
            'quantity',
            'unit_price',
            'unit_cost',
            'notes',
            'subtotal',
            'cost_total',
        )
        read_only_fields = ('unit_cost', 'unit_price')

    def get_subtotal(self, obj) -> Decimal:
        return obj.subtotal

    def get_cost_total(self, obj) -> Decimal:
        return obj.cost_total


class OutflowSerializer(serializers.ModelSerializer):
    items = OutflowItemSerializer(many=True)
    outflow_type_display = serializers.CharField(source='get_outflow_type_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    total_items = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()
    impact_amount_value = serializers.SerializerMethodField()

    class Meta:
        model = Outflow
        fields = (
            'id',
            'outflow_type',
            'outflow_type_display',
            'description',
            'recipient',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
            'items',
            'total_items',
            'total_cost',
            'total_value',
            'impact_amount_value',
        )
        read_only_fields = ('created_by', 'created_at', 'updated_at')

    def get_total_items(self, obj) -> int:
        return obj.total_items

    def get_total_cost(self, obj) -> Decimal:
        return obj.total_cost

    def get_total_value(self, obj) -> Decimal:
        return obj.total_value

    def get_impact_amount_value(self, obj) -> Decimal:
        return obj.impact_amount

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])

        if not items_data:
            raise serializers.ValidationError({'items': 'Adicione ao menos um item à saída.'})

        with transaction.atomic():
            outflow = Outflow.objects.create(**validated_data)
            self._create_items(outflow, items_data)

        return outflow

    def _create_items(self, outflow, items_data):
        saved = False

        for item_data in items_data:
            product = item_data.get('product')
            quantity = item_data.get('quantity')
            notes = item_data.get('notes', '')

            if not product or not quantity:
                raise serializers.ValidationError('Produto e quantidade são obrigatórios.')

            product.refresh_from_db()

            if quantity > product.quantity:
                raise serializers.ValidationError(
                    f'Estoque insuficiente para o produto {product}. Disponível: {product.quantity} unidade(s).'
                )

            OutflowItem.objects.create(
                outflow=outflow,
                product=product,
                quantity=quantity,
                unit_price=product.selling_price,
                unit_cost=product.cost_price,
                notes=notes,
            )

            product.quantity -= quantity
            product.save(update_fields=['quantity'])
            saved = True

        if not saved:
            raise serializers.ValidationError('Adicione ao menos um item válido à saída.')
