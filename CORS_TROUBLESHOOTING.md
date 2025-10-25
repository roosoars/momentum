# CORS Error Troubleshooting

## Erro Reportado

```
[Error] Not allowed to request resource
[Error] Fetch API cannot load http://localhost:8000/api/users/register due to access control checks.
```

## Análise do Problema

### 1. Rota Inexistente
A rota `/api/users/register` **não existe** no backend atual. As rotas de autenticação disponíveis são:

**Autenticação Admin** (`/api/admin/*`):
- POST `/api/admin/login` - Login com email/senha
- GET `/api/admin/me` - Perfil do admin

**Autenticação Telegram** (`/api/auth/*`):
- GET `/api/auth/status` - Status de autenticação
- POST `/api/auth/send-code` - Enviar código de verificação
- POST `/api/auth/verify-code` - Verificar código
- POST `/api/auth/password` - Configurar senha
- POST `/api/auth/logout` - Logout

### 2. Configuração de CORS
O backend foi corrigido para usar `allow_credentials=False` (commit `60b9f51`), o que resolve a incompatibilidade entre `allow_credentials=True` e `allow_origins=["*"]`.

**Arquivo**: `app/core/app_factory.py:41`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,  # Alterado de True para False
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Arquitetura do Sistema
O sistema usa **Caddy** como proxy reverso:
- Requisições para `https://{DOMAIN}/api/*` → `backend:8000`
- Requisições para `https://{DOMAIN}/ws/*` → `backend:8000`
- Outras requisições → `frontend:3000`

## Possíveis Causas do Erro

### Causa 1: Cache do Navegador
O navegador pode estar executando JavaScript antigo em cache que ainda tenta acessar a rota removida.

**Solução**:
1. Abra o DevTools (F12)
2. Vá em Network/Rede
3. Marque "Disable cache"
4. Faça hard refresh (Ctrl+Shift+R ou Cmd+Shift+R)
5. Ou limpe todo o cache do navegador

### Causa 2: Frontend Não Reconstruído
O frontend pode ter código compilado antigo no diretório `.next/`.

**Solução**:
```bash
# No diretório frontend/
rm -rf .next
docker compose restart frontend
```

### Causa 3: Arquivo .env Ausente
O backend não tem arquivo `.env`, então está usando valores padrão.

**Solução**:
Crie o arquivo `/home/user/momentum/.env` baseado em `.env.example` e configure:

```bash
# Minimal configuration for CORS
CORS_ALLOW_ORIGINS=https://yourdomain.com,http://localhost:3000

# Admin credentials
ADMIN_TOKEN_SECRET=your-secret-key-here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-password-here

# Telegram credentials
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash
TELEGRAM_PHONE=+5511999990000

# OpenAI (optional)
OPENAI_API_KEY=sk-...
```

### Causa 4: Acesso Direto ao Backend
Se o frontend está tentando acessar `http://localhost:8000` diretamente, bypassa o Caddy e causa problemas de CORS.

**Verificar**:
- O frontend deve ser acessado via domínio configurado (ex: `https://momentum.roosoars.com`)
- **NÃO** acesse via `http://localhost:3000` em produção

**Configuração do Frontend** (apenas para desenvolvimento local):
```bash
# frontend/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_WS_URL=ws://localhost:8000
```

**Em produção (Docker)**, o frontend usa `window.location.origin` automaticamente.

### Causa 5: Extensão do Navegador ou Script Externo
Alguma extensão ou script pode estar fazendo requisições não autorizadas.

**Solução**:
1. Abra o navegador em modo anônimo/privado
2. Desabilite todas as extensões
3. Teste novamente

## Ações Recomendadas

1. **Reiniciar serviços com logs**:
   ```bash
   docker compose restart backend frontend
   docker compose logs -f backend frontend
   ```

2. **Verificar logs do backend** durante a requisição problemática:
   ```bash
   docker compose logs backend --tail=100 -f
   ```

3. **Inspecionar requisição no DevTools**:
   - Abra DevTools → Network
   - Reproduza o erro
   - Clique na requisição falhada
   - Verifique:
     - URL completa
     - Request Headers (especialmente `Origin`)
     - Response Headers (procure por `Access-Control-*`)
     - Status code

4. **Testar endpoint de health**:
   ```bash
   curl -v http://localhost:8000/health
   curl -v https://yourdomain.com/health
   ```

## Próximos Passos

Se o erro persistir após:
1. ✅ Limpar cache do navegador
2. ✅ Reiniciar serviços Docker
3. ✅ Verificar que está acessando via domínio correto (não localhost diretamente)

Então forneça:
- Captura de tela da aba Network no DevTools mostrando a requisição falhada
- Logs completos do backend durante o erro
- URL que você está acessando no navegador
- Se está em ambiente de desenvolvimento ou produção

## Referências

- Commit com fix CORS: `60b9f51`
- Arquivo de configuração CORS: `app/core/app_factory.py:38-44`
- Proxy reverso: `infra/caddy/Caddyfile`
