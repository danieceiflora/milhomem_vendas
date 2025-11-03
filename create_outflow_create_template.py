#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para criar o template outflow_create.html de forma confiável"""

import os

TEMPLATE_CONTENT = """{% extends 'base.html' %}

{% block title %}SGE - Registrar Saída Não Faturada{% endblock %}

{% block content %}

<div class="mb-8">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-3xl font-bold bg-gradient-to-r from-red-400 via-orange-400 to-red-400 bg-clip-text text-transparent">
        Registrar Saída Não Faturada
      </h1>
      <p class="text-muted-foreground mt-2">Registre saídas de produtos por vencimento, doação, avaria e outros motivos</p>
    </div>
    <a href="{% url 'outflow_list' %}" class="inline-flex items-center space-x-2 border border-border bg-background hover:bg-accent text-foreground px-4 py-2 rounded-lg transition-colors">
      <i data-lucide="arrow-left" class="h-4 w-4"></i>
      <span>Voltar</span>
    </a>
  </div>
</div>

<div class="max-w-4xl mx-auto">
  <div class="rounded-lg border border-border bg-card p-6 glass-effect space-y-8">
    
    <form method="post" class="space-y-8" id="outflow-form">
      {% csrf_token %}

      <!-- Tipo de Saída e Descrição -->
      <section class="space-y-4">
        <div class="flex items-center space-x-3">
          <div class="h-10 w-10 bg-gradient-to-r from-red-500 to-orange-600 rounded-lg flex items-center justify-center">
            <i data-lucide="package-x" class="h-5 w-5 text-white"></i>
          </div>
          <div>
            <h2 class="text-xl font-semibold">Informações da Saída</h2>
            <p class="text-sm text-muted-foreground">Defina o tipo e descreva o motivo da saída</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Tipo de Saída -->
          <div class="space-y-2">
            <label for="{{ form.outflow_type.id_for_label }}" class="text-sm font-medium flex items-center space-x-2">
              <i data-lucide="tag" class="h-4 w-4 text-primary"></i>
              <span>{{ form.outflow_type.label }}</span>
              <span class="text-red-400">*</span>
            </label>
            {{ form.outflow_type }}
            {% if form.outflow_type.errors %}
              <div class="text-red-400 text-sm flex items-center space-x-1">
                <i data-lucide="alert-circle" class="h-4 w-4"></i>
                <span>{{ form.outflow_type.errors.0 }}</span>
              </div>
            {% endif %}
            <p class="text-xs text-muted-foreground">{{ form.outflow_type.help_text }}</p>
          </div>

          <!-- Destinatário (opcional) -->
          <div class="space-y-2">
            <label for="{{ form.recipient.id_for_label }}" class="text-sm font-medium flex items-center space-x-2">
              <i data-lucide="user" class="h-4 w-4 text-primary"></i>
              <span>{{ form.recipient.label }}</span>
            </label>
            {{ form.recipient }}
            {% if form.recipient.errors %}
              <div class="text-red-400 text-sm flex items-center space-x-1">
                <i data-lucide="alert-circle" class="h-4 w-4"></i>
                <span>{{ form.recipient.errors.0 }}</span>
              </div>
            {% endif %}
            <p class="text-xs text-muted-foreground">{{ form.recipient.help_text }}</p>
          </div>
        </div>

        <!-- Descrição -->
        <div class="space-y-2">
          <label for="{{ form.description.id_for_label }}" class="text-sm font-medium flex items-center space-x-2">
            <i data-lucide="file-text" class="h-4 w-4 text-primary"></i>
            <span>{{ form.description.label }}</span>
            <span class="text-red-400">*</span>
          </label>
          {{ form.description }}
          {% if form.description.errors %}
            <div class="text-red-400 text-sm flex items-center space-x-1">
              <i data-lucide="alert-circle" class="h-4 w-4"></i>
              <span>{{ form.description.errors.0 }}</span>
            </div>
          {% endif %}
          <p class="text-xs text-muted-foreground">{{ form.description.help_text }}</p>
        </div>
      </section>

      {% if form.non_field_errors %}
        <div class="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
          <div class="text-red-400 text-sm flex items-center space-x-2">
            <i data-lucide="alert-octagon" class="h-4 w-4"></i>
            <span>{{ form.non_field_errors.0 }}</span>
          </div>
        </div>
      {% endif %}

      <!-- Produtos -->
      <section class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="h-10 w-10 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg flex items-center justify-center">
              <i data-lucide="package" class="h-5 w-5 text-white"></i>
            </div>
            <div>
              <h2 class="text-xl font-semibold">Produtos</h2>
              <p class="text-sm text-muted-foreground">Adicione os produtos que estão saindo do estoque</p>
            </div>
          </div>
          <button type="button" id="add-item" class="inline-flex items-center space-x-2 bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            <i data-lucide="plus" class="h-4 w-4"></i>
            <span>Adicionar Produto</span>
          </button>
        </div>

        {{ items_formset.management_form }}
        {% if items_formset.non_form_errors %}
          <div class="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
            <div class="text-red-400 text-sm flex items-center space-x-2">
              <i data-lucide="alert-octagon" class="h-4 w-4"></i>
              <span>{{ items_formset.non_form_errors.0 }}</span>
            </div>
          </div>
        {% endif %}

        <div id="items-formset" class="space-y-4">
          {% for item_form in items_formset.forms %}
            {% include 'components/_outflow_item_form.html' with form=item_form %}
          {% endfor %}
        </div>

        <template id="item-form-template">
          {% include 'components/_outflow_item_form.html' with form=items_formset.empty_form %}
        </template>
      </section>

      <!-- Botões de Ação -->
      <div class="flex flex-wrap items-center justify-between pt-6 border-t border-border">
        <button type="submit" class="inline-flex items-center space-x-2 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700 text-white px-6 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg">
          <i data-lucide="save" class="h-4 w-4"></i>
          <span>Registrar Saída</span>
        </button>
        <a href="{% url 'outflow_list' %}" class="inline-flex items-center space-x-2 border border-border bg-background hover:bg-accent text-foreground px-4 py-2 rounded-lg transition-colors">
          <i data-lucide="x" class="h-4 w-4"></i>
          <span>Cancelar</span>
        </a>
      </div>
    </form>
  </div>
</div>

<script>
  document.addEventListener('DOMContentLoaded', function() {
    const addItemButton = document.getElementById('add-item');
    const formsetContainer = document.getElementById('items-formset');
    const totalFormsInput = document.getElementById('id_items-TOTAL_FORMS');
    const template = document.getElementById('item-form-template');

    function renderLucide() {
      if (window.lucide) {
        window.lucide.createIcons();
      }
    }

    function debounce(fn, delay) {
      let timeout;
      return (...args) => {
        window.clearTimeout(timeout);
        timeout = window.setTimeout(() => fn(...args), delay);
      };
    }

    function formatCurrency(value) {
      if (value === null || value === undefined || value === '') {
        return '';
      }
      const numeric = typeof value === 'number' ? value : parseFloat(value);
      if (Number.isNaN(numeric)) {
        return '';
      }
      return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(numeric);
    }

    function initializeRemoveButtons(scope) {
      scope.querySelectorAll('.remove-item').forEach((button) => {
        if (button.dataset.bound === 'true') {
          return;
        }
        button.dataset.bound = 'true';
        button.addEventListener('click', () => {
          const formWrapper = button.closest('[data-form-prefix]');
          if (!formWrapper) {
            return;
          }
          const deleteInput = formWrapper.querySelector('input[name$="-DELETE"]');
          if (deleteInput) {
            deleteInput.value = 'on';
          }
          formWrapper.classList.add('hidden');
        });
      });
    }

    async function loadProduct(productId) {
      try {
        const response = await fetch(`/api/v1/products/${productId}/`, {
          credentials: 'same-origin',
        });
        if (!response.ok) {
          throw new Error('Produto não encontrado');
        }
        return await response.json();
      } catch (error) {
        console.error(error);
        return null;
      }
    }

    function initializeProductSearch(scope) {
      if (!scope) {
        return;
      }

      const searchInput = scope.querySelector('[data-product-search]');
      const resultsContainer = scope.querySelector('[data-product-results]');
      const selectedContainer = scope.querySelector('[data-product-selected]');
      const hiddenInput = scope.querySelector('input[type="hidden"][name$="-product"]');
      
      if (!searchInput || !resultsContainer || !hiddenInput) {
        return;
      }

      if (searchInput.dataset.bound === 'true') {
        return;
      }
      searchInput.dataset.bound = 'true';

      const nameElement = selectedContainer ? selectedContainer.querySelector('[data-product-name]') : null;
      const codeElement = selectedContainer ? selectedContainer.querySelector('[data-product-code]') : null;
      const stockElement = selectedContainer ? selectedContainer.querySelector('[data-product-stock]') : null;
      const clearButton = selectedContainer ? selectedContainer.querySelector('[data-product-clear]') : null;
      const quantityInput = scope.querySelector('input[name$="-quantity"]');
      const notesInput = scope.querySelector('input[name$="-notes"]');
      const deleteInput = scope.querySelector('input[name$="-DELETE"]');
      const helperText = scope.querySelector('[data-product-helper]');

      if (deleteInput && deleteInput.value === 'on') {
        scope.classList.add('hidden');
      }

      let lastTerm = '';
      const fetchProducts = debounce(async (term) => {
        lastTerm = term;
        try {
          const response = await fetch(`/api/v1/products/?search=${encodeURIComponent(term)}`, {
            credentials: 'same-origin',
          });
          if (!response.ok) {
            throw new Error('Falha ao buscar produtos');
          }
          const payload = await response.json();
          if (lastTerm !== term) {
            return;
          }
          const products = Array.isArray(payload) ? payload : payload.results || [];
          renderResults(products);
        } catch (error) {
          console.error(error);
          renderResults([]);
        }
      }, 300);

      function renderResults(products) {
        resultsContainer.innerHTML = '';
        if (!products.length) {
          resultsContainer.innerHTML = '<div class="px-4 py-3 text-sm text-muted-foreground">Nenhum produto encontrado.</div>';
          resultsContainer.classList.remove('hidden');
          return;
        }

        products.forEach((product) => {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'flex w-full flex-col items-start space-y-1 rounded-md px-4 py-2 text-left hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary';
          const seriePart = product.serie_number ? ` · Série: ${product.serie_number}` : '';
          const costText = product.cost_price ? formatCurrency(product.cost_price) : 'Sem custo cadastrado';
          button.innerHTML = `
            <span class="font-medium text-foreground">${product.title}</span>
            <span class="text-xs text-muted-foreground">Código: ${product.id}${seriePart}</span>
            <span class="text-xs text-muted-foreground">Estoque: ${product.quantity} · Custo: ${costText}</span>
          `;
          button.addEventListener('click', () => selectProduct(product));
          resultsContainer.appendChild(button);
        });
        resultsContainer.classList.remove('hidden');
      }

      function selectProduct(product) {
        hiddenInput.value = product.id;
        resultsContainer.classList.add('hidden');
        searchInput.value = '';

        if (selectedContainer && nameElement && codeElement && stockElement) {
          nameElement.textContent = product.title;
          const details = [`Código: ${product.id}`];
          if (product.serie_number) {
            details.push(`Série: ${product.serie_number}`);
          }
          codeElement.textContent = details.join(' · ');
          stockElement.textContent = `Estoque disponível: ${product.quantity} · Custo: ${formatCurrency(product.cost_price)}`;
          selectedContainer.classList.remove('hidden');
        }

        if (helperText) {
          helperText.classList.add('hidden');
        }

        if (quantityInput && !quantityInput.value) {
          quantityInput.value = 1;
        }

        renderLucide();
      }

      if (clearButton) {
        clearButton.addEventListener('click', () => {
          hiddenInput.value = '';
          if (selectedContainer) {
            selectedContainer.classList.add('hidden');
          }
          if (helperText) {
            helperText.classList.remove('hidden');
          }
          if (nameElement) {
            nameElement.textContent = '';
          }
          if (codeElement) {
            codeElement.textContent = '';
          }
          if (stockElement) {
            stockElement.textContent = '';
          }
          searchInput.focus();
        });
      }

      searchInput.addEventListener('input', (event) => {
        const term = event.target.value.trim();
        if (term.length < 2) {
          resultsContainer.classList.add('hidden');
          return;
        }
        fetchProducts(term);
      });

      searchInput.addEventListener('focus', () => {
        if (resultsContainer.children.length) {
          resultsContainer.classList.remove('hidden');
        }
      });

      searchInput.addEventListener('blur', () => {
        window.setTimeout(() => resultsContainer.classList.add('hidden'), 200);
      });

      if (hiddenInput.value) {
        loadProduct(hiddenInput.value).then((product) => {
          if (product) {
            selectProduct(product);
          }
        });
      } else if (selectedContainer) {
        selectedContainer.classList.add('hidden');
        if (helperText) {
          helperText.classList.remove('hidden');
        }
      }
    }

    if (addItemButton) {
      addItemButton.addEventListener('click', () => {
        const formCount = parseInt(totalFormsInput.value, 10);
        const templateHtml = template.innerHTML.replace(/__prefix__/g, formCount);
        const wrapper = document.createElement('div');
        wrapper.innerHTML = templateHtml.trim();
        const newForm = wrapper.firstElementChild;
        formsetContainer.appendChild(newForm);
        totalFormsInput.value = formCount + 1;
        initializeRemoveButtons(newForm);
        initializeProductSearch(newForm);
        renderLucide();
      });
    }

    initializeRemoveButtons(formsetContainer);
    formsetContainer.querySelectorAll('[data-form-prefix]').forEach((formWrapper) => {
      initializeProductSearch(formWrapper);
    });
    renderLucide();
  });
</script>

{% endblock %}
"""

def main():
    template_path = os.path.join(
        os.path.dirname(__file__),
        'outflows',
        'templates',
        'outflow_create.html'
    )
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(template_path), exist_ok=True)
    
    # Write file with explicit mode
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(TEMPLATE_CONTENT)
    
    print(f"✅ Template criado com sucesso em: {template_path}")
    print(f"📊 Tamanho do arquivo: {len(TEMPLATE_CONTENT)} bytes")

if __name__ == '__main__':
    main()
