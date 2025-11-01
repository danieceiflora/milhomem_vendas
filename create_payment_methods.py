from outflows.models import PaymentMethod
from decimal import Decimal

methods = [
    ('Dinheiro', 0),
    ('PIX', 5),
    ('Cartão de Débito', 2),
    ('Cartão de Crédito', 0),
]

for name, disc in methods:
    pm, created = PaymentMethod.objects.get_or_create(
        name=name,
        defaults={
            'discount_percentage': Decimal(str(disc)),
            'is_active': True
        }
    )
    print(f'{name}: {pm.id} (criado={created})')
