from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import OutflowItem


@receiver(post_delete, sender=OutflowItem)
def restore_product_quantity_on_delete(sender, instance, **kwargs):
    product = instance.product
    product.quantity += instance.quantity
    product.save(update_fields=['quantity'])
