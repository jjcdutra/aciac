#!/usr/bin/env bash
# Deploy do site (Django + Postgres + Caddy) em VPS/hosting com Docker.
# Uso: ./deploy.sh <comando>   (ver ./deploy.sh help)
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE_FILE="docker-compose.prod.yml"
COMPOSE=(docker compose -f "$COMPOSE_FILE")

azul=$'\033[1;34m'; vermelho=$'\033[1;31m'; verde=$'\033[1;32m'; reset=$'\033[0m'
ok()   { echo "${verde}✔${reset} $*"; }
erro() { echo "${vermelho}✘${reset} $*" >&2; exit 1; }
info() { echo "${azul}→${reset} $*"; }

checar_env() {
  [[ -f .env ]] || erro ".env não encontrado. Copie .env.example para .env e configure (ver DEPLOY.md)."
  grep -q '^SECRET_KEY=django-insecure' .env && erro "SECRET_KEY ainda é a padrão de dev. Gere uma nova (ver DEPLOY.md)."
  grep -qE '^POSTGRES_PASSWORD=(associacao|)$' .env && erro "POSTGRES_PASSWORD vazio ou padrão. Troque por uma senha forte."
  DOMAIN=$(grep -E '^DOMAIN=' .env | cut -d= -f2- || true)
  DOMAIN=${DOMAIN:-dutratech.cloud}
  ALLOWED=$(grep -E '^ALLOWED_HOSTS=' .env | cut -d= -f2- || true)
  [[ "$ALLOWED" == *"$DOMAIN"* ]] || erro "ALLOWED_HOSTS não contém o domínio ($DOMAIN). Corrija o .env."
}

checar_docker() {
  command -v docker >/dev/null 2>&1 || erro "Docker não instalado. Instruções em DEPLOY.md."
  docker compose version >/dev/null 2>&1 || erro "Docker Compose v2 não disponível."
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  up|deploy)
    checar_docker
    checar_env
    info "Subindo stack de produção (build + migrate + collectstatic)…"
    "${COMPOSE[@]}" up -d --build "$@"
    ok "Deploy concluído. HTTPS: https://${DOMAIN:-dutratech.cloud}"
    info "Status: ./deploy.sh ps · Logs: ./deploy.sh logs"
    ;;

  down)
    "${COMPOSE[@]}" down "$@"
    ok "Stack parado (volumes preservados)."
    ;;

  restart)
    "${COMPOSE[@]}" restart "$@"
    ok "Reiniciado."
    ;;

  ps|status)
    "${COMPOSE[@]}" ps "$@"
    ;;

  logs)
    "${COMPOSE[@]}" logs -f --tail=100 "$@"
    ;;

  migrate)
    "${COMPOSE[@]}" exec app uv run python manage.py migrate "$@"
    ;;

  superuser)
    "${COMPOSE[@]}" exec app uv run python manage.py createsuperuser "$@"
    ;;

  shell)
    "${COMPOSE[@]}" exec app sh "$@"
    ;;

  manage)
    "${COMPOSE[@]}" exec app uv run python manage.py "$@"
    ;;

  backup)
    ts=$(date +%Y%m%d-%H%M%S)
    mkdir -p backups
    file="backups/db-${ts}.sql.gz"
    info "Gerando backup do Postgres…"
    "${COMPOSE[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$file"
    ok "Backup salvo em ${file} ($(du -h "$file" | cut -f1))"
    ;;

  restore)
    file="${1:-}"
    [[ -n "$file" && -f "$file" ]] || erro "Uso: ./deploy.sh restore backups/db-AAAAmmdd-HHMMSS.sql.gz"
    info "Restaurando ${file} (o banco atual será substituído)…"
    read -rp "Confirma? [s/N] " resp
    [[ "$resp" =~ ^[sS]$ ]] || erro "Abortado."
    gunzip -c "$file" | "${COMPOSE[@]}" exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"'
    ok "Backup restaurado."
    ;;

  pull-code)
    # Atualiza o código do servidor a partir do Git (alternativa ao rsync).
    git pull --ff-only "$@"
    ok "Código atualizado. Rode: ./deploy.sh up"
    ;;

  help|-h|--help)
    cat <<'EOF'
Uso: ./deploy.sh <comando>

  up           Build + sobe o stack (app, Postgres, Caddy com HTTPS)   [deploy]
  down         Para o stack (preserva volumes/banco)
  restart      Reinicia os containers
  ps           Status dos containers
  logs         Logs em tempo real (aceita nome do serviço: logs app)
  migrate      Aplica migrations
  superuser    Cria superusuário (admin do Django)
  manage       Qualquer comando manage.py (ex.: collectstatic)
  shell        Shell dentro do container do app
  backup       Backup do Postgres → backups/db-<timestamp>.sql.gz
  restore      Restaura backup: ./deploy.sh restore backups/db-xxx.sql.gz
  pull-code    git pull --ff-only (se o server usa Git)
  help         Esta mensagem

Guia completo de publicação (Hostinger VPS, DNS, firewall): DEPLOY.md
EOF
  ;;

  *)
    erro "Comando desconhecido: $cmd (use ./deploy.sh help)"
    ;;
esac
