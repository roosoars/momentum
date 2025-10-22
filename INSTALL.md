# Guia de Instalação

Este documento descreve passo a passo como preparar, configurar e implantar o projeto **Telegram Channel Collector** tanto para ambiente local de desenvolvimento quanto para produção em um servidor Linux na DigitalOcean utilizando o domínio `momentum.roosoars.com`.

---

## 1. Pré-requisitos

### 1.1. Conta/recursos externos
1. Credenciais do Telegram (API ID e API Hash) obtidas em [my.telegram.org](https://my.telegram.org/).
2. Registro de domínio com possibilidade de criar um registro DNS tipo A.
3. (Produção) Droplet Ubuntu 22.04 LTS ou superior na DigitalOcean.

### 1.2. Ferramentas locais
- Git
- Python 3.11+
- Node.js 18+ (apenas se executar o frontend localmente sem Docker)
- Docker Engine 24+ e Docker Compose Plugin (opcional para local, obrigatório para produção)

---

## 2. Preparação do Repositório

1. **Clonar o projeto**
   ```bash
   git clone https://seu-repositorio.git momentum
   cd momentum
   ```
2. **Copiar variáveis de ambiente**
   ```bash
   cp .env.example .env
   ```
3. **Editar `.env`**
   - Preencha `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE` e, se desejar, `TELEGRAM_CHANNEL_ID`.
   - Ajuste `SITE_DOMAIN`, `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_API_WS_URL` e `CORS_ALLOW_ORIGINS` conforme o ambiente (ex.: `http://localhost:8000` / `ws://localhost:8000` para desenvolvimento).
   - Defina `CADDY_ADMIN_EMAIL` com um e-mail válido (obrigatório para emissão automática de certificados em produção).

---

## 3. Ambiente de Desenvolvimento (opcional)

### 3.1. Backend (FastAPI)
1. Criar ambiente virtual e instalar dependências:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Executar o servidor:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Endpoints disponíveis:
   - REST: `http://localhost:8000`
   - WebSocket: `ws://localhost:8000/ws/messages`

### 3.2. Frontend (Next.js)
1. Instalar dependências:
   ```bash
   cd frontend
   npm install
   ```
2. Executar em modo desenvolvimento:
   ```bash
   npm run dev
   ```
3. Painel disponível em `http://localhost:3000`.

---

## 4. Preparação para Produção (DigitalOcean)

### 4.1. Configurar DNS
1. Crie um registro A para `momentum.roosoars.com` apontando para o IP público do droplet.
2. Aguarde a propagação (normalmente alguns minutos).

### 4.2. Acesso ao servidor
1. Conecte via SSH ao droplet:
   ```bash
   ssh root@SEU_IP_PUBLICO
   ```
2. Instale Git (se necessário):
   ```bash
   apt-get update && apt-get install -y git
   ```

### 4.3. Clonar projeto no servidor
```bash
git clone https://seu-repositorio.git momentum
cd momentum
```

### 4.4. Variáveis de ambiente
1. Copiar o template e editar:
   ```bash
   cp .env.example .env
   nano .env  # ou editor de sua preferência
   ```
2. Verifique se:
   - `SITE_DOMAIN=momentum.roosoars.com`
   - `NEXT_PUBLIC_API_BASE_URL=https://momentum.roosoars.com`
   - `NEXT_PUBLIC_API_WS_URL=wss://momentum.roosoars.com`
   - `CORS_ALLOW_ORIGINS=https://momentum.roosoars.com`
   - `CADDY_ADMIN_EMAIL` possui e-mail válido

---

## 5. Deploy Automatizado

O script `scripts/deploy.sh` realiza a instalação de Docker/Compose, atualiza `.env`, constrói e inicia os containers, além de oferecer a autorização interativa do Telegram.

### 5.1. Executar o script
```bash
chmod +x scripts/deploy.sh
sudo scripts/deploy.sh
```

### 5.2. Fluxo do script
1. Verifica dependências e instala Docker/Compose se necessário.
2. Garante que `.env` existe e solicita valores que estiverem em branco.
3. Cria diretórios persistentes `data/` (SQLite) e `state/` (sessão Telegram).
4. Executa `docker compose up -d --build`.
5. Pergunta se deseja rodar `scripts/authorize.py` dentro do container para autenticar a conta do Telegram.
   - Caso aceite, será necessário informar telefone, código SMS/Telegram e senha 2FA (se habilitada).

### 5.3. Resultado esperado
Após conclusão:
- Painel: `https://momentum.roosoars.com`
- API REST: `https://momentum.roosoars.com/api`
- WebSocket: `wss://momentum.roosoars.com/ws/messages`

---

## 6. Operação e Manutenção

### 6.1. Comandos úteis
- Visualizar logs do backend:
  ```bash
  docker compose logs -f backend
  ```
- Reiniciar serviços:
  ```bash
  docker compose restart backend
  docker compose restart frontend
  ```
- Autorizar novamente o Telegram:
  ```bash
  docker compose run --rm backend python scripts/authorize.py
  ```
- Encerrar todos os containers:
  ```bash
  docker compose down
  ```

### 6.2. Atualizações
1. Pull das alterações Git:
   ```bash
   git pull origin main  # ajuste a branch conforme necessário
   ```
2. Rebuild/rollout:
   ```bash
   docker compose up -d --build
   ```

---

## 7. Solução de Problemas

| Sintoma | Possível causa | Ação recomendada |
| --- | --- | --- |
| Painel inacessível via HTTPS | DNS não propagado ou porta 443 bloqueada | Verificar registro A, firewall e logs do Caddy (`docker compose logs -f caddy`) |
| API responde 401/403 | Conta Telegram não autenticada | Rodar `docker compose run --rm backend python scripts/authorize.py` e reiniciar backend |
| WebSocket não conecta | URL incorreta ou WebSocket bloqueado | Confirmar que o frontend usa `wss://momentum.roosoars.com` e que o DNS aponta corretamente |
| Erros de certificado | E-mail ausente ou portas 80/443 indisponíveis | Conferir `.env`, liberar portas no firewall e reiniciar Caddy |

---

## 8. Próximos Passos

1. Configurar backups do volume `data/` para preservar histórico de mensagens.
2. Adicionar camada de autenticação no painel (ex.: OAuth, Basic Auth via Caddy ou middleware).
3. Configurar monitoramento (UptimeRobot, Healthchecks, etc.) e alertas para quedas da API.
4. Avaliar substituição do SQLite por banco gerenciado se o volume de mensagens crescer significativamente.

---

**Tudo pronto!** Com essas etapas você terá o Telegram Channel Collector operando em `momentum.roosoars.com`, pronto para coletar e exibir mensagens em tempo real. Boas capturas! 🚀
