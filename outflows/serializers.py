from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from .models import Outflow, OutflowItem, OutflowReturnItem, PaymentMethod


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


class OutflowReturnItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    original_product_title = serializers.CharField(source='original_item.product.title', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OutflowReturnItem
        fields = (
            'id',
            'original_item',
            'original_product_title',
            'product',
            'product_title',
            'quantity',
            'unit_price',
            'unit_cost',
            'subtotal',
        )
        read_only_fields = ('unit_price', 'unit_cost', 'product')

    def get_subtotal(self, obj) -> Decimal:
        return obj.subtotal


class OutflowSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    items = OutflowItemSerializer(many=True)
    return_items = OutflowReturnItemSerializer(many=True, read_only=True)
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    total_items = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    total_profit = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    final_amount_value = serializers.SerializerMethodField()
    payment_method = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    related_outflow = serializers.PrimaryKeyRelatedField(
        queryset=Outflow.objects.filter(operation_type=Outflow.OperationType.SALE),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Outflow
        fields = (
            'id',
            'customer',
            'customer_name',
            'operation_type',
            'operation_type_display',
            'related_outflow',
            'payment_method',
            'payment_method_name',
            'payment_discount_percentage',
            'payment_discount_amount',
            'final_amount',
            'discount_amount',
            'final_amount_value',
            'description',
            'created_at',
            'updated_at',
            'items',
            'return_items',
            'total_items',
            'total_amount',
            'total_cost',
            'total_profit',
        )
        read_only_fields = (
            'payment_discount_percentage',
            'payment_discount_amount',
            'final_amount',
        )

    def get_total_items(self, obj) -> int:
        return obj.total_items

    def get_total_amount(self, obj) -> Decimal:
        return obj.total_amount

    def get_total_cost(self, obj) -> Decimal:
        return obj.total_cost

    def get_total_profit(self, obj) -> Decimal:
        return obj.total_profit

    def get_discount_amount(self, obj) -> Decimal:
        return obj.payment_discount_amount

    def get_final_amount_value(self, obj) -> Decimal:
        return obj.final_amount

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])

        operation_type = validated_data.get('operation_type', Outflow.OperationType.SALE)
        validated_data['operation_type'] = operation_type

        if operation_type != Outflow.OperationType.SALE:
            raise serializers.ValidationError(
                {'operation_type': 'Somente vendas podem ser criadas pela API no momento.'}
            )

        payment_method = validated_data.get('payment_method')
        related_outflow = validated_data.get('related_outflow')

        if operation_type == Outflow.OperationType.SALE:
            if not payment_method:
                raise serializers.ValidationError({'payment_method': 'Informe o método de pagamento.'})
            if related_outflow:
                raise serializers.ValidationError({'related_outflow': 'Vendas não devem referenciar outra operação.'})
            validated_data['payment_discount_percentage'] = payment_method.discount_percentage
        else:
            if not related_outflow:
                raise serializers.ValidationError({'related_outflow': 'Informe a venda original.'})
            if related_outflow.operation_type != Outflow.OperationType.SALE:
                raise serializers.ValidationError({'related_outflow': 'A operação relacionada precisa ser uma venda.'})
            if validated_data['customer'] != related_outflow.customer:
                raise serializers.ValidationError({'customer': 'O cliente deve ser o mesmo da venda original.'})
            validated_data['payment_method'] = None
            validated_data['payment_discount_percentage'] = Decimal('0')

        if not items_data:
            raise serializers.ValidationError({'items': 'Adicione ao menos um item à venda.'})

        with transaction.atomic():
            outflow = Outflow.objects.create(**validated_data)
            self._create_items(outflow, items_data)
            outflow.refresh_financials()
            outflow.save(update_fields=['payment_discount_amount', 'final_amount'])

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
