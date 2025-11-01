# 🎯 Guia Rápido - Sistema PDV

## Acesso Rápido
**URL Principal**: http://localhost:8000/pos/

## Primeiros Passos

### 1. Certifique-se de ter:
- ✅ Cliente genérico criado (automático)
- ✅ Métodos de pagamento cadastrados
- ✅ Produtos com preço de venda

### 2. Criar Métodos de Pagamento (se necessário)
Acesse: `/admin/outflows/paymentmethod/` e crie:
- Dinheiro (desconto 0%)
- PIX (desconto 5%)
- Cartão de Débito (desconto 2%)
- Cartão de Crédito (desconto 0%)

## Fluxo Básico de Venda

### Cenário 1: Venda Simples com Dinheiro
1. Acesse `/pos/`
2. Busque produto (código, série ou nome)
3. Informe quantidade e clique "Adicionar"
4. Selecione "Dinheiro" como método
5. Informe valor recebido (ex: R$ 100,00)
6. Clique "Adicionar Pagamento"
7. Veja o troco calculado automaticamente
8. Clique "Finalizar Venda"

### Cenário 2: Múltiplos Pagamentos
1. Venda total: R$ 350,00
2. Cliente paga:
   - R$ 200,00 em PIX
   - R$ 150,00 no Cartão
3. Sistema soma automaticamente
4. Finaliza quando total_paid = total

### Cenário 3: Pagamento Menor (Gerar Débito)
1. Total da venda: R$ 500,00
2. Cliente paga: R$ 300,00
3. Ao finalizar, modal pergunta:
   - "Aplicar Desconto" → Reduz total para R$ 300,00
   - "Gerar Débito" → Cria débito de R$ 200,00 para o cliente

### Cenário 4: Pagamento Maior (Gerar Crédito)
1. Total da venda: R$ 100,00
2. Cliente paga: R$ 150,00 (não em dinheiro)
3. Modal pergunta:
   - "Gerar Crédito" → Cliente fica com R$ 50,00 de crédito
   - "Editar Venda" → Volta para ajustar

### Cenário 5: Cliente Específico
1. Use a busca no topo da página
2. Digite nome, CPF ou telefone
3. Selecione o cliente
4. Continue a venda normalmente
5. Crédito/débito será vinculado a esse cliente

## Atalhos e Dicas

### Interface
- **Busca de Produto**: Mínimo 2 caracteres
- **Busca de Cliente**: Mínimo 2 caracteres
- **Quantidade**: Pode editar direto na tabela
- **Remover Item**: Ícone de lixeira
- **Remover Pagamento**: Ícone X

### Resumo em Tempo Real
- **Subtotal**: Soma dos itens
- **Desconto**: Manual + diferença de finalização
- **Total**: Subtotal - Desconto
- **Pago**: Soma dos pagamentos aplicados
- **Troco**: Apenas de dinheiro
- **Restante**: Total - Pago

### Regras de Negócio
- ✅ Troco só para "Dinheiro"
- ✅ Pode misturar métodos de pagamento
- ✅ Desconto automático por método (ex: PIX 5%)
- ✅ Desconto manual ao finalizar com diferença
- ✅ Débito = cliente deve
- ✅ Crédito = cliente tem a receber

## Visualizar Lançamentos
**URL**: `/pos/ledger/`

Filtros disponíveis:
- Tipo: Crédito / Débito
- Status: Em aberto / Liquidado / Cancelado
- Cliente: Específico

## Admin Django
**Vendas PDV**: `/admin/pos/sale/`
- Ver histórico completo
- Editar vendas em rascunho
- Ver itens e pagamentos inline

**Lançamentos**: `/admin/pos/ledgerentry/`
- Marcar como liquidado (ação em lote)
- Marcar como cancelado (ação em lote)
- Filtrar por tipo, status, cliente

## Troubleshooting

### "Nenhum método de pagamento"
→ Cadastre em `/admin/outflows/paymentmethod/`

### "Erro ao adicionar item"
→ Verifique se produto tem `selling_price` cadastrado

### "Venda não finaliza"
→ Adicione pelo menos 1 item e 1 pagamento

### Troco não calculado
→ Certifique-se de selecionar método "Dinheiro"

## Ações Rápidas

### Cancelar Venda
- Recarregue a página (F5)
- Nova venda draft é criada automaticamente

### Nova Venda Após Finalizar
- Clique "Nova Venda" no modal de sucesso
- OU recarregue a página

### Reatribuir Lançamento
1. Acesse `/pos/ledger/`
2. Identifique lançamento de cliente genérico
3. Use API ou admin para reatribuir

## API Endpoints (para integração)

```javascript
// Adicionar item
POST /pos/add-item/
{
  "product_id": 123,
  "quantity": 2
}

// Adicionar pagamento (dinheiro)
POST /pos/add-payment/
{
  "payment_method_id": 1,
  "cash_tendered": 100.00
}

// Adicionar pagamento (outro)
POST /pos/add-payment/
{
  "payment_method_id": 2,
  "amount": 50.00
}

// Finalizar
POST /pos/finalize/
{
  "resolution": "apply_discount" // ou "generate_debit" ou "generate_credit"
}
```

## Exemplo Completo via API

```javascript
// 1. Adicionar produto
const item = await fetch('/pos/add-item/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken
  },
  body: JSON.stringify({
    product_id: 5,
    quantity: 3
  })
});

// 2. Adicionar pagamento
const payment = await fetch('/pos/add-payment/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken
  },
  body: JSON.stringify({
    payment_method_id: 2,
    amount: 150.00
  })
});

// 3. Finalizar
const result = await fetch('/pos/finalize/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken
  },
  body: JSON.stringify({})
});

if (result.requires_resolution) {
  // Mostrar modal e pedir escolha do usuário
  console.log(result.type); // "underpaid" ou "overpaid"
  console.log(result.difference); // valor da diferença
}
```

## Boas Práticas

1. **Sempre defina o cliente específico** quando possível
2. **Use cliente genérico apenas para vendas sem identificação**
3. **Reatribua lançamentos genéricos** assim que identificar o cliente
4. **Verifique estoque** antes de finalizar vendas grandes
5. **Feche o caixa diariamente** consultando vendas finalizadas

## Suporte
Para dúvidas ou problemas, consulte:
- `PDV_README.md` - Documentação técnica completa
- `/admin/pos/` - Interface administrativa
- Logs do Django para debugging
