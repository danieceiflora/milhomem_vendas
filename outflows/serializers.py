from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from .models import Outflow, OutflowItem


class OutflowItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    subtotal = serializers.SerializerMethodField()
    profit = serializers.SerializerMethodField()

    class Meta:
        model = OutflowItem
        fields = (
            'id',
            'product',
            'product_title',
            'quantity',
            'unit_price',
            'unit_cost',
            'subtotal',
            'profit',
        )
        read_only_fields = ('unit_cost',)
        extra_kwargs = {
            'unit_price': {'required': False},
        }

    def get_subtotal(self, obj) -> Decimal:
        return obj.subtotal

    def get_profit(self, obj) -> Decimal:
        return obj.profit


class OutflowSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    items = OutflowItemSerializer(many=True)
    total_items = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    total_profit = serializers.SerializerMethodField()

    class Meta:
        model = Outflow
        fields = (
            'id',
            'customer',
            'customer_name',
            'description',
            'created_at',
            'updated_at',
            'items',
            'total_items',
            'total_amount',
            'total_profit',
        )

    def get_total_items(self, obj) -> int:
        return obj.total_items

    def get_total_amount(self, obj) -> Decimal:
        return obj.total_amount

    def get_total_profit(self, obj) -> Decimal:
        return obj.total_profit

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])

        if not items_data:
            raise serializers.ValidationError({'items': 'Adicione ao menos um item à venda.'})

        with transaction.atomic():
            outflow = Outflow.objects.create(**validated_data)
            self._create_items(outflow, items_data)

        return outflow

    def _create_items(self, outflow, items_data):
        saved = False

        for item_data in items_data:
            product = item_data.get('product')
            quantity = item_data.get('quantity')
            unit_price = item_data.get('unit_price')

            if not product or not quantity:
                raise serializers.ValidationError('Produto e quantidade são obrigatórios.')

            product.refresh_from_db()

            if quantity > product.quantity:
                raise serializers.ValidationError(
                    f'Estoque insuficiente para o produto {product}. Disponível: {product.quantity} unidade(s).'
                )

            if not unit_price or unit_price == Decimal('0'):
                unit_price = product.selling_price

            OutflowItem.objects.create(
                outflow=outflow,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                unit_cost=product.cost_price,
            )

            product.quantity -= quantity
            product.save(update_fields=['quantity'])
            saved = True

        if not saved:
            raise serializers.ValidationError('Adicione ao menos um item válido à venda.')
