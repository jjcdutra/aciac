# Deploy — Publicação em produção (Hostinger VPS + dutratech.cloud)

Guia completo para publicar o site em produção com HTTPS automático.

## Arquiturura

```
Internet ──► Caddy (:80/:443) ──► app:8000 (Django/gunicorn)
                     │                    │
              certificado          db:5432 (Postgres)
              Let's Encrypt         (rede interna)
```

| Arquivo | Papel |
|---|---|
| `docker-compose.prod.yml` | Stack de produção: Postgres + app + Caddy |
| `deploy/Caddyfile` | Proxy reverso, HTTPS automático e servidão de `/media` |
| `deploy.sh` | Atalhos: deploy, logs, backup, migrate, superuser |
| `.env` | **Nunca versionado** — toda a configuração sensível |

Decisões de design:

- **Caddy dentro do Docker** (não no host): tudo versionado e reproduzível;
  migra de servidor com o mesmo comando.
- **Sem portas públicas** para app (8000) e Postgres — só o Caddy expõe
  80/443; o restante fica na rede interna do Compose.
- **HTTPS automático** via Let's Encrypt (Caddy obtém e renova o certificado
  sozinho — sem cron de certbot).
- **Mídia** (`/media`) servida direto pelo Caddy (mais rápido; volume
  compartilhado com o app).
- `prod.py` já endurece a aplicação (`DEBUG=False`, HSTS, cookies `Secure`);
  `SECURE_SSL_REDIRECT=False` no Compose porque o Caddy cuida do
  redirecionamento HTTP→HTTPS e informa o esquema via `X-Forwarded-Proto`.

---

## 1. Pré-requisitos

### 1.1 Plano de hospedagem

Este projeto é **Python/Django + PostgreSQL** — não roda no hospedagem
compartilhada (cPanel/PHP) da Hostinger. Use um dos:

| Produto Hostinger | Serve? | Observação |
|---|---|---|
| **VPS KVM 2+** (recomendado) | Sim | Ubuntu 24.04, 2+ GB RAM, Docker completo |
| Cloud Server | Sim | Mesma lógica do VPS |
| Hospedagem compartilhada / Premium | Não | Só PHP/MySQL, sem Docker/Python |

### 1.2 Domínio

O domínio `dutratech.cloud` deve resolver (DNS) para o IP do VPS **antes** de
subir o Caddy — senão o Let's Encrypt falha ao validar.

No hPanel da Hostinger (domínio registrado lá):

1. **DNS Zone** → adicionar/atualizar registros:

   | Tipo | Nome | Valor |
   |---|---|---|
   | A | `@` | `IP_DO_VPS` |
   | A | `www` | `IP_DO_VPS` |

2. Propagação: de minutos a algumas horas. Teste:
   ```bash
   dig +short dutratech.cloud A
   dig +short www.dutratech.cloud A
   ```

Se o domínio está em outro registrador (ex.: Cloudflare), aponte os mesmos
registros A para o IP do VPS. Se usar Cloudflare, recomenda-se modo
*Full (strict)* com o proxy ligado.

---

## 2. Preparar o servidor (uma vez)

Conecte via SSH:

```bash
ssh root@IP_DO_VPS
```

### 2.1 Docker

```bash
curl -fsSL https://get.docker.com | sh
docker compose version   # deve mostrar v2+
```

### 2.2 Firewall

```bash
apt install -y ufw
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp   # HTTP/3 (opcional)
ufw enable
ufw status
```

> O app (8000) e o Postgres (5432) **não** precisam de regra — ficam na rede
> interna do Docker.

### 2.3 Código no servidor

**Opção A — Git (recomendado):**

```bash
apt install -y git
mkdir -p /opt/associacao && cd /opt/associacao
git clone <URL_DO_REPO> .
```

**Opção B — rsync (do seu computador):**

```bash
rsync -avz --exclude .venv --exclude .env --exclude db.sqlite3 \
  ./ root@IP_DO_VPS:/opt/associacao/
```

---

## 3. Configurar o `.env` de produção

No servidor:

```bash
cd /opt/associacao
cp .env.example .env
nano .env
```

Checklist mínimo para produção:

| Variável | Valor de produção |
|---|---|
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `dutratech.cloud,www.dutratech.cloud` |
| `CSRF_TRUSTED_ORIGINS` | `https://dutratech.cloud,https://www.dutratech.cloud` |
| `DOMAIN` | `dutratech.cloud` (usado pelo Caddy) |
| `POSTGRES_PASSWORD` | senha forte aleatória |
| `ASSOCIACAO_PIX_CHAVE` | chave PIX oficial da associação |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| SMTP (`EMAIL_HOST` etc.) | configurar se quiser e-mail real (recuperação de senha) |

> O `deploy.sh` valida automaticamente: `SECRET_KEY` não pode ser a de dev e
> `POSTGRES_PASSWORD` não pode estar vazio/padrão.

Exemplo de `.env` de produção:

```ini
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=<token_urlsafe(50)>
DEBUG=False
ALLOWED_HOSTS=dutratech.cloud,www.dutratech.cloud
CSRF_TRUSTED_ORIGINS=https://dutratech.cloud,https://www.dutratech.cloud
DOMAIN=dutratech.cloud

POSTGRES_DB=associacao
POSTGRES_USER=associacao
POSTGRES_PASSWORD=<senha-forte>
POSTGRES_HOST=
POSTGRES_PORT=5432

ASSOCIACAO_NOME=Associação Comercial
ASSOCIACAO_CIDADE=SAO PAULO
ASSOCIACAO_UF=SP
ASSOCIACAO_TELEFONE=(11) 3000-0000
ASSOCIACAO_EMAIL=contato@associacao.com.br
ASSOCIACAO_PIX_CHAVE=<chave-oficial>

TAXA_ASSOCIACAO_VALOR=120.00
CERTIFICADO_DIGITAL_VALOR=350.00

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=noreply@associacao.com.br
```

---

## 4. Subir o site

```bash
cd /opt/associacao
./deploy.sh up
```

O que acontece:

1. Build da imagem da app (Python 3.12 + gunicorn + whitenoise).
2. Postgres sobe e passa no healthcheck.
3. App roda `migrate` + `collectstatic` e sobe o gunicorn.
4. Caddy sobe, obtém o certificado Let's Encrypt (ouvia 80/443) e serve
   `https://dutratech.cloud` (e `www`).

Verifique:

```bash
./deploy.sh ps        # todos os serviços Up (healthy)
curl -I https://dutratech.cloud   # deve retornar HTTP 200 (ou 301/302)
```

Crie o superusuário (admin):

```bash
./deploy.sh superuser
```

Acesse `https://dutratech.cloud/admin/`.

---

## 5. Rotina de operação

| Ação | Comando |
|---|---|
| Atualizar deploy | `git pull` (ou rsync) e `./deploy.sh up` |
| Ver logs | `./deploy.sh logs app` |
| Status | `./deploy.sh ps` |
| Aplicar migrations manualmente | `./deploy.sh migrate` |
| Comando avulso | `./deploy.sh manage check --deploy` |
| Backup do banco | `./deploy.sh backup` |
| Restaurar backup | `./deploy.sh restore backups/db-xxx.sql.gz` |
| Parar tudo | `./deploy.sh down` |

### 5.1 Backup automático (cron)

No servidor:

```bash
crontab -e
```

```cron
# Backup diário às 3h (mantém arquivos em /opt/associacao/backups)
0 3 * * * cd /opt/associacao && ./deploy.sh backup >> backups/backup.log 2>&1
# Limpeza: mantém apenas os 30 backups mais recentes
10 3 * * * ls -1t /opt/associacao/backups/db-*.sql.gz | tail -n +31 | xargs -r rm -f
```

Copie os backups para fora do VPS periodicamente (ex.: `scp`, storage).

### 5.2 Atualizações de código

```bash
cd /opt/associacao
git pull --ff-only
./deploy.sh up      # rebuild + restart; migrations rodam automaticamente
```

O Caddy só recarrega a config se `deploy/Caddyfile` mudar — nesse caso:

```bash
./deploy.sh restart caddy
```

---

## 6. Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| Caddy log: erro de certificado / ACME challenge | DNS não aponta para o VPS | Aguarde propagação (`dig`); libere 80/443 no firewall |
| `400 Bad Request` no admin/POST | `CSRF_TRUSTED_ORIGINS` errado no `.env` | Inclua `https://dutratech.cloud` e reinicie: `./deploy.sh restart app` |
| `DisallowedHost` no log | `ALLOWED_HOSTS` sem o domínio | Corrija o `.env` e `./deploy.sh restart app` |
| Erro 502 | App não subiu | `./deploy.sh logs app` (migrations/secret) |
| Site fora do ar após reboot | OK com `restart: unless-stopped`; se não | `./deploy.sh up` |
| Postgres pedindo senha | `.env` trocado com volume antigo | Restaurar `pgdata` ou recriar volume (perde dados) |
| Cloudflare 522 | VPS não respondendo | Confira `./deploy.sh ps` e firewall |

Logs úteis:

```bash
./deploy.sh logs caddy
./deploy.sh logs app
./deploy.sh logs db
docker compose -f docker-compose.prod.yml exec app \
  uv run python manage.py check --deploy
```

---

## 7. Checklist final de produção

- [ ] DNS `@` e `www` apontando para o VPS e propagado
- [ ] `SECRET_KEY` aleatória (não a de dev)
- [ ] `POSTGRES_PASSWORD` forte
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` com o domínio
- [ ] `ASSOCIACAO_PIX_CHAVE` = chave oficial
- [ ] Superusuário criado e senha trocada
- [ ] `https://dutratech.cloud` respondendo com cadeado no navegador
- [ ] Backup agendado (cron) e um backup manual feito
- [ ] E-mail SMTP configurado (recuperação de senha)
