"""
Serviços de lógica de negócio para o PDV.
Funções puras que realizam operações e cálculos independentes de views.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from typing import Optional, Dict, Any
from .models import Sale, SaleItem, SalePayment, LedgerEntry, PaymentMethod
from customers.models import Customer
from products.models import Product


TWO_PLACES = Decimal('0.01')


def get_or_create_generic_customer() -> Customer:
    """Retorna ou cria o cliente genérico do sistema."""
    customer, created = Customer.objects.get_or_create(
        phone='00000000000',
        defaults={
            'full_name': 'Cliente Genérico',
            'is_generic': True,
        }
    )
    if not customer.is_generic:
        customer.is_generic = True
        customer.save(update_fields=['is_generic'])
    return customer


def get_or_create_draft_sale(user, session_key: str, customer: Optional[Customer] = None) -> Sale:
    """
    Retorna a venda em rascunho do usuário ou cria uma nova.
    Um usuário pode ter apenas uma venda draft ativa por vez.
    """
    if not customer:
        customer = get_or_create_generic_customer()
    
    sale = Sale.objects.filter(
        user=user,
        status=Sale.Status.DRAFT,
        session_key=session_key
    ).first()
    
    if not sale:
        sale = Sale.objects.create(
            user=user,
            customer=customer,
            session_key=session_key,
            status=Sale.Status.DRAFT
        )
    
    return sale


@transaction.atomic
def add_item(sale: Sale, product_id: int, quantity: int) -> SaleItem:
    """
    Adiciona um item à venda ou atualiza a quantidade se já existir.
    Recalcula os totais automaticamente.
    Valida estoque disponível.
    """
    if quantity < 1:
        raise ValueError("Quantidade deve ser maior que zero")
    
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        raise ValueError(f"Produto {product_id} não encontrado")
    
    # Validação de estoque
    if product.quantity <= 0:
        raise ValueError(f"Produto '{product.title}' está sem estoque disponível")
    
    # Verifica se o item já existe na venda
    item = sale.items.filter(product=product).first()
    new_quantity = quantity if not item else item.quantity + quantity
    
    if new_quantity > product.quantity:
        raise ValueError(
            f"Quantidade solicitada ({new_quantity}) excede o estoque disponível ({product.quantity}) "
            f"para o produto '{product.title}'"
        )
    
    if item:
        item.quantity = new_quantity
        item.save()
    else:
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            unit_price=product.selling_price or Decimal('0'),
            unit_cost=product.cost_price or Decimal('0')
        )
    
    recalc_totals(sale)
    return item


@transaction.atomic
def update_item(sale: Sale, item_id: int, quantity: int) -> SaleItem:
    """
    Atualiza a quantidade de um item específico.
    Remove o item se quantidade for 0.
    Valida estoque disponível.
    """
    if quantity < 0:
        raise ValueError("Quantidade não pode ser negativa")
    
    try:
        item = sale.items.get(pk=item_id)
    except SaleItem.DoesNotExist:
        raise ValueError(f"Item {item_id} não encontrado")
    
    # Validação de estoque ao atualizar
    if quantity > 0 and quantity > item.product.quantity:
        raise ValueError(
            f"Quantidade solicitada ({quantity}) excede o estoque disponível ({item.product.quantity}) "
            f"para o produto '{item.product.title}'"
        )
    
    if quantity == 0:
        item.delete()
    else:
        item.quantity = quantity
        item.save()
    
    recalc_totals(sale)
    return item if quantity > 0 else None


@transaction.atomic
def remove_item(sale: Sale, item_id: int) -> None:
    """Remove um item da venda."""
    try:
        item = sale.items.get(pk=item_id)
        item.delete()
    except SaleItem.DoesNotExist:
        raise ValueError(f"Item {item_id} não encontrado")
    
    recalc_totals(sale)


@transaction.atomic
def add_payment(
    sale: Sale,
    payment_method_id: int,
    amount: Optional[Decimal] = None,
    cash_tendered: Optional[Decimal] = None
) -> SalePayment:
    """
    Adiciona um pagamento à venda.
    Para dinheiro: calcula o troco e o amount_applied baseado em cash_tendered.
    Para outros métodos: usa o amount fornecido.
    """
    try:
        payment_method = PaymentMethod.objects.get(pk=payment_method_id)
    except PaymentMethod.DoesNotExist:
        raise ValueError(f"Método de pagamento {payment_method_id} não encontrado")
    
    is_cash = payment_method.name.lower() in ['dinheiro', 'cash']
    
    if is_cash:
        if not cash_tendered or cash_tendered <= 0:
            raise ValueError("Valor recebido em dinheiro deve ser maior que zero")
        
        # Calcula quanto ainda falta pagar
        remaining = sale.total - sale.total_paid
        
        # O amount_applied é o mínimo entre o recebido e o restante
        amount_applied = min(cash_tendered, remaining)
        
        # O troco é o excedente
        change_given = max(Decimal('0'), cash_tendered - amount_applied)
        
        payment = SalePayment.objects.create(
            sale=sale,
            payment_method=payment_method,
            amount_applied=amount_applied,
            cash_tendered=cash_tendered,
            change_given=change_given
        )
    else:
        if not amount or amount <= 0:
            raise ValueError("Valor do pagamento deve ser maior que zero")
        
        payment = SalePayment.objects.create(
            sale=sale,
            payment_method=payment_method,
            amount_applied=amount
        )
    
    recalc_totals(sale)
    return payment


@transaction.atomic
def remove_payment(sale: Sale, payment_id: int) -> None:
    """Remove um pagamento da venda."""
    try:
        payment = sale.payments.get(pk=payment_id)
        payment.delete()
    except SalePayment.DoesNotExist:
        raise ValueError(f"Pagamento {payment_id} não encontrado")
    
    recalc_totals(sale)


@transaction.atomic
def set_customer(sale: Sale, customer_id: Optional[int]) -> Sale:
    """Define ou altera o cliente da venda."""
    if customer_id:
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            raise ValueError(f"Cliente {customer_id} não encontrado")
    else:
        customer = get_or_create_generic_customer()
    
    sale.customer = customer
    sale.save(update_fields=['customer'])
    return sale


def recalc_totals(sale: Sale) -> Sale:
    """
    Recalcula todos os totais da venda baseado nos itens e pagamentos.
    Atualiza: subtotal, total, total_paid.
    NÃO altera discount_total (apenas em finalize).
    
    O total considera:
    - Subtotal (soma dos itens)
    - Menos descontos manuais (discount_total)
    - Mais taxas de pagamento pagas pelo cliente (fee_total)
    
    IMPORTANTE: A taxa é calculada sobre o SUBTOTAL-DESCONTO, uma única vez,
    se houver pelo menos um pagamento com taxa paga pelo cliente.
    """
    # Calcula subtotal dos itens
    subtotal = sum(
        (item.line_total for item in sale.items.all()),
        Decimal('0')
    )
    
    # Valor base para cálculo de taxas (subtotal - desconto)
    base_value = (subtotal - sale.discount_total).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    base_value = max(Decimal('0'), base_value)
    
    # Calcula taxas de pagamento pagas pelo cliente
    # A taxa é aplicada UMA VEZ sobre o valor base, usando a maior taxa dentre os métodos
    fee_total = Decimal('0')
    max_fee_percentage = Decimal('0')
    
    for payment in sale.payments.select_related('payment_method').all():
        if payment.payment_method.fee_payer == PaymentMethod.FeePayerType.CUSTOMER:
            # Encontra a maior taxa
            if payment.payment_method.fee_percentage > max_fee_percentage:
                max_fee_percentage = payment.payment_method.fee_percentage
    
    # Aplica a maior taxa sobre o valor base
    if max_fee_percentage > 0 and base_value > 0:
        fee_total = (base_value * (max_fee_percentage / 100)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    
    # Total = subtotal - desconto + taxa
    total = (subtotal - sale.discount_total + fee_total).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    total = max(Decimal('0'), total)
    
    # Total pago = soma dos pagamentos aplicados
    total_paid = sum(
        (payment.amount_applied for payment in sale.payments.all()),
        Decimal('0')
    )
    
    sale.subtotal = subtotal
    sale.total = total
    sale.total_paid = total_paid
    sale.save(update_fields=['subtotal', 'total', 'total_paid'])
    
    return sale


@transaction.atomic
@transaction.atomic
def finalize_sale(sale: Sale, resolution: Optional[str] = None) -> Dict[str, Any]:
    """
    Finaliza a venda e atualiza o estoque dos produtos.
    
    Retorna:
        - {'status': 'success'} se finalizado
        - {'status': 'diff', 'difference': Decimal, 'type': 'underpaid'|'overpaid'} se houver diferença
    
    resolution pode ser:
        - 'apply_discount': ajusta discount_total para igualar total com total_paid
        - 'generate_debit': cria LedgerEntry de débito
        - 'generate_credit': cria LedgerEntry de crédito
        - 'edit': retorna para edição (não finaliza)
    """
    if sale.status != Sale.Status.DRAFT:
        raise ValueError("Apenas vendas em rascunho podem ser finalizadas")
    
    if not sale.items.exists():
        raise ValueError("Não é possível finalizar venda sem itens")
    
    # Validação de estoque antes de finalizar
    items_without_stock = []
    items_exceeding_stock = []
    
    for item in sale.items.select_related('product'):
        if item.product.quantity <= 0:
            items_without_stock.append(item.product.title)
        elif item.quantity > item.product.quantity:
            items_exceeding_stock.append(
                f"{item.product.title} (solicitado: {item.quantity}, disponível: {item.product.quantity})"
            )
    
    if items_without_stock:
        raise ValueError(
            f"Não é possível finalizar a venda. Os seguintes produtos estão sem estoque: {', '.join(items_without_stock)}"
        )
    
    if items_exceeding_stock:
        raise ValueError(
            f"Não é possível finalizar a venda. Quantidades excedem estoque disponível: {', '.join(items_exceeding_stock)}"
        )
    
    # Recalcula para garantir consistência
    recalc_totals(sale)
    
    difference = (sale.total_paid - sale.total).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    tolerance = Decimal('0.01')  # Tolerância de 1 centavo
    
    # Verifica se há diferença significativa
    if abs(difference) > tolerance:
        if difference < 0:  # Pagou menos que o total
            if resolution == 'apply_discount':
                # Aumenta o desconto para igualar
                additional_discount = abs(difference)
                sale.discount_total += additional_discount
                sale.total -= additional_discount
                sale.save(update_fields=['discount_total', 'total'])
            elif resolution == 'generate_debit':
                # Cria lançamento de débito
                LedgerEntry.objects.create(
                    customer=sale.customer,
                    sale=sale,
                    type=LedgerEntry.Type.DEBIT,
                    amount=abs(difference),
                    description=f'Débito gerado na venda #{sale.pk}'
                )
            else:
                # Retorna indicando que precisa de resolução
                return {
                    'status': 'diff',
                    'difference': abs(difference),
                    'type': 'underpaid'
                }
        
        else:  # Pagou mais que o total (excluindo troco já calculado)
            # Verifica se o excesso é explicado por troco
            change_total = sale.change_total
            excess_not_change = difference - change_total
            
            if excess_not_change > tolerance:
                if resolution == 'generate_credit':
                    # Cria lançamento de crédito
                    LedgerEntry.objects.create(
                        customer=sale.customer,
                        sale=sale,
                        type=LedgerEntry.Type.CREDIT,
                        amount=excess_not_change,
                        description=f'Crédito gerado na venda #{sale.pk}'
                    )
                else:
                    # Retorna indicando que precisa de resolução
                    return {
                        'status': 'diff',
                        'difference': excess_not_change,
                        'type': 'overpaid'
                    }
    
    # Finaliza a venda
    sale.status = Sale.Status.FINALIZED
    sale.finalized_at = timezone.now()
    sale.save(update_fields=['status', 'finalized_at'])
    
    # Liquida créditos usados na venda
    settle_credit_after_sale(sale)
    
    # Atualiza o estoque dos produtos (debita as quantidades vendidas)
    for item in sale.items.select_related('product'):
        product = item.product
        product.quantity -= item.quantity
        product.save(update_fields=['quantity'])
    
    return {'status': 'success', 'sale_id': sale.pk}


@transaction.atomic
def reassign_ledger_entry(entry_id: int, customer_id: int) -> LedgerEntry:
    """Reatribui um lançamento para outro cliente."""
    try:
        entry = LedgerEntry.objects.get(pk=entry_id)
    except LedgerEntry.DoesNotExist:
        raise ValueError(f"Lançamento {entry_id} não encontrado")
    
    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        raise ValueError(f"Cliente {customer_id} não encontrado")
    
    entry.customer = customer
    entry.save(update_fields=['customer'])
    
    return entry


def get_customer_available_credit(customer: Customer) -> Decimal:
    """
    Retorna o saldo de crédito disponível do cliente.
    Créditos em aberto - Débitos em aberto.
    """
    from django.db.models import Sum, Q
    
    # Soma de créditos em aberto
    credits = LedgerEntry.objects.filter(
        customer=customer,
        type=LedgerEntry.Type.CREDIT,
        status=LedgerEntry.Status.OPEN
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Soma de débitos em aberto
    debits = LedgerEntry.objects.filter(
        customer=customer,
        type=LedgerEntry.Type.DEBIT,
        status=LedgerEntry.Status.OPEN
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    return credits - debits


@transaction.atomic
def apply_credit_to_sale(sale: Sale, credit_amount: Decimal) -> SalePayment:
    """
    Aplica crédito disponível do cliente como pagamento na venda.
    
    Args:
        sale: Venda onde o crédito será aplicado
        credit_amount: Valor do crédito a ser usado
    
    Returns:
        SalePayment criado
    
    Raises:
        ValueError: Se o crédito for inválido ou insuficiente
    """
    if sale.status != Sale.Status.DRAFT:
        raise ValueError("Apenas vendas em rascunho podem receber pagamentos")
    
    if credit_amount <= Decimal('0'):
        raise ValueError("O valor do crédito deve ser maior que zero")
    
    # Verifica se o cliente tem crédito disponível
    available_credit = get_customer_available_credit(sale.customer)
    
    if credit_amount > available_credit:
        raise ValueError(
            f"Crédito insuficiente. Disponível: R$ {available_credit:.2f}, "
            f"Solicitado: R$ {credit_amount:.2f}"
        )
    
    # Verifica se não ultrapassa o total da venda
    sale = recalc_totals(sale)
    remaining = sale.total - sale.total_paid
    
    if credit_amount > remaining:
        raise ValueError(
            f"O crédito aplicado (R$ {credit_amount:.2f}) não pode ser maior que "
            f"o valor restante da venda (R$ {remaining:.2f})"
        )
    
    # Cria um método de pagamento "Crédito" se não existir
    credit_method, _ = PaymentMethod.objects.get_or_create(
        name='Crédito',
        defaults={
            'description': 'Uso de crédito disponível do cliente',
            'fee_percentage': Decimal('0'),
            'fee_payer': PaymentMethod.FeePayerType.MERCHANT,
            'is_active': True
        }
    )
    
    # Cria o pagamento
    payment = SalePayment.objects.create(
        sale=sale,
        payment_method=credit_method,
        amount_applied=credit_amount.quantize(TWO_PLACES),
        cash_tendered=None,
        change_given=Decimal('0')
    )
    
    # Recalcula totais
    recalc_totals(sale)
    
    return payment


@transaction.atomic
def settle_credit_after_sale(sale: Sale) -> None:
    """
    Liquida os créditos usados na venda após a finalização.
    Marca os lançamentos de crédito como liquidados.
    """
    # Busca pagamentos com crédito nesta venda
    credit_payments = sale.payments.filter(
        payment_method__name='Crédito'
    )
    
    if not credit_payments.exists():
        return
    
    # Soma total de crédito usado
    total_credit_used = sum(p.amount_applied for p in credit_payments)
    
    # Busca créditos em aberto do cliente (mais antigos primeiro)
    open_credits = LedgerEntry.objects.filter(
        customer=sale.customer,
        type=LedgerEntry.Type.CREDIT,
        status=LedgerEntry.Status.OPEN
    ).order_by('created_at')
    
    remaining_to_settle = total_credit_used
    
    for credit in open_credits:
        if remaining_to_settle <= Decimal('0'):
            break
        
        if credit.amount <= remaining_to_settle:
            # Liquida o crédito completamente
            credit.status = LedgerEntry.Status.SETTLED
            credit.settled_at = timezone.now()
            credit.save(update_fields=['status', 'settled_at'])
            remaining_to_settle -= credit.amount
        else:
            # Liquida parcialmente: divide o crédito
            # Cria um novo lançamento liquidado com a parte usada
            LedgerEntry.objects.create(
                customer=credit.customer,
                sale=sale,
                type=LedgerEntry.Type.CREDIT,
                status=LedgerEntry.Status.SETTLED,
                amount=remaining_to_settle,
                description=f'Crédito usado na venda #{sale.pk}',
                settled_at=timezone.now()
            )
            
            # Reduz o valor do crédito original
            credit.amount -= remaining_to_settle
            credit.save(update_fields=['amount'])
            remaining_to_settle = Decimal('0')
