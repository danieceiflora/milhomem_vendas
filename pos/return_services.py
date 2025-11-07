"""
Serviços de lógica de negócio para devoluções (Returns).
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, List
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Sale, SaleItem, Return, ReturnItem, LedgerEntry, TWO_PLACES
from products.models import Product
from customers.models import Customer


class ReturnValidationError(Exception):
    """Exceção para erros de validação em devoluções."""
    pass


def validate_return_items(sale: Sale, items_data: List[Dict]) -> None:
    """
    Valida se os itens podem ser devolvidos.
    
    Args:
        sale: Venda original
        items_data: Lista de dicts com 'sale_item_id' e 'quantity'
    
    Raises:
        ReturnValidationError: Se houver algum erro de validação
    """
    if sale.status not in [Sale.Status.FINALIZED, Sale.Status.PARTIALLY_RETURNED]:
        raise ReturnValidationError(
            f'Apenas vendas finalizadas ou parcialmente devolvidas podem ter itens devolvidos. '
            f'Status atual: {sale.get_status_display()}'
        )
    
    if not items_data:
        raise ReturnValidationError('Nenhum item foi selecionado para devolução.')
    
    # Validar cada item
    for item_data in items_data:
        sale_item_id = item_data.get('sale_item_id')
        quantity = item_data.get('quantity', 0)
        
        if not sale_item_id:
            raise ReturnValidationError('ID do item da venda não fornecido.')
        
        try:
            sale_item = SaleItem.objects.get(id=sale_item_id, sale=sale)
        except SaleItem.DoesNotExist:
            raise ReturnValidationError(f'Item #{sale_item_id} não encontrado nesta venda.')
        
        if quantity <= 0:
            raise ReturnValidationError(
                f'Quantidade inválida para {sale_item.product.title}: {quantity}'
            )
        
        # Calcular quantidade já devolvida
        already_returned = sum(
            ri.quantity 
            for ri in sale_item.return_items.filter(
                return_instance__status__in=[Return.Status.APPROVED, Return.Status.COMPLETED]
            )
        )
        
        available = sale_item.quantity - already_returned
        
        if quantity > available:
            raise ReturnValidationError(
                f'{sale_item.product.title}: Tentando devolver {quantity} unidades, '
                f'mas apenas {available} estão disponíveis (total vendido: {sale_item.quantity}, '
                f'já devolvido: {already_returned}).'
            )

        raw_unit_price = item_data.get('unit_price')
        if raw_unit_price in (None, ''):
            unit_price = sale_item.unit_price
        else:
            try:
                unit_price = Decimal(str(raw_unit_price))
            except (InvalidOperation, ValueError, TypeError):
                raise ReturnValidationError(
                    f'Valor unitário inválido para o item {sale_item.product.title}.'
                )

        unit_price = unit_price.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        if unit_price < Decimal('0'):
            raise ReturnValidationError(
                f'Valor unitário inválido para {sale_item.product.title}: não pode ser negativo.'
            )

        max_unit_price = sale_item.unit_price.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        if unit_price > max_unit_price:
            raise ReturnValidationError(
                f'Valor unitário para {sale_item.product.title} não pode exceder o valor original (R$ {max_unit_price}).'
            )

        item_data['unit_price'] = unit_price
        item_data['sale_item'] = sale_item


def calculate_return_total(items_data: List[Dict]) -> Decimal:
    """
    Calcula o valor total da devolução baseado nos itens.
    
    Args:
        items_data: Lista de dicts com 'sale_item_id' e 'quantity'
    
    Returns:
        Valor total da devolução
    """
    total = Decimal('0')
    
    for item_data in items_data:
        sale_item = item_data.get('sale_item')
        if sale_item is None:
            sale_item = SaleItem.objects.get(id=item_data['sale_item_id'])
        quantity = Decimal(str(item_data['quantity']))
        unit_price = item_data.get('unit_price', sale_item.unit_price)
        line_total = (unit_price * quantity).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        total += line_total
    
    return total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@transaction.atomic
def create_return(
    sale: Sale,
    items_data: List[Dict],
    reason: str,
    refund_method: str,
    user: User,
    notes: str = ''
) -> Return:
    """
    Cria uma nova devolução.
    
    Args:
        sale: Venda original
        items_data: Lista de dicts com 'sale_item_id' e 'quantity'
        reason: Motivo da devolução
        refund_method: Método de reembolso (Return.RefundMethod)
        user: Usuário que está processando a devolução
        notes: Observações adicionais (opcional)
    
    Returns:
        Instância de Return criada
    
    Raises:
        ReturnValidationError: Se houver erro de validação
    """
    # Validar itens
    validate_return_items(sale, items_data)
    
    # Calcular total
    total_amount = calculate_return_total(items_data)
    
    # Criar devolução
    return_instance = Return.objects.create(
        original_sale=sale,
        customer=sale.customer,
        user=user,
        status=Return.Status.PENDING,
        reason=reason,
        refund_method=refund_method,
        total_amount=total_amount,
        notes=notes
    )
    
    # Criar itens da devolução
    for item_data in items_data:
        sale_item = item_data.get('sale_item')
        if sale_item is None:
            sale_item = SaleItem.objects.get(id=item_data['sale_item_id'])
        quantity = item_data['quantity']
        unit_price = item_data.get('unit_price', sale_item.unit_price)
        
        ReturnItem.objects.create(
            return_instance=return_instance,
            sale_item=sale_item,
            product=sale_item.product,
            quantity=quantity,
            unit_price=unit_price
        )
    
    return return_instance


@transaction.atomic
def approve_return(return_instance: Return, approved_by: User) -> Return:
    """
    Aprova uma devolução (apenas para gerentes/admins).
    
    Args:
        return_instance: Instância de Return
        approved_by: Usuário que está aprovando (deve ser staff)
    
    Returns:
        Instância de Return atualizada
    
    Raises:
        ReturnValidationError: Se houver erro de validação
    """
    if not approved_by.is_staff:
        raise ReturnValidationError('Apenas gerentes podem aprovar devoluções.')
    
    if return_instance.status != Return.Status.PENDING:
        raise ReturnValidationError(
            f'Apenas devoluções pendentes podem ser aprovadas. '
            f'Status atual: {return_instance.get_status_display()}'
        )
    
    return_instance.status = Return.Status.APPROVED
    return_instance.approved_by = approved_by
    return_instance.approved_at = timezone.now()
    return_instance.save()
    
    return return_instance


@transaction.atomic
def complete_return(return_instance: Return) -> Return:
    """
    Completa uma devolução aprovada:
    - Atualiza estoque dos produtos
    - Gera lançamento de crédito
    - Atualiza status da venda original
    
    Args:
        return_instance: Instância de Return aprovada
    
    Returns:
        Instância de Return atualizada
    
    Raises:
        ReturnValidationError: Se houver erro de validação
    """
    if return_instance.status != Return.Status.APPROVED:
        raise ReturnValidationError(
            f'Apenas devoluções aprovadas podem ser concluídas. '
            f'Status atual: {return_instance.get_status_display()}'
        )
    
    # Atualizar estoque dos produtos devolvidos
    for return_item in return_instance.items.all():
        product = return_item.product
        product.quantity += return_item.quantity
        product.save(update_fields=['quantity'])
    
    # Gerar lançamento de crédito (apenas se método for 'credit' ou ainda não foi reembolsado)
    if return_instance.refund_method == Return.RefundMethod.CREDIT:
        ledger_entry = LedgerEntry.objects.create(
            customer=return_instance.customer,
            sale=return_instance.original_sale,
            type=LedgerEntry.Type.CREDIT,
            status=LedgerEntry.Status.OPEN,
            amount=return_instance.total_amount,
            description=f'Crédito referente à devolução #{return_instance.pk} da venda #{return_instance.original_sale.pk}'
        )
        return_instance.ledger_entry = ledger_entry
    else:
        # Se foi reembolsado em dinheiro/cartão/pix, criar lançamento já liquidado para histórico
        ledger_entry = LedgerEntry.objects.create(
            customer=return_instance.customer,
            sale=return_instance.original_sale,
            type=LedgerEntry.Type.CREDIT,
            status=LedgerEntry.Status.SETTLED,
            amount=return_instance.total_amount,
            settled_at=timezone.now(),
            description=f'Reembolso via {return_instance.get_refund_method_display()} - Devolução #{return_instance.pk} da venda #{return_instance.original_sale.pk}'
        )
        return_instance.ledger_entry = ledger_entry
    
    # Atualizar status da devolução
    return_instance.status = Return.Status.COMPLETED
    return_instance.completed_at = timezone.now()
    return_instance.save()
    
    # Atualizar status da venda original
    update_sale_return_status(return_instance.original_sale)
    
    return return_instance


def update_sale_return_status(sale: Sale) -> None:
    """
    Atualiza o status da venda com base nas devoluções.
    
    Args:
        sale: Venda a ser atualizada
    """
    # Pegar todos os itens da venda
    sale_items = sale.items.all()
    
    if not sale_items:
        return
    
    # Calcular total vendido e total devolvido (apenas devoluções concluídas)
    total_sold = sum(item.quantity for item in sale_items)
    total_returned = 0
    
    for sale_item in sale_items:
        returned_qty = sum(
            ri.quantity 
            for ri in sale_item.return_items.filter(
                return_instance__status=Return.Status.COMPLETED
            )
        )
        total_returned += returned_qty
    
    # Atualizar status
    if total_returned == 0:
        # Nenhum item devolvido, manter FINALIZED
        if sale.status in [Sale.Status.PARTIALLY_RETURNED, Sale.Status.FULLY_RETURNED]:
            sale.status = Sale.Status.FINALIZED
            sale.save(update_fields=['status'])
    elif total_returned >= total_sold:
        # Todos os itens devolvidos
        sale.status = Sale.Status.FULLY_RETURNED
        sale.save(update_fields=['status'])
    else:
        # Alguns itens devolvidos
        sale.status = Sale.Status.PARTIALLY_RETURNED
        sale.save(update_fields=['status'])


@transaction.atomic
def reject_return(return_instance: Return, rejected_by: User, rejection_reason: str = '') -> Return:
    """
    Rejeita uma devolução (apenas para gerentes/admins).
    
    Args:
        return_instance: Instância de Return
        rejected_by: Usuário que está rejeitando (deve ser staff)
        rejection_reason: Motivo da rejeição (opcional)
    
    Returns:
        Instância de Return atualizada
    
    Raises:
        ReturnValidationError: Se houver erro de validação
    """
    if not rejected_by.is_staff:
        raise ReturnValidationError('Apenas gerentes podem rejeitar devoluções.')
    
    if return_instance.status != Return.Status.PENDING:
        raise ReturnValidationError(
            f'Apenas devoluções pendentes podem ser rejeitadas. '
            f'Status atual: {return_instance.get_status_display()}'
        )
    
    return_instance.status = Return.Status.REJECTED
    return_instance.approved_by = rejected_by  # Registra quem rejeitou
    return_instance.approved_at = timezone.now()
    
    if rejection_reason:
        return_instance.notes = f'{return_instance.notes}\n\nMotivo da rejeição: {rejection_reason}'.strip()
    
    return_instance.save()
    
    return return_instance


def get_customer_available_credit(customer: Customer) -> Decimal:
    """
    Retorna o total de crédito disponível do cliente.
    
    Args:
        customer: Cliente
    
    Returns:
        Valor total de crédito disponível
    """
    credits = LedgerEntry.objects.filter(
        customer=customer,
        type=LedgerEntry.Type.CREDIT,
        status=LedgerEntry.Status.OPEN
    ).aggregate(total=Sum('amount'))
    
    return credits['total'] or Decimal('0')
