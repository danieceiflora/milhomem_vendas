from decimal import Decimal
from django.db import migrations, models
import unicodedata


def mark_credit_as_internal(apps, schema_editor):
    PaymentMethod = apps.get_model('pos', 'PaymentMethod')

    for method in PaymentMethod.objects.all():
        normalized = unicodedata.normalize('NFKD', method.name or '').encode('ascii', 'ignore').decode('ascii').lower()
        if normalized == 'credito':
            fields_to_update = []
            if not method.is_internal:
                method.is_internal = True
                fields_to_update.append('is_internal')
            if not method.is_active:
                method.is_active = True
                fields_to_update.append('is_active')
            if method.fee_payer != 'merchant':
                method.fee_payer = 'merchant'
                fields_to_update.append('fee_payer')
            if method.fee_percentage != Decimal('0'):
                method.fee_percentage = Decimal('0')
                fields_to_update.append('fee_percentage')
            description = method.description or ''
            if description.strip() != 'Uso de crédito disponível do cliente':
                method.description = 'Uso de crédito disponível do cliente'
                fields_to_update.append('description')
            if fields_to_update:
                method.save(update_fields=fields_to_update)


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0003_alter_sale_status_return_returnitem_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmethod',
            name='is_internal',
            field=models.BooleanField(
                default=False,
                help_text='Método reservado para fluxos automáticos do sistema',
                verbose_name='Uso interno'
            ),
        ),
        migrations.RunPython(mark_credit_as_internal, migrations.RunPython.noop),
    ]
