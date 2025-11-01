from rest_framework import serializers
from products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    has_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = '__all__'
    
    def get_has_stock(self, obj):
        """Retorna True se o produto tem estoque disponível"""
        return obj.quantity > 0
