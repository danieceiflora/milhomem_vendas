"""
Comando para criar métodos de pagamento padrão.
"""
from django.core.management.base import BaseCommand
from pos.models import PaymentMethod
from decimal import Decimal


class Command(BaseCommand):
    help = 'Cria métodos de pagamento padrão'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('💳 Criando métodos de pagamento...'))
        
        payment_methods = [
            {'name': 'Dinheiro', 'discount_percentage': Decimal('0.00')},
            {'name': 'PIX', 'discount_percentage': Decimal('5.00')},
            {'name': 'Cartão de Débito', 'discount_percentage': Decimal('2.00')},
            {'name': 'Cartão de Crédito', 'discount_percentage': Decimal('0.00')},
        ]
        
        created_count = 0
        
        for pm_data in payment_methods:
            pm, created = PaymentMethod.objects.get_or_create(
                name=pm_data['name'],
                defaults={
                    'discount_percentage': pm_data['discount_percentage'],
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Criado: {pm.name} ({pm.discount_percentage}% desconto)'))
                created_count += 1
            else:
                self.stdout.write(f'⏭️  Já existe: {pm.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\n🎉 {created_count} método(s) de pagamento criado(s)!'))
