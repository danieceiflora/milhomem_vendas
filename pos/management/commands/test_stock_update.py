"""
Comando para testar atualização de estoque ao finalizar venda.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pos.models import Sale
from pos import services
from products.models import Product

User = get_user_model()


class Command(BaseCommand):
    help = 'Testa se o estoque é atualizado ao finalizar uma venda'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🧪 Iniciando teste de atualização de estoque...'))
        
        # Pega um produto qualquer
        product = Product.objects.filter(quantity__gt=0).first()
        
        if not product:
            self.stdout.write(self.style.ERROR('❌ Nenhum produto com estoque disponível'))
            return
        
        # Pega um usuário
        user = User.objects.first()
        
        if not user:
            self.stdout.write(self.style.ERROR('❌ Nenhum usuário encontrado'))
            return
        
        # Estoque inicial
        initial_stock = product.quantity
        quantity_to_sell = 1 if initial_stock >= 1 else 0
        
        if quantity_to_sell == 0:
            self.stdout.write(self.style.ERROR('❌ Produto sem estoque suficiente'))
            return
        
        self.stdout.write(f'📦 Produto: {product.title}')
        self.stdout.write(f'📊 Estoque inicial: {initial_stock}')
        self.stdout.write(f'🛒 Quantidade a vender: {quantity_to_sell}')
        
        # Cria uma venda de teste
        sale = services.get_or_create_draft_sale(user=user, session_key='test-stock-update')
        
        # Adiciona o item
        services.add_item(sale, product.id, quantity_to_sell)
        
        # Adiciona pagamento (simula pagamento em dinheiro)
        from pos.models import PaymentMethod
        payment_method = PaymentMethod.objects.filter(is_active=True).first()
        
        if not payment_method:
            self.stdout.write(self.style.ERROR('❌ Nenhum método de pagamento encontrado'))
            return
        
        services.add_payment(
            sale=sale,
            payment_method_id=payment_method.id,
            amount=sale.total,
            cash_tendered=sale.total
        )
        
        # Finaliza a venda
        result = services.finalize_sale(sale)
        
        if result['status'] != 'success':
            self.stdout.write(self.style.ERROR(f'❌ Falha ao finalizar: {result}'))
            return
        
        # Recarrega o produto do banco
        product.refresh_from_db()
        
        # Verifica se o estoque foi atualizado
        expected_stock = initial_stock - quantity_to_sell
        actual_stock = product.quantity
        
        self.stdout.write(f'📊 Estoque esperado: {expected_stock}')
        self.stdout.write(f'📊 Estoque atual: {actual_stock}')
        
        if actual_stock == expected_stock:
            self.stdout.write(self.style.SUCCESS('✅ SUCESSO! Estoque atualizado corretamente!'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ ERRO! Estoque não foi atualizado. Esperado: {expected_stock}, Atual: {actual_stock}'))
        
        self.stdout.write(f'🧾 Venda #{sale.id} finalizada')
