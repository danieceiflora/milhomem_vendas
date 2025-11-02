"""
Comando para migrar métodos de pagamento para o novo formato.
"""
from django.core.management.base import BaseCommand
from pos.models import PaymentMethod


class Command(BaseCommand):
    help = 'Atualiza métodos de pagamento para o novo formato (fee_payer)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🔄 Atualizando métodos de pagamento...'))
        
        # PIX - Taxa paga pelo cliente (acréscimo)
        pix, created = PaymentMethod.objects.get_or_create(
            name='PIX',
            defaults={
                'fee_percentage': 0,
                'fee_payer': PaymentMethod.FeePayerType.CUSTOMER,
                'is_active': True
            }
        )
        if not created:
            pix.fee_payer = PaymentMethod.FeePayerType.CUSTOMER
            pix.fee_percentage = 0  # Sem taxa
            pix.save()
        self.stdout.write(f'✅ PIX: {pix.fee_payer}')
        
        # Dinheiro - Sem taxa
        dinheiro, created = PaymentMethod.objects.get_or_create(
            name='Dinheiro',
            defaults={
                'fee_percentage': 0,
                'fee_payer': PaymentMethod.FeePayerType.MERCHANT,
                'is_active': True
            }
        )
        if not created:
            dinheiro.fee_percentage = 0
            dinheiro.save()
        self.stdout.write(f'✅ Dinheiro: {dinheiro.fee_payer}')
        
        # Cartão de Débito - Taxa paga pelo cliente (2%)
        debito, created = PaymentMethod.objects.get_or_create(
            name='Cartão de Débito',
            defaults={
                'fee_percentage': 2.00,
                'fee_payer': PaymentMethod.FeePayerType.CUSTOMER,
                'is_active': True
            }
        )
        if not created:
            debito.fee_percentage = 2.00
            debito.fee_payer = PaymentMethod.FeePayerType.CUSTOMER
            debito.save()
        self.stdout.write(f'✅ Cartão de Débito: {debito.fee_payer} - {debito.fee_percentage}%')
        
        # Cartão de Crédito - Taxa paga pelo cliente (3%)
        credito, created = PaymentMethod.objects.get_or_create(
            name='Cartão de Crédito',
            defaults={
                'fee_percentage': 3.00,
                'fee_payer': PaymentMethod.FeePayerType.CUSTOMER,
                'is_active': True
            }
        )
        if not created:
            credito.fee_percentage = 3.00
            credito.fee_payer = PaymentMethod.FeePayerType.CUSTOMER
            credito.save()
        self.stdout.write(f'✅ Cartão de Crédito: {credito.fee_payer} - {credito.fee_percentage}%')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Métodos de pagamento atualizados!'))
        self.stdout.write('\n💡 Configuração:')
        self.stdout.write('   - Dinheiro/PIX: sem taxa')
        self.stdout.write('   - Débito: +2% (cliente paga)')
        self.stdout.write('   - Crédito: +3% (cliente paga)')
