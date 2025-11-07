/**
 * PDV - Ponto de Venda
 * Sistema de vendas com múltiplos pagamentos
 */

document.addEventListener('DOMContentLoaded', function() {
  console.log('PDV JS carregado!');
  
  // Estado global da venda
  let saleData = parseJsonScript('sale-data');
  let availableCredit = 0;
  const paymentMethodsData = parseJsonScript('payment-methods-data') || [];
  
  console.log('Sale data:', saleData);
  console.log('Payment methods:', paymentMethodsData);
  
  // Seletores de elementos
  const customerSearch = document.querySelector('[data-customer-search]');
  const customerResults = document.querySelector('[data-customer-results]');
  const customerSelected = document.querySelector('[data-customer-selected]');
  const customerName = document.querySelector('[data-customer-name]');
  const customerDetails = document.querySelector('[data-customer-details]');
  
  const productSearch = document.querySelector('[data-product-search]');
  const productResults = document.querySelector('[data-product-results]');
  const productQuantity = document.querySelector('[data-product-quantity]');
  const addProductBtn = document.querySelector('[data-add-product-btn]');
  
  const itemsContainer = document.querySelector('[data-items-container]');
  const itemsCount = document.querySelector('[data-items-count]');
  const itemsBody = document.querySelector('[data-items-body]');
  
  const paymentMethodSelect = document.querySelector('[data-payment-method-select]');
  const cashFields = document.querySelector('[data-cash-fields]');
  const otherFields = document.querySelector('[data-other-fields]');
  const cashTendered = document.querySelector('[data-cash-tendered]');
  const paymentAmount = document.querySelector('[data-payment-amount]');
  const addPaymentBtn = document.querySelector('[data-add-payment-btn]');
  const paymentsContainer = document.querySelector('[data-payments-container]');
  const paymentsList = document.querySelector('[data-payments-list]');
  
  const finalizeBtn = document.querySelector('[data-finalize-btn]');
  const cancelSaleBtn = document.querySelector('[data-cancel-sale-btn]');
  const diffModal = document.querySelector('[data-diff-modal]');
  const diffMessage = document.querySelector('[data-diff-message]');
  const diffOptions = document.querySelector('[data-diff-options]');
  const diffCancel = document.querySelector('[data-diff-cancel]');
  const successModal = document.querySelector('[data-success-modal]');
  
  // Debug: verificar se elementos foram encontrados
  console.log('Elementos encontrados:', {
    customerSearch: !!customerSearch,
    customerResults: !!customerResults,
    productSearch: !!productSearch,
    productResults: !!productResults,
    itemsContainer: !!itemsContainer,
    paymentsContainer: !!paymentsContainer,
    paymentMethodSelect: !!paymentMethodSelect,
    addPaymentBtn: !!addPaymentBtn,
    cashFields: !!cashFields,
    otherFields: !!otherFields
  });
  
  // Formatador de moeda
  const currencyFormatter = new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  });
  
  // Produto selecionado temporariamente
  let selectedProduct = null;
  
  // Utilitários
  function parseJsonScript(id) {
    const element = document.getElementById(id);
    if (!element) return null;
    try {
      return JSON.parse(element.textContent);
    } catch (error) {
      console.error('Erro ao parsear JSON:', error);
      return null;
    }
  }
  
  function debounce(fn, delay) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn(...args), delay);
    };
  }
  
  function formatCurrency(value) {
    if (value === null || value === undefined || value === '') return 'R$ 0,00';
    const numeric = typeof value === 'number' ? value : parseFloat(value);
    if (isNaN(numeric)) return 'R$ 0,00';
    return currencyFormatter.format(numeric);
  }
  
  function formatCpf(value) {
    if (!value) return '';
    const digits = String(value).replace(/\D/g, '');
    if (digits.length !== 11) return value;
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
  }
  
  function formatPhone(value) {
    if (!value) return '';
    const digits = String(value).replace(/\D/g, '');
    if (digits.length === 11) {
      return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
    }
    if (digits.length === 10) {
      return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
    }
    return value;
  }
  
  function renderLucide() {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  function resetSaleUI() {
    if (customerSearch) customerSearch.value = '';
    customerResults?.classList.add('hidden');
    customerSelected?.classList.add('hidden');
    if (customerName) customerName.textContent = '';
    if (customerDetails) customerDetails.textContent = '';
    if (productSearch) productSearch.value = '';
    productResults?.classList.add('hidden');
    if (productQuantity) productQuantity.value = '1';
    selectedProduct = null;
    if (paymentMethodSelect) paymentMethodSelect.value = '';
    cashFields?.classList.add('hidden');
    otherFields?.classList.add('hidden');
    if (cashTendered) cashTendered.value = '';
    if (paymentAmount) paymentAmount.value = '';
    addProductBtn && (addProductBtn.disabled = true);
    addPaymentBtn && (addPaymentBtn.disabled = true);
  }
  
  function getCsrfToken() {
    // Busca em cookies primeiro
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='));
    
    if (cookieValue) {
      return cookieValue.split('=')[1];
    }
    
    // Fallback para meta tag
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
      return metaTag.getAttribute('content');
    }
    
    // Fallback para input hidden
    const inputTag = document.querySelector('[name=csrfmiddlewaretoken]');
    if (inputTag) {
      return inputTag.value;
    }
    
    console.warn('CSRF token não encontrado');
    return '';
  }
  
  async function apiCall(url, data) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    if (!result.success && !result.requires_resolution) {
      throw new Error(result.error || 'Erro desconhecido');
    }
    return result;
  }
  
  // Atualização da UI
  function updateSaleUI(newSaleData) {
    saleData = newSaleData;
    renderItems();
    renderPayments();
    updateSummary();
    updateCreditUI(availableCredit);
    renderLucide();
  }
  
  function renderItems() {
    if (!saleData.items || saleData.items.length === 0) {
      itemsContainer.innerHTML = `
        <div class="text-center py-8 text-muted-foreground">
          <i data-lucide="inbox" class="h-12 w-12 mx-auto mb-2 opacity-50"></i>
          <p class="text-sm">Nenhum item adicionado</p>
        </div>
      `;
      itemsCount.textContent = '0 itens';
      return;
    }
    
    const totalQty = saleData.items.reduce((sum, item) => sum + item.quantity, 0);
    itemsCount.textContent = `${totalQty} ${totalQty === 1 ? 'item' : 'itens'}`;
    
    const tableHtml = `
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-border">
              <th class="text-left py-2 px-2 text-sm font-medium text-muted-foreground">Produto</th>
              <th class="text-center py-2 px-2 text-sm font-medium text-muted-foreground w-24">Qtd</th>
              <th class="text-right py-2 px-2 text-sm font-medium text-muted-foreground w-28">Preço</th>
              <th class="text-right py-2 px-2 text-sm font-medium text-muted-foreground w-28">Total</th>
              <th class="w-12"></th>
            </tr>
          </thead>
          <tbody>
            ${saleData.items.map(item => `
              <tr class="border-b border-border/50">
                <td class="py-2 px-2">
                  <div class="text-sm font-medium">${item.product_name}</div>
                  <div class="text-xs text-muted-foreground">Cód: ${item.product_code}</div>
                </td>
                <td class="py-2 px-2">
                  <input
                    type="number"
                    min="0"
                    value="${item.quantity}"
                    class="w-16 h-8 text-center rounded border border-input bg-background text-sm"
                    data-item-qty="${item.id}"
                  >
                </td>
                <td class="py-2 px-2 text-right text-sm">${formatCurrency(item.unit_price)}</td>
                <td class="py-2 px-2 text-right font-medium">${formatCurrency(item.line_total)}</td>
                <td class="py-2 px-2 text-center">
                  <button
                    type="button"
                    class="text-red-500 hover:text-red-700"
                    data-remove-item="${item.id}"
                  >
                    <i data-lucide="trash-2" class="h-4 w-4"></i>
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
    
    itemsContainer.innerHTML = tableHtml;
    
    // Adiciona listeners para edição de quantidade
    document.querySelectorAll('[data-item-qty]').forEach(input => {
      input.addEventListener('change', async (e) => {
        const itemId = e.target.dataset.itemQty;
        const quantity = parseInt(e.target.value, 10);
        try {
          const result = await apiCall('/pos/update-item/', { item_id: itemId, quantity });
          updateSaleUI(result.sale);
        } catch (error) {
          alert('Erro ao atualizar quantidade: ' + error.message);
        }
      });
    });
    
    // Adiciona listeners para remoção de itens
    document.querySelectorAll('[data-remove-item]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const itemId = e.currentTarget.dataset.removeItem;
        if (confirm('Remover este item?')) {
          try {
            const result = await apiCall('/pos/remove-item/', { item_id: itemId });
            updateSaleUI(result.sale);
          } catch (error) {
            alert('Erro ao remover item: ' + error.message);
          }
        }
      });
    });
  }
  
  function renderPayments() {
    if (!saleData.payments || saleData.payments.length === 0) {
      paymentsContainer.innerHTML = `
        <div class="text-center py-4 text-muted-foreground">
          <p class="text-sm">Nenhum pagamento adicionado</p>
        </div>
      `;
      return;
    }
    
    const paymentsHtml = `
      <div class="space-y-2">
        ${saleData.payments.map(payment => `
          <div class="flex items-center justify-between p-3 rounded-lg border border-border bg-background">
            <div class="flex-1">
              <div class="text-sm font-medium">${payment.payment_method_name}</div>
              <div class="text-xs text-muted-foreground">
                ${payment.cash_tendered ? `Recebido: ${formatCurrency(payment.cash_tendered)} | Troco: ${formatCurrency(payment.change_given)}` : ''}
              </div>
            </div>
            <div class="flex items-center space-x-3">
              <span class="font-medium text-green-500">${formatCurrency(payment.amount_applied)}</span>
              <button
                type="button"
                class="text-red-500 hover:text-red-700"
                data-remove-payment="${payment.id}"
              >
                <i data-lucide="x" class="h-4 w-4"></i>
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
    
    paymentsContainer.innerHTML = paymentsHtml;
    
    // Adiciona listeners para remoção de pagamentos
    document.querySelectorAll('[data-remove-payment]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const paymentId = e.currentTarget.dataset.removePayment;
        if (confirm('Remover este pagamento?')) {
          try {
            const result = await apiCall('/pos/remove-payment/', { payment_id: paymentId });
            updateSaleUI(result.sale);
          } catch (error) {
            alert('Erro ao remover pagamento: ' + error.message);
          }
        }
      });
    });
  }
  
  function updateSummary() {
    const summarySubtotal = document.querySelectorAll('[data-summary-subtotal]');
    const summaryDiscounts = document.querySelectorAll('[data-summary-discounts]');
    const summaryFees = document.querySelectorAll('[data-summary-fees]');
    const summaryTotal = document.querySelectorAll('[data-summary-total]');
    const summaryPaid = document.querySelectorAll('[data-summary-paid]');
    const summaryRemaining = document.querySelectorAll('[data-summary-remaining]');
    
    // Atualiza todos os elementos com data-summary-subtotal (header e outros)
    summarySubtotal.forEach(el => el.textContent = formatCurrency(saleData.subtotal));
    summaryDiscounts.forEach(el => el.textContent = formatCurrency(saleData.discount_total || 0));
    summaryFees.forEach(el => el.textContent = formatCurrency(saleData.fee_total || 0));
    summaryTotal.forEach(el => el.textContent = formatCurrency(saleData.total));
    summaryPaid.forEach(el => el.textContent = formatCurrency(saleData.total_paid));
    summaryRemaining.forEach(el => el.textContent = formatCurrency(saleData.remaining));
  }
  
  function updateSummaryWithPotentialFee(feePercentage, feePayer) {
    // Calcula e mostra a taxa potencial quando um método é selecionado
    const summaryFees = document.querySelectorAll('[data-summary-fees]');
    const summaryTotal = document.querySelectorAll('[data-summary-total]');
    const summaryRemaining = document.querySelectorAll('[data-summary-remaining]');
    
    let potentialFee = 0;
    let newTotal = parseFloat(saleData.total) || 0;
    let newRemaining = parseFloat(saleData.remaining) || 0;
    
    // Calcula valor base (subtotal - desconto)
    const baseValue = (parseFloat(saleData.subtotal) || 0) - (parseFloat(saleData.discount_total) || 0);
    
    if (feePercentage > 0 && feePayer === 'customer' && baseValue > 0) {
      // Calcula taxa sobre o valor base da venda
      potentialFee = baseValue * (feePercentage / 100);
      newTotal = newTotal + potentialFee;
      newRemaining = newTotal - (parseFloat(saleData.total_paid) || 0);
    }
    
    // Atualiza com valores potenciais (temporários)
    summaryFees.forEach(el => {
      const currentFee = parseFloat(saleData.fee_total) || 0;
      const totalFee = currentFee + potentialFee;
      el.textContent = formatCurrency(totalFee);
      
      // Adiciona indicador visual de que é uma previsão
      if (potentialFee > 0) {
        el.classList.add('animate-pulse');
      } else {
        el.classList.remove('animate-pulse');
      }
    });
    
    summaryTotal.forEach(el => {
      el.textContent = formatCurrency(newTotal);
      if (potentialFee > 0) {
        el.classList.add('animate-pulse');
      } else {
        el.classList.remove('animate-pulse');
      }
    });
    
    summaryRemaining.forEach(el => {
      el.textContent = formatCurrency(newRemaining);
      if (potentialFee > 0) {
        el.classList.add('animate-pulse');
      } else {
        el.classList.remove('animate-pulse');
      }
    });
  }
  
  // Busca de clientes
  const searchCustomers = debounce(async (term) => {
    if (term.length < 2) {
      customerResults.classList.add('hidden');
      return;
    }
    
    try {
      console.log('Buscando clientes:', term);
      const response = await fetch(`/api/v1/customers/?search=${encodeURIComponent(term)}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Dados recebidos:', data);
      
      const customers = Array.isArray(data) ? data : data.results || [];
      
      if (customers.length === 0) {
        customerResults.innerHTML = '<div class="px-4 py-3 text-sm text-muted-foreground">Nenhum cliente encontrado.</div>';
      } else {
        customerResults.innerHTML = customers.map(customer => `
          <button
            type="button"
            class="flex w-full flex-col items-start space-y-1 rounded-md px-4 py-2 text-left hover:bg-primary/10"
            data-select-customer="${customer.id}"
          >
            <span class="font-medium">${customer.full_name}</span>
            <span class="text-xs text-muted-foreground">${formatCpf(customer.cpf) || 'CPF não informado'} · ${formatPhone(customer.phone)}</span>
          </button>
        `).join('');
        
        customerResults.querySelectorAll('[data-select-customer]').forEach(btn => {
          btn.addEventListener('click', async () => {
            const customerId = btn.dataset.selectCustomer;
            try {
              const result = await apiCall('/pos/set-customer/', { customer_id: customerId });
              
              // Atualiza estado da venda
              saleData = result.sale;
              
              // Atualiza crédito disponível
              if (result.available_credit !== undefined) {
                updateCreditUI(parseFloat(result.available_credit) || 0);
              }
              
              // Busca os dados do cliente selecionado
              const customer = customers.find(c => c.id == customerId);
              
              if (customerName && customerDetails && customerSelected) {
                customerName.textContent = result.sale.customer_name || customer.full_name;
                customerDetails.textContent = formatPhone(customer.phone) || 'Telefone não informado';
                customerSelected.classList.remove('hidden');
              }
              
              customerResults.classList.add('hidden');
              customerSearch.value = '';
            } catch (error) {
              alert('Erro ao definir cliente: ' + error.message);
            }
          });
        });
      }
      
      customerResults.classList.remove('hidden');
    } catch (error) {
      console.error('Erro ao buscar clientes:', error);
      customerResults.innerHTML = `<div class="px-4 py-3 text-sm text-red-500">Erro ao buscar clientes: ${error.message}</div>`;
      customerResults.classList.remove('hidden');
    }
  }, 300);
  
  customerSearch?.addEventListener('input', (e) => searchCustomers(e.target.value.trim()));
  customerSearch?.addEventListener('blur', () => {
    setTimeout(() => customerResults?.classList.add('hidden'), 200);
  });
  
  // Busca de produtos
  const searchProducts = debounce(async (term) => {
    if (term.length < 2) {
      productResults.classList.add('hidden');
      return;
    }
    
    try {
      console.log('Buscando produtos:', term);
      const response = await fetch(`/api/v1/products/?search=${encodeURIComponent(term)}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Dados recebidos:', data);
      
      const products = Array.isArray(data) ? data : data.results || [];
      
      if (products.length === 0) {
        productResults.innerHTML = '<div class="px-4 py-3 text-sm text-muted-foreground">Nenhum produto encontrado.</div>';
      } else {
        productResults.innerHTML = products.map(product => {
          const hasStock = product.quantity > 0;
          const stockClass = hasStock ? 'hover:bg-primary/10 cursor-pointer' : 'bg-red-500/10 cursor-not-allowed opacity-60';
          const stockBadge = hasStock 
            ? `<span class="text-xs text-green-500">Estoque: ${product.quantity}</span>`
            : `<span class="text-xs text-red-500 font-semibold">⚠️ SEM ESTOQUE</span>`;
          
          return `
            <button
              type="button"
              class="flex w-full flex-col items-start space-y-1 rounded-md px-4 py-2 text-left ${stockClass}"
              data-select-product='${JSON.stringify(product)}'
              ${!hasStock ? 'disabled' : ''}
            >
              <span class="font-medium ${!hasStock ? 'text-muted-foreground' : ''}">${product.title}</span>
              <div class="flex items-center gap-2">
                <span class="text-xs text-muted-foreground">Cód: ${product.id}</span>
                ${stockBadge}
              </div>
              <span class="text-xs font-medium ${!hasStock ? 'text-muted-foreground' : 'text-green-500'}">${formatCurrency(product.selling_price)}</span>
            </button>
          `;
        }).join('');
        
        productResults.querySelectorAll('[data-select-product]:not([disabled])').forEach(btn => {
          btn.addEventListener('click', () => {
            selectedProduct = JSON.parse(btn.dataset.selectProduct);
            productSearch.value = selectedProduct.title;
            productResults.classList.add('hidden');
            addProductBtn.disabled = false;
            productQuantity.max = selectedProduct.quantity; // Define quantidade máxima
            productQuantity.focus();
          });
        });
      }
      
      productResults.classList.remove('hidden');
    } catch (error) {
      console.error('Erro ao buscar produtos:', error);
      productResults.innerHTML = `<div class="px-4 py-3 text-sm text-red-500">Erro ao buscar produtos: ${error.message}</div>`;
      productResults.classList.remove('hidden');
    }
  }, 300);
  
  productSearch?.addEventListener('input', (e) => {
    selectedProduct = null;
    addProductBtn.disabled = true;
    searchProducts(e.target.value.trim());
  });
  
  productSearch?.addEventListener('blur', () => {
    setTimeout(() => productResults?.classList.add('hidden'), 200);
  });
  
  // Adicionar produto
  addProductBtn?.addEventListener('click', async () => {
    if (!selectedProduct) return;
    
    const quantity = parseInt(productQuantity.value, 10) || 1;
    
    // Validação de estoque
    if (selectedProduct.quantity <= 0) {
      alert('❌ Este produto está sem estoque disponível.');
      return;
    }
    
    if (quantity > selectedProduct.quantity) {
      alert(`❌ Quantidade solicitada (${quantity}) excede o estoque disponível (${selectedProduct.quantity}).`);
      productQuantity.value = selectedProduct.quantity;
      return;
    }
    
    if (quantity <= 0) {
      alert('❌ A quantidade deve ser maior que zero.');
      productQuantity.value = 1;
      return;
    }
    
    try {
      const result = await apiCall('/pos/add-item/', {
        product_id: selectedProduct.id,
        quantity
      });
      
      updateSaleUI(result.sale);
      
      // Limpa campos
      productSearch.value = '';
      productQuantity.value = 1;
      selectedProduct = null;
      addProductBtn.disabled = true;
      productSearch.focus();
    } catch (error) {
      alert('Erro ao adicionar produto: ' + error.message);
    }
  });
  
  // Método de pagamento
  paymentMethodSelect?.addEventListener('change', (e) => {
    const methodId = e.target.value;
    const selectedOption = e.target.options[e.target.selectedIndex];
    const methodName = selectedOption?.dataset.name || '';
    const feePercentageRaw = selectedOption?.dataset.feePercentage || '0';
    const feePercentage = parseFloat(feePercentageRaw);
    const feePayer = selectedOption?.dataset.feePayer || '';
    
    console.log('Método selecionado:', { 
      methodId, 
      methodName, 
      feePercentageRaw, 
      feePercentage, 
      feePayer 
    });
    
    if (!methodId) {
      cashFields.classList.add('hidden');
      otherFields.classList.add('hidden');
      addPaymentBtn.disabled = true;
      // Restaura valores originais no resumo
      updateSummary();
      return;
    }
    
    const isCash = methodName.toLowerCase().includes('dinheiro');
    
    // Calcula valor com taxa se cliente paga
    // A taxa é calculada sobre o SUBTOTAL - DESCONTO (valor base da venda)
    const baseValue = (parseFloat(saleData.subtotal) || 0) - (parseFloat(saleData.discount_total) || 0);
    let remainingWithFee = parseFloat(saleData.remaining) || 0;
    let feeAmount = 0;
    
    console.log('Valores:', { 
      subtotal: saleData.subtotal, 
      discount: saleData.discount_total, 
      baseValue, 
      remaining: saleData.remaining 
    });
    
    if (feePercentage > 0 && feePayer === 'customer' && baseValue > 0) {
      // Cliente paga a taxa - calculada sobre o valor base da venda
      feeAmount = baseValue * (feePercentage / 100);
      // O valor a pagar é o restante + taxa
      remainingWithFee = remainingWithFee + feeAmount;
      
      console.log('Calculando taxa:', { feeAmount, remainingWithFee });
      
      // Atualiza resumo com valores potenciais
      updateSummaryWithPotentialFee(feePercentage, feePayer);
    } else {
      // Restaura valores originais no resumo
      updateSummary();
    }
    
    if (isCash) {
      cashFields.classList.remove('hidden');
      otherFields.classList.add('hidden');
      cashTendered.value = '';
      cashTendered.focus();
    } else {
      cashFields.classList.add('hidden');
      otherFields.classList.remove('hidden');
      
      // Preenche com valor + taxa (se houver)
      paymentAmount.value = remainingWithFee.toFixed(2);
      
      // Mostra aviso se há taxa
      if (feePercentage > 0 && feePayer === 'customer') {
        const originalValue = parseFloat(saleData.remaining).toFixed(2);
        const feeValue = feeAmount.toFixed(2);
        const totalWithFee = remainingWithFee.toFixed(2);
        paymentAmount.title = `Valor da venda: R$ ${originalValue}\nTaxa ${feePercentage}%: R$ ${feeValue}\nTotal a pagar: R$ ${totalWithFee}`;
        
        // Adiciona visual feedback
        paymentAmount.classList.add('border-orange-500', 'bg-orange-500/10');
        
        // Remove classes depois que o usuário focar
        paymentAmount.addEventListener('focus', function removeFeedback() {
          this.classList.remove('border-orange-500', 'bg-orange-500/10');
          this.removeEventListener('focus', removeFeedback);
        });
      } else {
        paymentAmount.title = '';
        paymentAmount.classList.remove('border-orange-500', 'bg-orange-500/10');
      }
      
      paymentAmount.focus();
    }
    
    addPaymentBtn.disabled = false;
  });
  
  // Adicionar pagamento
  addPaymentBtn?.addEventListener('click', async () => {
    const methodId = paymentMethodSelect.value;
    if (!methodId) return;
    
    const selectedOption = paymentMethodSelect.options[paymentMethodSelect.selectedIndex];
    const methodName = selectedOption?.dataset.name || '';
    const isCash = methodName.toLowerCase().includes('dinheiro');
    
    try {
      let data = { payment_method_id: methodId };
      
      if (isCash) {
        const tendered = parseFloat(cashTendered.value);
        if (!tendered || tendered <= 0) {
          alert('Informe o valor recebido');
          return;
        }
        data.cash_tendered = tendered;
      } else {
        const amount = parseFloat(paymentAmount.value);
        if (!amount || amount <= 0) {
          alert('Informe o valor do pagamento');
          return;
        }
        data.amount = amount;
      }
      
      const result = await apiCall('/pos/add-payment/', data);
      updateSaleUI(result.sale);
      
      // Limpa campos
      paymentMethodSelect.value = '';
      cashFields.classList.add('hidden');
      otherFields.classList.add('hidden');
      addPaymentBtn.disabled = true;
      
      // Remove animação pulse dos valores (se houver)
      document.querySelectorAll('[data-summary-fees], [data-summary-total], [data-summary-remaining]').forEach(el => {
        el.classList.remove('animate-pulse');
      });
    } catch (error) {
      alert('Erro ao adicionar pagamento: ' + error.message);
    }
  });
  
  // Finalizar venda
  cancelSaleBtn?.addEventListener('click', async () => {
    if (!confirm('Cancelar a venda atual e limpar o formulário?')) {
      return;
    }

    cancelSaleBtn.disabled = true;

    try {
      const result = await apiCall('/pos/cancel-sale/', {});
      availableCredit = parseFloat(result.available_credit) || 0;
      updateSaleUI(result.sale);
      resetSaleUI();
    } catch (error) {
      alert('Erro ao cancelar venda: ' + error.message);
    } finally {
      cancelSaleBtn.disabled = false;
    }
  });

  finalizeBtn?.addEventListener('click', async () => {
    if (!saleData.items || saleData.items.length === 0) {
      alert('Adicione pelo menos um item à venda');
      return;
    }
    
    try {
      const result = await apiCall('/pos/finalize/', {});
      
      if (result.success) {
        // Armazena o ID da venda para impressão
        window.lastSaleId = result.sale_id;
        
        successModal.classList.remove('hidden');
        successModal.classList.add('flex');
      } else if (result.requires_resolution) {
        showDiffModal(result);
      }
    } catch (error) {
      alert('Erro ao finalizar venda: ' + error.message);
    }
  });
  
  // Botão de imprimir recibo no modal de sucesso
  const printReceiptBtn = document.querySelector('[data-print-receipt]');
  printReceiptBtn?.addEventListener('click', () => {
    if (window.lastSaleId) {
      // Abre o recibo em nova aba/janela com autoprint
      const url = `/pos/sales/${window.lastSaleId}/receipt/?autoprint=1`;
      window.open(url, '_blank', 'width=400,height=600');
    }
  });
  
  function showDiffModal(result) {
    const difference = parseFloat(result.difference);
    const type = result.type;
    
    if (type === 'underpaid') {
      diffMessage.textContent = `Faltam ${formatCurrency(difference)} para fechar a venda. Escolha uma opção:`;
      diffOptions.innerHTML = `
        <button
          type="button"
          class="w-full bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg font-medium"
          data-resolve="apply_discount"
        >
          Aplicar Desconto
        </button>
        <button
          type="button"
          class="w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium"
          data-resolve="generate_debit"
        >
          Gerar Débito para o Cliente
        </button>
      `;
    } else {
      diffMessage.textContent = `Há um excesso de ${formatCurrency(difference)}. Escolha uma opção:`;
      diffOptions.innerHTML = `
        <button
          type="button"
          class="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium"
          data-resolve="generate_credit"
        >
          Gerar Crédito para o Cliente
        </button>
        <button
          type="button"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium"
          data-resolve="edit"
        >
          Editar Venda
        </button>
      `;
    }
    
    diffOptions.querySelectorAll('[data-resolve]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const resolution = btn.dataset.resolve;
        if (resolution === 'edit') {
          diffModal.classList.add('hidden');
          diffModal.classList.remove('flex');
          return;
        }
        
        try {
          const result = await apiCall('/pos/finalize/', { resolution });
          if (result.success) {
            diffModal.classList.add('hidden');
            diffModal.classList.remove('flex');
            successModal.classList.remove('hidden');
            successModal.classList.add('flex');
          }
        } catch (error) {
          alert('Erro ao finalizar: ' + error.message);
        }
      });
    });
    
    diffModal.classList.remove('hidden');
    diffModal.classList.add('flex');
  }
  
  diffCancel?.addEventListener('click', () => {
    diffModal.classList.add('hidden');
    diffModal.classList.remove('flex');
  });
  
  // ============================================================================
  // GERENCIAMENTO DE CRÉDITO
  // ============================================================================
  
  // Elementos do crédito
  const creditAvailableContainer = document.querySelector('[data-credit-available-container]');
  const creditAvailableDisplay = document.querySelector('[data-credit-available]');
  const useCreditBtn = document.querySelector('[data-use-credit-btn]');
  
  // Modal de crédito
  const creditModal = document.getElementById('credit-modal');
  const creditModalOverlay = document.getElementById('credit-modal-overlay');
  const closeCreditModal = document.getElementById('close-credit-modal');
  const modalCreditAvailable = document.querySelector('[data-modal-credit-available]');
  const modalRemaining = document.querySelector('[data-modal-remaining]');
  const creditAmountInput = document.querySelector('[data-credit-amount-input]');
  const creditError = document.querySelector('[data-credit-error]');
  const creditCancel = document.querySelector('[data-credit-cancel]');
  const creditApply = document.querySelector('[data-credit-apply]');
  
  function updateCreditUI(credit) {
    availableCredit = parseFloat(credit) || 0;
    
    if (creditAvailableDisplay) {
      creditAvailableDisplay.textContent = formatCurrency(availableCredit);
    }
    
    // Mostra/oculta o container de crédito
    if (creditAvailableContainer) {
      const isGeneric = saleData.customer && saleData.customer.is_generic;
      if (availableCredit > 0 && !isGeneric) {
        creditAvailableContainer.classList.remove('hidden');
      } else {
        creditAvailableContainer.classList.add('hidden');
      }
    }
    
    // Habilita/desabilita botão de usar crédito
    if (useCreditBtn) {
      const remaining = parseFloat(saleData.total || 0) - parseFloat(saleData.total_paid || 0);
      useCreditBtn.disabled = availableCredit <= 0 || remaining <= 0;
    }
  }
  
  // Carrega crédito disponível inicial
  const creditDataElement = document.getElementById('available-credit-data');
  if (creditDataElement) {
    try {
      availableCredit = parseFloat(creditDataElement.textContent) || 0;
      updateCreditUI(availableCredit);
    } catch (error) {
      console.error('Erro ao carregar crédito:', error);
    }
  }
  
  function openCreditModal() {
    if (!creditModal || !creditModalOverlay) return;
    
    const remaining = parseFloat(saleData.total || 0) - parseFloat(saleData.total_paid || 0);
    
    // Atualiza valores no modal
    if (modalCreditAvailable) {
      modalCreditAvailable.textContent = formatCurrency(availableCredit);
    }
    if (modalRemaining) {
      modalRemaining.textContent = formatCurrency(remaining);
    }
    
    // Limpa input e erro
    if (creditAmountInput) {
      creditAmountInput.value = '';
      creditAmountInput.max = Math.min(availableCredit, remaining).toFixed(2);
    }
    if (creditError) {
      creditError.classList.add('hidden');
      creditError.textContent = '';
    }
    
    creditModal.classList.remove('hidden');
    creditModalOverlay.classList.remove('hidden');
    
    // Foca no input
    creditAmountInput?.focus();
  }
  
  function closeCreditModalFn() {
    if (!creditModal || !creditModalOverlay) return;
    creditModal.classList.add('hidden');
    creditModalOverlay.classList.add('hidden');
  }
  
  // Event listeners do modal de crédito
  useCreditBtn?.addEventListener('click', openCreditModal);
  closeCreditModal?.addEventListener('click', closeCreditModalFn);
  creditCancel?.addEventListener('click', closeCreditModalFn);
  creditModalOverlay?.addEventListener('click', closeCreditModalFn);
  
  creditApply?.addEventListener('click', async () => {
    if (creditError) {
      creditError.classList.add('hidden');
      creditError.textContent = '';
    }
    
    const remaining = parseFloat(saleData.total || 0) - parseFloat(saleData.total_paid || 0);
    let amount = parseFloat(creditAmountInput?.value || 0);
    
    // Se não informou valor, usa o máximo possível
    if (!amount || amount <= 0) {
      amount = Math.min(availableCredit, remaining);
    }
    
    // Validações
    if (amount <= 0) {
      if (creditError) {
        creditError.textContent = 'Informe um valor válido maior que zero.';
        creditError.classList.remove('hidden');
      }
      return;
    }
    
    if (amount > availableCredit) {
      if (creditError) {
        creditError.textContent = `Valor maior que o crédito disponível (${formatCurrency(availableCredit)}).`;
        creditError.classList.remove('hidden');
      }
      return;
    }
    
    if (amount > remaining) {
      if (creditError) {
        creditError.textContent = `Valor maior que o restante a pagar (${formatCurrency(remaining)}).`;
        creditError.classList.remove('hidden');
      }
      return;
    }
    
    try {
      const result = await apiCall('/pos/apply-credit/', { amount });
      
      if (result.success) {
        // Atualiza estado da venda
        saleData = result.sale;
        availableCredit = parseFloat(result.available_credit) || 0;
        
        // Atualiza UI
        updateSaleUI(saleData);
        updateCreditUI(availableCredit);
        
        // Fecha modal
        closeCreditModalFn();
        
        // Mensagem de sucesso
        console.log('Crédito aplicado com sucesso!');
      } else {
        if (creditError) {
          creditError.textContent = result.error || 'Erro ao aplicar crédito.';
          creditError.classList.remove('hidden');
        }
      }
    } catch (error) {
      if (creditError) {
        creditError.textContent = error.message || 'Erro ao aplicar crédito.';
        creditError.classList.remove('hidden');
      }
    }
  });
  
  // Inicialização
  updateSaleUI(saleData);
  renderLucide();
});
