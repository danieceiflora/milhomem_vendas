# Sistema PDV (Ponto de Venda) - Resumo da Implementação

## ✅ O que foi implementado

### 1. Modelos (pos/models.py)
- **Sale**: Venda com suporte a múltiplos pagamentos
  - Estados: draft, finalized, cancelled
  - Campos calculados: subtotal, discount_total, total, total_paid
  - Propriedades: items_count, change_total, remaining, overpaid
  
- **SaleItem**: Itens da venda
  - Snapshot de preço e custo no momento da venda
  - Cálculo automático de line_total
  
- **SalePayment**: Pagamentos múltiplos por venda
  - Suporte especial para dinheiro (cash_tendered, change_given)
  - amount_applied = valor efetivamente usado
  
- **LedgerEntry**: Lançamentos de crédito/débito
  - Tipos: credit, debit
  - Status: open, settled, cancelled
  - Vinculado a cliente e opcionalmente a venda

### 2. Serviços (pos/services.py)
Funções puras de lógica de negócio:
- `get_or_create_generic_customer()`: Cliente padrão do sistema
- `get_or_create_draft_sale()`: Gerencia vendas em rascunho
- `add_item()`: Adiciona produto à venda
- `update_item()`: Atualiza quantidade
- `remove_item()`: Remove item
- `add_payment()`: Adiciona pagamento (com lógica especial para dinheiro)
- `remove_payment()`: Remove pagamento
- `set_customer()`: Define/altera cliente
- `recalc_totals()`: Recalcula todos os totais
- `finalize_sale()`: Finaliza com validações e resoluções
- `reassign_ledger_entry()`: Reatribui lançamento para outro cliente

### 3. Views e APIs (pos/views.py)
- **POSNewView**: Tela principal do PDV
- **APIs JSON** (todas com @login_required):
  - POST /pos/add-item/
  - POST /pos/update-item/
  - POST /pos/remove-item/
  - POST /pos/add-payment/
  - POST /pos/remove-payment/
  - POST /pos/set-customer/
  - POST /pos/finalize/
- **LedgerListView**: Lista de lançamentos com filtros
- **reassign_ledger_view**: Reatribuir lançamento

### 4. Templates
- **pos/new.html**: Interface principal do PDV
  - Layout em 2 colunas (produtos/itens | pagamentos/resumo)
  - Busca de clientes e produtos com autocomplete
  - Modais para resolução de diferenças e sucesso
  
- **Componentes parciais**:
  - _items_table.html
  - _payments_table.html
  - _summary.html
  - ledger_list.html

### 5. JavaScript (pos/pos.js)
- Autocomplete de clientes e produtos com debounce
- Adicionar/editar/remover itens dinamicamente
- Múltiplos pagamentos com cálculo de troco
- Finalização com modais de resolução:
  - Pagamento menor: opções de desconto ou débito
  - Pagamento maior: opções de crédito ou editar
- Atualização em tempo real de totais e resumo
- Formatação de moeda, CPF e telefone

### 6. Admin (pos/admin.py)
- **SaleAdmin**: Com inlines de itens e pagamentos
- **LedgerEntryAdmin**: Com badges coloridos e ações:
  - Marcar como liquidado
  - Marcar como cancelado

### 7. Serializers (pos/serializers.py)
- SaleSerializer (completo com itens e pagamentos)
- SaleItemSerializer
- SalePaymentSerializer
- LedgerEntrySerializer

### 8. URLs (pos/urls.py)
Todas as rotas sob `/pos/`:
```
GET  /pos/              → PDV principal
POST /pos/add-item/     → Adicionar produto
POST /pos/update-item/  → Atualizar quantidade
POST /pos/remove-item/  → Remover produto
POST /pos/add-payment/  → Adicionar pagamento
POST /pos/remove-payment/ → Remover pagamento
POST /pos/set-customer/ → Definir cliente
POST /pos/finalize/     → Finalizar venda
GET  /pos/ledger/       → Lista de lançamentos
POST /pos/ledger/reassign/ → Reatribuir lançamento
```

### 9. Integrações
- **Customer**: Adicionado campo `is_generic` para cliente padrão
- **PaymentMethod**: Reutilizado do app outflows
- **Product**: Integrado para busca e preços

## 🎯 Funcionalidades Principais

### Fluxo de Venda
1. Sistema cria venda em draft automaticamente
2. Cliente pode ser genérico ou específico
3. Adicionar produtos com busca inteligente
4. Múltiplos pagamentos em diferentes métodos
5. Cálculo automático de troco para dinheiro
6. Finalização com validações:
   - Se pago < total: desconto ou débito
   - Se pago > total: crédito ou editar
   - Se pago == total: finaliza direto

### Pagamento em Dinheiro
- Operador informa valor recebido
- Sistema calcula troco automaticamente
- amount_applied = min(recebido, restante)
- change_given = excesso

### Crédito e Débito
- Gerados automaticamente na finalização
- Podem ser vinculados a cliente genérico
- Reatribuíveis posteriormente
- Estados: open, settled, cancelled

## 🔐 Segurança
- Todas as operações protegidas por @login_required
- Cálculos sempre server-side
- Transações atômicas em operações críticas
- CSRF protection em todas as APIs
- Validações de quantidade, preço, valores

## 📊 Decisões de Arquitetura
1. **App separado**: Mantém código isolado e organizado
2. **Services layer**: Lógica de negócio testável e reutilizável
3. **Cliente genérico**: Flag no modelo Customer evita NULL
4. **1 draft por usuário**: Simplifica UX e evita confusão
5. **Múltiplos pagamentos**: Flexibilidade para cenários reais
6. **Serializers DRF**: Consistência com resto do projeto
7. **Vanilla JS**: Sem dependências extras, apenas Fetch API

## 🚀 Como Usar

### Primeira Venda
1. Acesse `/pos/`
2. Sistema cria venda draft com cliente genérico
3. Busque e adicione produtos
4. Adicione formas de pagamento
5. Finalize (resolve diferenças se necessário)

### Cliente Específico
1. Use a busca de clientes no topo
2. Selecione o cliente desejado
3. Continue a venda normalmente

### Pagamento Parcial
1. Adicione pagamentos até cobrir o total
2. Ou finalize e escolha "Gerar Débito"

### Troco
1. Selecione "Dinheiro" como método
2. Informe valor recebido
3. Troco calculado automaticamente

## 📝 Próximos Passos (Opcionais)
- [ ] Impressão de cupom/recibo
- [ ] Liquidação de débitos em vendas futuras
- [ ] Histórico de vendas por cliente
- [ ] Relatórios de fechamento de caixa
- [ ] Integração com impressora fiscal
- [ ] App mobile para PDV

## 🧪 Testes
Modelos e services foram criados com testabilidade em mente:
- Funções puras em services.py
- Transações atômicas isoladas
- Validações server-side independentes
- Fácil mockar dependências

## 📦 Arquivos Criados/Modificados

### Criados
- pos/ (app completo)
- pos/models.py
- pos/services.py
- pos/views.py
- pos/urls.py
- pos/serializers.py
- pos/admin.py
- pos/templates/pos/new.html
- pos/templates/pos/ledger_list.html
- pos/templates/pos/components/*.html
- pos/static/pos/pos.js
- pos/migrations/0001_initial.py
- customers/migrations/0005_customer_is_generic.py

### Modificados
- customers/models.py (campo is_generic)
- app/settings.py (INSTALLED_APPS)
- app/urls.py (include pos.urls)

## ✨ Destaques Técnicos
- Uso de Decimal para precisão financeira
- TWO_PLACES com ROUND_HALF_UP
- Indices no banco para performance
- Prefetch/select_related para N+1
- Debounce em buscas
- Formatação i18n (pt-BR)
- Responsive design com Tailwind
- Ícones Lucide
