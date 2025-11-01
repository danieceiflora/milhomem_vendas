"""
Serviços de lógica de negócio para o PDV.
Funções puras que realizam operações e cálculos independentes de views.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from typing import Optional, Dict, Any
from .models import Sale, SaleItem, SalePayment, LedgerEntry
from customers.models import Customer
from products.models import Product
from outflows.models import PaymentMethod


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
    """
    if quantity < 1:
        raise ValueError("Quantidade deve ser maior que zero")
    
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        raise ValueError(f"Produto {product_id} não encontrado")
    
    # Verifica se o item já existe na venda
    item = sale.items.filter(product=product).first()
    
    if item:
        item.quantity += quantity
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
    """
    if quantity < 0:
        raise ValueError("Quantidade não pode ser negativa")
    
    try:
        item = sale.items.get(pk=item_id)
    except SaleItem.DoesNotExist:
        raise ValueError(f"Item {item_id} não encontrado")
    
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
    """
    # Calcula subtotal dos itens
    subtotal = sum(
        (item.line_total for item in sale.items.all()),
        Decimal('0')
    )
    
    # Total = subtotal - desconto
    total = (subtotal - sale.discount_total).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
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
def finalize_sale(sale: Sale, resolution: Optional[str] = None) -> Dict[str, Any]:
    """
    Finaliza a venda.
    
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
