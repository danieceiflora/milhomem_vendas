# App `outflows` - Status e Uso

## ⚠️ Status Atual: DEPRECATED (Em Desuso)

O app `outflows` foi **substituído pelo app `pos`** (Point of Sale) que implementa um sistema de vendas completo e moderno.

## 📊 Por que ainda existe?

O app `outflows` está sendo **mantido apenas para preservar dados históricos** de vendas antigas:

- **Modelo `Outflow`**: Vendas antigas realizadas antes da implementação do PDV
- **Modelo `OutflowItem`**: Itens das vendas antigas
- **Modelo `OutflowReturnItem`**: Devoluções do sistema antigo

## ✅ O que foi migrado para `pos`

- ✅ **PaymentMethod**: Agora está em `pos/models.py`
- ✅ **URLs e Views**: Desabilitadas (comentadas em `app/urls.py`)
- ✅ **Menu**: Removido do sidebar
- ✅ **Templates**: Sistema novo usa templates do app `pos`

## 🔒 Acesso aos Dados Históricos

Você ainda pode acessar os dados históricos de vendas antigas através do:
- **Django Admin**: `/admin/outflows/outflow/`
- **Django Admin**: `/admin/outflows/outflowitem/`

## 🗑️ Quando posso apagar?

Você pode **apagar o app `outflows`** depois de:

1. **Migrar os dados históricos** (opcional):
   - Criar script para converter `Outflow` → `Sale` (pos)
   - Converter `OutflowItem` → `SaleItem`
   - Atualizar métricas em `app/metrics.py` para usar `Sale`

2. **Remover dependências**:
   - ❌ `app/metrics.py` - ainda usa `Outflow` para métricas
   - ❌ `ai/agent.py` - ainda referencia `Outflow`
   - ✅ `pos/*` - já migrado para usar próprio `PaymentMethod`

3. **Executar passos**:
   ```bash
   # 1. Remover de INSTALLED_APPS
   # app/settings.py - remover 'outflows'
   
   # 2. Fazer migrations
   python manage.py makemigrations
   python manage.py migrate
   
   # 3. Apagar pasta
   rm -rf outflows/
   ```

## 🎯 Recomendação

**MANTENHA** o app `outflows` por enquanto se:
- Você tem vendas antigas que precisa consultar
- Ainda usa as métricas que dependem de `Outflow`

**APAGUE** o app `outflows` se:
- Não tem dados históricos importantes
- Já migrou tudo para o novo sistema PDV
- Atualizou todas as dependências (metrics, ai, etc)

## 📝 Sistema Atual (Novo)

Use o **app `pos`** para:
- ✅ Criar vendas: `/pos/` ou `/pos/new/`
- ✅ Listar vendas: `/pos/sales/`
- ✅ Detalhes de venda: `/pos/sales/<id>/`
- ✅ Métodos de pagamento: `/pos/payment-methods/`
- ✅ Lançamentos financeiros: `/pos/ledger/`

---

**Última atualização**: 01/11/2025
