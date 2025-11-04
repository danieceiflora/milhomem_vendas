"""Popula tabelas de categorias, marcas, fornecedores, clientes e produtos com dados fictícios.

Execute a partir da raiz do projeto (pasta que contém `manage.py`):

    python scripts\populate_demo_data.py

O script configura o Django automaticamente (usa `DJANGO_SETTINGS_MODULE = 'app.settings'`).
"""
from decimal import Decimal
import random
import os
import django

# Ajusta sys.path para garantir que o pacote do projeto (onde está `manage.py` e o pacote `app`) esteja
# no path mesmo quando o script for executado a partir de outra working directory.
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# opcional: muda o cwd para o root do projeto para operações relativas
os.chdir(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from categories.models import Category
from brands.models import Brand
from suppliers.models import Supplier
from customers.models import Customer
from products.models import Product


def create_categories():
    names = [
        'Bebidas', 'Alimentos', 'Higiene', 'Eletrônicos', 'Acessórios'
    ]
    existing = {c.name for c in Category.objects.filter(name__in=names)}
    objs = [Category(name=n, description=f'Categoria de {n}') for n in names if n not in existing]
    if objs:
        Category.objects.bulk_create(objs)
    print('Categories:', Category.objects.count())


def create_brands():
    names = [
        'Marca A', 'Marca B', 'Marca C', 'Genérico', 'Premium'
    ]
    existing = {b.name for b in Brand.objects.filter(name__in=names)}
    objs = [Brand(name=n, description=f'Linha {n}') for n in names if n not in existing]
    if objs:
        Brand.objects.bulk_create(objs)
    print('Brands:', Brand.objects.count())


def create_suppliers():
    names = [
        'Fornecedor Alfa', 'Fornecedor Beta', 'Distribuidora X', 'Atacado Y', 'Importadora Z'
    ]
    existing = {s.name for s in Supplier.objects.filter(name__in=names)}
    objs = [Supplier(name=n, description=f'Descrição de {n}') for n in names if n not in existing]
    if objs:
        Supplier.objects.bulk_create(objs)
    print('Suppliers:', Supplier.objects.count())


def create_customers(count=20):
    existing_phones = set(Customer.objects.values_list('phone', flat=True))
    objs = []
    for i in range(1, count + 1):
        phone = f'999000{i:04d}'
        if phone in existing_phones:
            continue
        full_name = f'Cliente Demo {i}'
        email = f'demo{i}@example.com'
        cpf = f'{10000000000 + i}'
        objs.append(Customer(
            full_name=full_name,
            phone=phone,
            email=email,
            cpf=cpf,
            city='Cidade',
            state='ST'
        ))
    if objs:
        Customer.objects.bulk_create(objs)
    print('Customers:', Customer.objects.count())


def create_products(count=30):
    categories = list(Category.objects.all())
    brands = list(Brand.objects.all())
    if not categories or not brands:
        print('Crie categorias e marcas primeiro.')
        return

    existing_titles = set(Product.objects.values_list('title', flat=True))
    objs = []
    for i in range(1, count + 1):
        title = f'Produto Demo {i}'
        if title in existing_titles:
            continue
        category = random.choice(categories)
        brand = random.choice(brands)
        cost = Decimal(str(round(random.uniform(5, 40), 2)))
        # margem entre 20% e 120%
        margin = random.uniform(1.2, 2.2)
        sell = (cost * Decimal(str(margin))).quantize(Decimal('0.01'))
        qty = random.randint(0, 50)
        objs.append(Product(
            title=title,
            category=category,
            brand=brand,
            description=f'Descrição do {title}',
            cost_price=cost,
            selling_price=sell,
            quantity=qty
        ))
    if objs:
        Product.objects.bulk_create(objs)
    print('Products:', Product.objects.count())


if __name__ == '__main__':
    print('Populando dados fictícios...')
    create_categories()
    create_brands()
    create_suppliers()
    create_customers(20)
    create_products(30)
    print('Concluído.')
