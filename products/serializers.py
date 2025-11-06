from rest_framework import serializers
from products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    has_stock = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = '__all__'
    
    def get_has_stock(self, obj):
        """Retorna True se o produto tem estoque disponível"""
        return obj.quantity > 0
    
    def get_image_url(self, obj):
        """Retorna a URL completa da imagem do produto"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
