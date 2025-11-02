"""
Exemplos de testes para o sistema PDV.
Execute com: python manage.py test pos
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from pos import services
from pos.models import Sale, SaleItem, SalePayment, LedgerEntry, PaymentMethod
from customers.models import Customer
from products.models import Product
from brands.models import Brand
from categories.models import Category


class ServiceTestCase(TestCase):
    """Testes das funções de serviço."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.customer = Customer.objects.create(
            full_name='Cliente Teste',
            phone='11999999999'
        )
        self.brand = Brand.objects.create(name='Marca Teste')
        self.category = Category.objects.create(name='Categoria Teste')
        self.product = Product.objects.create(
            title='Produto Teste',
            brand=self.brand,
            category=self.category,
            selling_price=Decimal('100.00'),
            cost_price=Decimal('50.00'),
            quantity=10
        )
        self.payment_method_cash = PaymentMethod.objects.create(
            name='Dinheiro',
            discount_percentage=Decimal('0')
        )
        self.payment_method_pix = PaymentMethod.objects.create(
            name='PIX',
            discount_percentage=Decimal('5')
        )
    
    def test_create_draft_sale(self):
        """Testa criação de venda em rascunho."""
        sale = services.get_or_create_draft_sale(self.user, 'test-session-123')
        
        self.assertIsNotNone(sale)
        self.assertEqual(sale.status, Sale.Status.DRAFT)
        self.assertEqual(sale.user, self.user)
        self.assertTrue(sale.customer.is_generic)
    
    def test_add_item(self):
        """Testa adição de item à venda."""
        sale = services.get_or_create_draft_sale(self.user, 'test-session')
        item = services.add_item(sale, self.product.id, 2)
        
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal('100.00'))
        self.assertEqual(item.line_total, Decimal('200.00'))
        
        sale.refresh_from_db()
        self.assertEqual(sale.subtotal, Decimal('200.00'))
        self.assertEqual(sale.total, Decimal('200.00'))
    
    def test_finalize_exact_payment(self):
        """Testa finalização com pagamento exato."""
        sale = services.get_or_create_draft_sale(self.user, 'test-session')
        services.add_item(sale, self.product.id, 1)
        services.add_payment(sale, self.payment_method_cash.id, cash_tendered=Decimal('100.00'))
        
        result = services.finalize_sale(sale)
        
        self.assertEqual(result['status'], 'success')
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.FINALIZED)
        self.assertIsNotNone(sale.finalized_at)


# Para executar:
# python manage.py test pos
# python manage.py test pos.tests.ServiceTestCase
# python manage.py test pos.tests.ServiceTestCase.test_add_item
