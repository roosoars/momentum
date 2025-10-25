# Guia de Instalação

Este documento descreve passo a passo como preparar, configurar e implantar o projeto **Momentum** tanto para ambiente local de desenvolvimento quanto para produção em um servidor Linux na DigitalOcean utilizando o domínio `momentum.roosoars.com`.

---

## 1. Pré-requisitos

### 1.1. Conta/recursos externos
1. Credenciais do Telegram (API ID e API Hash) obtidas em [my.telegram.org](https://my.telegram.org/).
2. Chave da OpenAI para parsing de sinais.
3. Registro de domínio com possibilidade de criar um registro DNS tipo A.
4. (Produção) Droplet Ubuntu 22.04 LTS ou superior na DigitalOcean.

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
   - Preencha `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` e, se necessário, `TELEGRAM_PHONE`.
   - Informe `OPENAI_API_KEY` (obrigatório para o parser de sinais) e ajuste `OPENAI_MODEL` se preferir outro modelo compatível.
   - Defina `ADMIN_TOKEN_SECRET` (obrigatório), além de `ADMIN_EMAIL`/`ADMIN_PASSWORD` caso queira provisionar o primeiro administrador automaticamente.
   - Ajuste `SITE_DOMAIN`, `NEXT_PUBLIC_API_BASE_URL` e `CORS_ALLOW_ORIGINS` conforme o ambiente (ex.: `http://localhost:8000` para desenvolvimento).
   - Configure `CADDY_ADMIN_EMAIL` com um e-mail válido (obrigatório para emissão automática de certificados em produção).

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
4. O painel e todas as rotas REST (exceto `/api/admin/login`) exigem token Bearer. Utilize o painel ou um cliente HTTP para chamar `POST /api/admin/login` com as credenciais administrativas e reutilizar o `access_token` retornado nas requisições subsequentes.

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
2. Instale Git e Docker (se necessário):
   ```bash
   apt-get update && apt-get install -y git docker.io docker-compose-plugin
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
   - `CORS_ALLOW_ORIGINS=https://momentum.roosoars.com`
   - `CADDY_ADMIN_EMAIL` possui e-mail válido

---

## 5. Deploy com Docker Compose

### 5.1. Construir e iniciar
```bash
docker compose up -d --build
```

### 5.2. Verificar status
```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

### 5.3. Resultado esperado
Após conclusão:
- Painel: `https://momentum.roosoars.com`
- API REST: `https://momentum.roosoars.com/api`

---

## 6. Autenticação do Telegram

### Via Interface Web (Recomendado)
1. Acesse o painel em `https://momentum.roosoars.com`
2. Faça login com suas credenciais administrativas
3. Vá para a aba **Telegram**
4. Informe seu número de telefone e siga o fluxo de autenticação

### Via Script (Recovery)
Caso precise autorizar manualmente via CLI:
```bash
docker compose run --rm backend python scripts/authorize.py
```

---

## 7. Operação e Manutenção

### 7.1. Comandos úteis
- Visualizar logs do backend:
  ```bash
  docker compose logs -f backend
  ```
- Reiniciar serviços:
  ```bash
  docker compose restart backend
  docker compose restart frontend
  ```
- Encerrar todos os containers:
  ```bash
  docker compose down
  ```

### 7.2. Atualizações
1. Pull das alterações Git:
   ```bash
   git pull origin main  # ajuste a branch conforme necessário
   ```
2. Rebuild/rollout:
   ```bash
   docker compose up -d --build
   ```

---

## 8. Solução de Problemas

| Sintoma | Possível causa | Ação recomendada |
| --- | --- | --- |
| Painel inacessível via HTTPS | DNS não propagado ou porta 443 bloqueada | Verificar registro A, firewall e logs do Caddy (`docker compose logs -f caddy`) |
| API responde 401/403 | Conta Telegram não autenticada | Autenticar via interface web na aba Telegram |
| Erros de certificado | E-mail ausente ou portas 80/443 indisponíveis | Conferir `.env`, liberar portas no firewall e reiniciar Caddy |
| Erro de permissões no banco | Volumes Docker com permissões incorretas | Remover volumes e recriar: `docker compose down && docker volume rm momentum_app-data momentum_telegram-session && docker compose up -d --build` |

---

## 9. Próximos Passos

1. Configurar backups dos volumes Docker `app-data` e `telegram-session`.
2. Configurar monitoramento (UptimeRobot, Healthchecks, etc.) e alertas para quedas da API.
3. Avaliar substituição do SQLite por banco gerenciado se o volume de mensagens crescer significativamente.
4. Ajustar `SIGNAL_RETENTION_HOURS` caso necessite armazenar sinais por mais tempo do que o padrão de 24 h.

---

**Tudo pronto!** Com essas etapas você terá o Momentum operando em `momentum.roosoars.com`, pronto para coletar e processar sinais em tempo real. 🚀
