# Momentum – Trading Signal Orchestrator

Momentum é um conjunto de serviços para ingestão de sinais do Telegram, normalização com OpenAI e exposição via painel administrativo. O backend (FastAPI) captura mensagens em tempo real, processa-as em uma fila assíncrona e armazena apenas os sinais estruturados dos últimos 24 h. O frontend (Next.js 14) oferece um painel responsivo com navegação estilo painel no desktop e tab bar no mobile.

## Principais recursos

- **Estratégias nomeadas (até 2 ativas)**: vincule cada estratégia a um canal Telegram e controle ativar/pausar/inativar individualmente.
- **Parsing com OpenAI**: mensagens recém-recebidas são transformadas em JSON padronizado (`symbol`, `action`, `entry`, `take_profit`, `stop_loss`…).
- **Fila assíncrona resiliente**: impede sobrecarga da API da OpenAI e aplica retenção automática de 24 h para sinais processados.
- **Autenticação administrativa**: painel protegido com JWT (e-mail/senha). É possível cadastrar novos administradores autenticados.
- **Gestão completa do Telegram**: login com código + 2FA, controle de captura (start/pause/stop) e visualização de status.

## Requisitos

- Python 3.11+
- Node.js 18+
- npm 9+
- (Opcional) Docker 24+ para deploy containerizado
- Credenciais do Telegram (API ID / API Hash) disponíveis em [my.telegram.org](https://my.telegram.org/)
- Chave da OpenAI (modelo `gpt-4o`/`gpt-4o-mini` ou compatível com `responses.create`)

## Variáveis de ambiente

Crie um `.env` na raiz (o backend lê automaticamente com `python-dotenv`). Principais chaves:

| Variável | Obrigatório | Descrição |
| --- | --- | --- |
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | ✓ | Credenciais do Telegram |
| `TELEGRAM_SESSION_NAME` | | Nome do arquivo de sessão (default `telegram_session`) |
| `TELEGRAM_INITIAL_HISTORY` | | Mensagens históricas a buscar ao configurar um canal (default 200) |
| `DATABASE_PATH` | | Caminho do SQLite (default `data/app.db`) |
| `OPENAI_API_KEY` | ✓ | Chave da OpenAI para parsing dos sinais |
| `OPENAI_MODEL` | | Modelo (default `gpt-4o-mini`) |
| `SIGNAL_RETENTION_HOURS` | | Horas a manter sinais processados (default 24) |
| `SIGNAL_WORKERS` | | Workers da fila de parsing (default 2) |
| `ADMIN_TOKEN_SECRET` | ✓ | Segredo JWT para autenticação administrativa |
| `ADMIN_TOKEN_EXP_MINUTES` | | Expiração do token (default 1440 ≈ 24 h) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | | Se informados, cria o administrador inicial no primeiro boot |
| `CORS_ALLOW_ORIGINS` | | Lista separada por vírgula de origens autorizadas |

O frontend (`frontend/.env.local`) pode apontar para a API caso você altere portas ou exposes via proxy:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_WS_URL=ws://localhost:8000
```

## Execução local

### Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A API REST fica em `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Painel disponível em `http://localhost:3000`.

## Autenticação administrativa

1. Defina `ADMIN_TOKEN_SECRET` (e opcionalmente `ADMIN_EMAIL` / `ADMIN_PASSWORD`).
2. Inicie o backend; se o e-mail/senha padrão forem fornecidos, o usuário é criado automaticamente.
3. No painel, informe o e-mail/senha para receber um token. O token é armazenado no `localStorage` e enviado em `Authorization: Bearer` para todas as chamadas protegidas.
4. Administradores autenticados podem criar novos usuários em **Administrador → Criar novo administrador**.

## Fluxo para estratégias e sinais

1. Autentique-se e abra a aba **Estratégias**.
2. Informe nome e canal (`@username`, ID numérico ou link `https://t.me/...`).
3. Ao ativar (máx. 2 simultâneas), o backend mantém o canal em escuta e envia novas mensagens para a fila de parsing.
4. O parser solicita ao modelo da OpenAI o JSON padronizado. Sucessos são salvos com `status=parsed`; falhas permanecem registradas com `status=failed` e o erro retornado.
5. A aba **Sinais** permite selecionar uma estratégia e visualizar os sinais processados (os mais recentes dentro das últimas 24 h).

Sinais com mais de `SIGNAL_RETENTION_HOURS` são limpos automaticamente após cada processamento para manter o banco enxuto.

## Principais endpoints

### Autenticação administrativa
- `POST /api/admin/login` → `{ access_token, token_type }`
- `POST /api/admin/register` *(requer token)* → cria novo admin
- `GET /api/admin/me` *(requer token)* → dados do administrador atual

### Estratégias & sinais *(requer token)*
- `GET /api/strategies`
- `POST /api/strategies` `{ name, channel_identifier, activate }`
- `PATCH /api/strategies/{id}` `{ name }`
- `POST /api/strategies/{id}/channel` `{ channel_identifier }`
- `POST /api/strategies/{id}/(activate|deactivate|pause|resume)`
- `DELETE /api/strategies/{id}`
- `GET /api/strategies/{id}/signals?limit=100&newer_than=ISO8601`

### Sessão do Telegram *(requer token)*
- `GET /api/auth/status`
- `POST /api/auth/send-code` `{ phone }`
- `POST /api/auth/verify-code` `{ code }`
- `POST /api/auth/password` `{ password }`
- `POST /api/auth/logout`

### Configuração legacy *(requer token)*
- `GET /api/config`
- `POST /api/config/channel` `{ channels: ["@canal"], reset_history }`
- `GET /api/config/channels/available`
- `POST /api/config/capture/(start|stop|pause|resume|clear-history)`

## Estrutura do projeto

```
app/
  application/      # Casos de uso (Auth, Channel, Strategy)
  core/             # Configuração, container, logging
  domain/           # Modelos e portas (interfaces)
  infrastructure/   # Persistência SQLite
  presentation/     # Routers FastAPI
  services/         # Integrações (Telegram, OpenAI parser, fila)
frontend/
  app/              # Next.js App Router, layout e páginas
  ...
```

## Observações

- Se `OPENAI_API_KEY` não estiver configurada ou o modelo retornar erro, o registro é mantido com `status="failed"` e o campo `error` preenchido.
- Mensagens históricas antigas não são reprocessadas automaticamente; apenas sinais recebidos após a vinculação do canal (timestamp ≥ `channel_linked_at`) entram na fila.
- Sempre persista os volumes Docker `app-data` (SQLite) e `telegram-session` (sessão Telegram) em produção.

## Licença

Projeto de uso interno. Ajuste conforme necessário antes de expor publicamente.
