# Stripe Integration Setup Guide

Este guia explica como configurar a integração Stripe no Momentum para aceitar pagamentos e gerenciar assinaturas.

## 1. Criar Conta Stripe

1. Acesse [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)
2. Crie sua conta Stripe
3. Complete o processo de verificação (se necessário)

## 2. Obter API Keys

### Test Mode Keys (Para desenvolvimento/testes)

1. No Stripe Dashboard, certifique-se que está em **Test mode** (toggle no canto superior direito)
2. Vá para **Developers → API keys**
3. Copie as chaves:
   - **Publishable key**: começa com `pk_test_...`
   - **Secret key**: começa com `sk_test_...` (clique em "Reveal test key")

### Production Mode Keys (Para produção)

1. No Stripe Dashboard, mude para **Live mode** (toggle no canto superior direito)
2. Vá para **Developers → API keys**
3. Copie as chaves:
   - **Publishable key**: começa com `pk_live_...`
   - **Secret key**: começa com `sk_live_...` (clique em "Reveal live key")

⚠️ **IMPORTANTE**: NUNCA exponha suas secret keys publicamente ou em repositórios Git!

## 3. Criar Produto e Preço no Stripe

### Usando o Dashboard

1. Vá para **Products** no menu lateral
2. Clique em **+ Add product**
3. Preencha:
   - **Name**: Ex: "Momentum Monthly Subscription"
   - **Description**: Descrição do seu produto
4. Em **Pricing**:
   - Escolha **Recurring**
   - **Price**: Defina o valor (ex: R$ 99,00)
   - **Billing period**: Escolha a frequência (Monthly, Yearly, etc.)
5. Clique em **Save product**
6. Anote o **Price ID** (começa com `price_...`)

### Usando a Stripe CLI (Opcional)

```bash
stripe products create \
  --name="Momentum Monthly Subscription" \
  --description="Assinatura mensal do Momentum"

stripe prices create \
  --product=prod_xxxxx \
  --unit-amount=9900 \
  --currency=brl \
  --recurring[interval]=month
```

## 4. Configurar no Painel Momentum

1. Acesse o painel administrativo do Momentum
2. Vá para **Stripe** no menu lateral
3. Configure as API keys:

### Para Modo Test:
- Cole a **Test Secret Key** (sk_test_...)
- Cole a **Test Publishable Key** (pk_test_...)
- Selecione modo **Test**
- Clique em **Salvar Configuração**

### Para Modo Production:
- Cole a **Production Secret Key** (sk_live_...)
- Cole a **Production Publishable Key** (pk_live_...)
- Selecione modo **Production**
- Clique em **Salvar Configuração**

4. Verifique o **Status da Conexão** - deve mostrar "Conectado"

## 5. Testar a Integração

### No Modo Test:

1. Certifique-se que está em modo **Test**
2. Clique em **Criar Assinatura de Teste**
3. Uma assinatura será criada automaticamente com dados de teste
4. Verifique no Stripe Dashboard → Customers e Subscriptions

### Cartões de Teste

Para testes com cartão de crédito, use:

- **Sucesso**: `4242 4242 4242 4242`
- **Requer autenticação**: `4000 0025 0000 3155`
- **Recusado**: `4000 0000 0000 0002`
- **CVV**: Qualquer 3 dígitos
- **Data de expiração**: Qualquer data futura
- **CEP**: Qualquer CEP

Mais cartões de teste: [https://stripe.com/docs/testing](https://stripe.com/docs/testing)

## 6. Alternar entre Test e Production

Você pode alternar entre os modos a qualquer momento no painel:

1. Acesse **Stripe** no painel
2. Clique no botão **Test** ou **Production**
3. Clique em **Salvar Configuração**

O sistema usará automaticamente as chaves correspondentes ao modo selecionado.

## 7. Webhooks (Futuro)

Para receber notificações de eventos do Stripe (pagamentos bem-sucedidos, falhas, cancelamentos):

1. No Stripe Dashboard → **Developers → Webhooks**
2. Clique em **Add endpoint**
3. URL: `https://seu-dominio.com/api/stripe/webhook`
4. Selecione os eventos que deseja receber
5. Copie o **Signing secret** (começa com `whsec_...`)

## 8. Segurança

### Boas Práticas:

- ✅ Use sempre HTTPS em produção
- ✅ Mantenha as Secret Keys seguras
- ✅ Teste extensivamente em Test mode antes de ir para Production
- ✅ Configure webhooks para receber atualizações de status
- ✅ Implemente retry logic para chamadas de API
- ❌ NUNCA exponha Secret Keys no frontend
- ❌ NUNCA commite API keys no Git

### Variáveis de Ambiente

As chaves ficam armazenadas no banco de dados SQLite do Momentum. Para maior segurança em produção, considere usar variáveis de ambiente ou secrets management.

## 9. Monitoramento

### Stripe Dashboard

- **Payments**: Monitore todos os pagamentos
- **Customers**: Veja clientes e assinaturas ativas
- **Subscriptions**: Gerencie todas as assinaturas
- **Logs**: Veja todos os eventos de API

### Momentum Dashboard

- Status da conexão em tempo real
- Modo atual (Test/Production)
- Indicador de configuração (Configurado/Não configurado)

## 10. Troubleshooting

### "Stripe not configured"
- Verifique se salvou as API keys corretamente
- Confirme que está usando as chaves do modo correto (Test/Live)

### "Invalid API key"
- As chaves expiraram ou foram revogadas
- Copie novas chaves do Stripe Dashboard

### "No active prices found"
- Crie um produto e preço no Stripe Dashboard primeiro
- Certifique-se que o preço está ativo

### Conexão falha
- Verifique sua conexão com internet
- Confirme que as chaves estão corretas
- Veja os logs do backend para mais detalhes

## 11. Links Úteis

- [Stripe Dashboard](https://dashboard.stripe.com/)
- [Stripe Documentation](https://stripe.com/docs)
- [Testing Stripe](https://stripe.com/docs/testing)
- [API Reference](https://stripe.com/docs/api)
- [Stripe CLI](https://stripe.com/docs/stripe-cli)

## 12. Suporte

Para problemas com:
- **Stripe**: [https://support.stripe.com/](https://support.stripe.com/)
- **Momentum**: Abra uma issue no repositório do projeto
