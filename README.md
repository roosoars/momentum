<<<<<<< HEAD
# momentum
=======
# Telegram Channel Collector

API FastAPI e painel Next.js para coletar mensagens completas de canais do Telegram. O sistema permite autenticação com código/2FA, seleção dinâmica do canal monitorado e streaming em tempo real das mensagens.

## Requisitos

- Python 3.11+
- Node.js 18+ e npm
- Docker 24+ (opcional, para implantação containerizada)
- Credenciais do Telegram (API ID / API Hash) disponíveis em [my.telegram.org](https://my.telegram.org/)

## Arquitetura

O backend foi reorganizado seguindo princípios de Clean Architecture e SOLID:

- `app/core` – configuração, logging, fábrica FastAPI e container de dependências
- `app/domain` – portas (interfaces) usadas pelas camadas superiores
- `app/infrastructure` – implementações concretas (SQLite)
- `app/services` – integrações externas (Telegram, WebSocket)
- `app/application` – casos de uso (Auth, Channel, Messages)
- `app/presentation` – routers FastAPI e WebSockets

O frontend permanece isolado em `frontend/` com Next.js 14 e Tailwind.

## Execução local (sem Docker)

### Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # preencha com suas credenciais
uvicorn app.main:app --reload
```

Endpoints em `http://localhost:8000` (REST) e `ws://localhost:8000/ws/messages`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Painel em [http://localhost:3000](http://localhost:3000). Ajuste `NEXT_PUBLIC_API_BASE_URL`/`NEXT_PUBLIC_API_WS_URL` se modificar portas.

## Deploy automatizado (DigitalOcean / produção)

O projeto inclui um script que prepara um host Ubuntu na DigitalOcean (ou ambiente compatível) e entrega o stack completo com HTTPS no domínio `momentum.roosoars.com`.

1. Configure o DNS do domínio apontando `momentum.roosoars.com` para o IP do servidor.
2. Faça login no servidor e clone o repositório.
3. Copie e ajuste as variáveis:
   ```bash
   cp .env.example .env
   ```
4. Torne o script executável e rode a implantação:
   ```bash
   chmod +x scripts/deploy.sh
   sudo scripts/deploy.sh
   ```
   O script instala Docker/Compose, preenche o `.env` com os dados solicitados (API do Telegram, e-mail para TLS, etc.), constrói os containers e executa o `docker compose up -d --build`. Ao final, oferece rodar automaticamente `scripts/authorize.py` dentro do container para concluir a autenticação com o Telegram.

Serviços atendidos via Caddy (TLS automático):

- Painel Next.js: `https://momentum.roosoars.com`
- API FastAPI: `https://momentum.roosoars.com/api`
- WebSocket: `wss://momentum.roosoars.com/ws/messages`

Volumes persistem banco SQLite (`./data`) e sessão do Telegram (`./state`). O backend utiliza `TELEGRAM_SESSION_NAME=/app/state/telegram_session` para manter a autorização entre deploys.

Comandos úteis (executar na raiz do projeto):

```bash
docker compose logs -f backend
docker compose restart frontend
docker compose run --rm backend python scripts/authorize.py
docker compose down
```

> Para executar o stack Docker localmente sem domínio, ajuste `SITE_DOMAIN`, `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_API_WS_URL` e `CORS_ALLOW_ORIGINS` no `.env`, mantendo as portas `127.0.0.1:8000` e `127.0.0.1:3000` liberadas apenas para loopback.

## Endpoints principais

- `POST /api/auth/send-code` – envia código ao telefone
- `POST /api/auth/verify-code` – valida o código, indicando 2FA se necessário
- `POST /api/auth/password` – confirma a senha do segundo fator
- `POST /api/auth/logout` – encerra a sessão atual
- `GET /api/auth/status` – status de conexão/autorização
- `POST /api/config/channel` – troca o canal monitorado (`channel_id`, `reset_history`)
- `GET /api/config` – configuração salva e status atual
- `GET /api/messages` – histórico persistido (`?limit=` / `?channel_id=`)
- `ws://host/ws/messages` – streaming (`history` inicial + `message` para novos eventos)

O script `python scripts/authorize.py` continua disponível para autorizar a sessão via terminal.

## Fluxo de uso

1. No painel, informe o telefone e clique em “Enviar código”.
2. Digite o código recebido; confirme senha 2FA se solicitado.
3. Com a sessão ativa, informe o ID ou `@username` do canal e salve.
4. O histórico inicial (configurável) é sincronizado e novas mensagens entram em tempo real.

Mensagens e payloads integrais ficam em `data/app.db`. Ajuste `DATABASE_PATH` se usar outro volume ou driver.

## Observações

- A conta precisa ter permissão de leitura no canal monitorado.
- Persistir o diretório `state/` é essencial para não perder a sessão Telegram nos deploys.
- Considere adicionar autenticação adicional (reverse proxy, OAuth) antes de expor o painel publicamente.
>>>>>>> e7c57b3 (feature: telegram connector e painel administrador)
