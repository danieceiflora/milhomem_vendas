from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'formatted_cpf', 'created_at')
    search_fields = ('full_name', 'email', 'cpf')
    list_filter = ('created_at',)
