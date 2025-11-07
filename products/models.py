from django.db import models
from categories.models import Category
from brands.models import Brand


class Product(models.Model):
    title = models.CharField(max_length=500)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    description = models.TextField(null=True, blank=True)
    serie_number = models.CharField(max_length=200, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=20, decimal_places=2)
    selling_price = models.DecimalField(max_digits=20, decimal_places=2)
    quantity = models.IntegerField(default=0)
    image = models.ImageField(
        upload_to='products/', 
        null=True, 
        blank=True,
        verbose_name='Imagem do Produto',
        help_text='Faça upload de uma imagem do produto (JPG, PNG)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def deletion_block_reason(self) -> str | None:
        """Retorna o motivo para impedir exclusão, se existir."""
        if self.quantity and self.quantity > 0:
            return 'Não é possível excluir este produto porque ainda possui estoque disponível.'

        if not self.pk:
            return None

        from django.apps import apps

        SaleItem = apps.get_model('pos', 'SaleItem')
        ReturnItem = apps.get_model('pos', 'ReturnItem')

        if SaleItem.objects.filter(product_id=self.pk).exists():
            return 'Não é possível excluir este produto porque ele já foi utilizado em vendas.'

        if ReturnItem.objects.filter(product_id=self.pk).exists():
            return 'Não é possível excluir este produto porque ele já foi utilizado em devoluções.'

        return None

    def can_be_deleted(self) -> bool:
        """Indica se o produto pode ser excluído com segurança."""
        return self.deletion_block_reason() is None
