#!/usr/bin/env bash

set -euo pipefail

DEFAULT_DOMAIN="momentum.roosoars.com"
DOMAIN="${DEFAULT_DOMAIN}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

require_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Este script precisa ser executado como root (use sudo)." >&2
        exit 1
    fi
}

require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

install_docker() {
    echo "Instalando Docker e dependências..."
    apt-get update
    apt-get install -y ca-certificates curl gnupg lsb-release

    if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
    fi

    local codename
    codename="$(lsb_release -cs)"
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        ${codename} stable" >/etc/apt/sources.list.d/docker.list

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    systemctl enable docker
    systemctl restart docker

    if [ -n "${SUDO_USER:-}" ]; then
        usermod -aG docker "${SUDO_USER}"
        echo "Usuário ${SUDO_USER} adicionado ao grupo docker (é necessário logout/login para efeito)."
    fi
}

ensure_env_file() {
    if [ ! -f "${ENV_FILE}" ]; then
        echo "Criando ${ENV_FILE} a partir de .env.example..."
        cp "${PROJECT_ROOT}/.env.example" "${ENV_FILE}"
    fi
}

escape_sed() {
    printf '%s' "$1" | sed -e 's/[\/&]/\\&/g'
}

update_env_var() {
    local key="$1"
    local value="$2"
    local escaped
    escaped="$(escape_sed "${value}")"
    if grep -q "^${key}=" "${ENV_FILE}"; then
        sed -i "s/^${key}=.*/${key}=${escaped}/" "${ENV_FILE}"
    else
        printf '%s=%s\n' "${key}" "${value}" >>"${ENV_FILE}"
    fi
}

prompt_env_var() {
    local key="$1"
    local prompt="$2"
    local default_value="${3:-}"
    local silent="${4:-no}"

    local current=""
    if grep -q "^${key}=" "${ENV_FILE}"; then
        current="$(grep "^${key}=" "${ENV_FILE}" | head -n1 | cut -d= -f2-)"
    fi

    if [ -n "${current}" ]; then
        echo "${key} já definido em ${ENV_FILE} (mantido)."
        return
    fi

    local value=""
    if [ "${silent}" = "yes" ]; then
        read -rsp "${prompt}: " value
        echo
    else
        if [ -n "${default_value}" ]; then
            read -rp "${prompt} [${default_value}]: " value
        else
            read -rp "${prompt}: " value
        fi
    fi

    if [ -z "${value}" ] && [ -n "${default_value}" ]; then
        value="${default_value}"
    fi

    update_env_var "${key}" "${value}"
}

detect_compose_command() {
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
    else
        echo ""
    fi
}

authorize_telegram() {
    echo
    read -rp "Deseja autorizar a sessão do Telegram agora? (y/N): " answer
    case "${answer:-n}" in
        y|Y)
            echo "Abrindo fluxo interativo dentro do container..."
            ${COMPOSE_CMD} run --rm backend python scripts/authorize.py
            echo "Reiniciando serviço backend para carregar a sessão..."
            ${COMPOSE_CMD} restart backend
            ;;
        *)
            echo "Pulando autorização automática. Você pode executar latermente:"
            echo "  ${COMPOSE_CMD} run --rm backend python scripts/authorize.py"
            ;;
    esac
}

main() {
    require_root

    if ! require_cmd curl; then
        echo "Instalando curl..."
        apt-get update && apt-get install -y curl
    fi

    if ! require_cmd docker; then
        install_docker
    fi

    local compose_candidate
    compose_candidate="$(detect_compose_command)"
    if [ -z "${compose_candidate}" ]; then
        echo "Docker Compose não encontrado mesmo após instalação. Abortando." >&2
        exit 1
    fi
    COMPOSE_CMD="${compose_candidate}"

    ensure_env_file

    local existing_domain=""
    if [ -n "${DEPLOY_DOMAIN:-}" ]; then
        DOMAIN="${DEPLOY_DOMAIN}"
    elif grep -q "^SITE_DOMAIN=" "${ENV_FILE}"; then
        existing_domain="$(grep "^SITE_DOMAIN=" "${ENV_FILE}" | head -n1 | cut -d= -f2-)"
        if [ -n "${existing_domain}" ]; then
            DOMAIN="${existing_domain}"
        fi
    fi

    update_env_var "SITE_DOMAIN" "${DOMAIN}"
    update_env_var "NEXT_PUBLIC_API_BASE_URL" "https://${DOMAIN}"
    update_env_var "NEXT_PUBLIC_API_WS_URL" "wss://${DOMAIN}"
    update_env_var "CORS_ALLOW_ORIGINS" "https://${DOMAIN}"

    prompt_env_var "TELEGRAM_API_ID" "Informe o TELEGRAM_API_ID"
    prompt_env_var "TELEGRAM_API_HASH" "Informe o TELEGRAM_API_HASH (hash secreto)" "" "yes"
    prompt_env_var "TELEGRAM_PHONE" "Número do Telegram (ex: +5511999999999)"
    prompt_env_var "TELEGRAM_CHANNEL_ID" "Canal padrão (ID numérico ou @username) [opcional]"
    prompt_env_var "CADDY_ADMIN_EMAIL" "E-mail para certificados Let's Encrypt"

    mkdir -p "${PROJECT_ROOT}/data" "${PROJECT_ROOT}/state"
    chown -R 1000:1000 "${PROJECT_ROOT}/data" "${PROJECT_ROOT}/state"

    echo "Construindo imagens e iniciando serviços..."
    (cd "${PROJECT_ROOT}" && ${COMPOSE_CMD} up -d --build)

    echo "Serviços iniciados. Aguardando 10 segundos para estabilizar..."
    sleep 10

    authorize_telegram

    echo
    echo "Implantação concluída!"
    echo "- Painel: https://${DOMAIN}"
    echo "- API:    https://${DOMAIN}/api"
    echo "- Ver logs: ${COMPOSE_CMD} logs -f backend"
}

main "$@"
