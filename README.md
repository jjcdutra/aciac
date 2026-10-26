# Associação Comercial — Site institucional + área do associado

Site dinâmico, responsivo e seguro para associação comercial, com cadastro de
associados, área logada (painel), consulta de CPF/CNPJ, solicitação de serviços
(certificado digital etc.) e pagamento via PIX (copia-e-cola + QR Code).

> 📄 Registro das solicitações, respostas e decisões técnicas:
> [DOCUMENTACAO.md](DOCUMENTACAO.md)

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 + Django |
| Banco | SQLite (dev local) / PostgreSQL 16 (Docker/produção) |
| Frontend | Django Templates + CSS próprio mobile-first + JS leve |
| Consulta CNPJ | BrasilAPI (gratuita, via `httpx`, com cache e rate-limit) |
| PIX | Payload EMV (BR Code) gerado em Python puro + QR client-side |
| Deploy | Docker Compose (app + Postgres) ou `uv run` direto; produção com Traefik (HTTPS) |

## Estrutura

```
config/            # settings (base/dev/prod), urls, wsgi/asgi
apps/
  core/            # páginas institucionais + context processor da identidade
  associados/      # User custom, perfil, cadastro, auth, painel
  consultas/       # validador CPF/CNPJ + BrasilAPI + cache/rate-limit + log
  solicitacoes/    # catálogo de serviços + máquina de status
  pagamentos/      # payload PIX EMV + registro de pagamentos
templates/         # base + páginas (core, associados, consultas, ...)
static/            # css/, js/
```

## Como rodar (desenvolvimento local)

Pré-requisitos: [uv](https://docs.astral.sh/uv/) e Python 3.12.

```bash
cp .env.example .env      # edite os valores (nome da associação, chave PIX etc.)
uv sync                   # instala dependências
uv run python manage.py migrate
uv run python manage.py createsuperuser   # acesso ao admin
uv run python manage.py runserver         # http://127.0.0.1:8000
```

Com SQLite local (padrão): basta `POSTGRES_HOST=` vazio no `.env`.

## Como rodar (Docker)

```bash
cp .env.example .env       # configure SECRET_KEY, senha do banco e chave PIX
docker compose up --build  # app em http://localhost:8000
```

> O compose injeta `POSTGRES_HOST=db` e roda migrations + collectstatic na subida.

## Como publicar em produção

Stack de produção (`docker-compose.prod.yml`): Postgres + app, servidos pelo
**Traefik** (proxy reverso com HTTPS automático via Let's Encrypt — o mesmo
do n8n no VPS). Guia completo
(Hostinger VPS, DNS, firewall, backups): **[DEPLOY.md](DEPLOY.md)**.

```bash
cp .env.example .env   # configure SECRET_KEY, ALLOWED_HOSTS, senha do banco etc.
./deploy.sh up         # build + migrate + collectstatic + gunicorn
./deploy.sh superuser  # cria o admin
```

| Arquivo | Papel |
|---|---|
| `docker-compose.prod.yml` | Stack de produção (app/Postgres sem porta pública; labels Traefik) |
| `deploy.sh` | Atalhos: `up`, `logs`, `backup`, `restore`, `migrate`… |

## Configuração via `.env`

Todas as identidades e valores são configuráveis:

| Variável | Descrição |
|---|---|
| `ASSOCIACAO_NOME` | Nome exibido no site e no payload PIX |
| `ASSOCIACAO_CIDADE` / `ASSOCIACAO_UF` | Cidade/UF (cidade entra no payload PIX) |
| `ASSOCIACAO_TELEFONE` / `ASSOCIACAO_EMAIL` | Contatos no rodapé e páginas |
| `ASSOCIACAO_PIX_CHAVE` | Chave PIX estática (CPF/CNPJ/e-mail/UUID) |
| `TAXA_ASSOCIACAO_VALOR` | Valor da taxa anual |
| `CERTIFICADO_DIGITAL_VALOR` | Valor do certificado digital |
| `CONSULTA_RATE_LIMIT` | Consultas por minuto por IP (padrão 10) |
| `CONSULTA_CACHE_HORAS` | Cache das respostas de consulta (padrão 24h) |
| `SERPRO_API_TOKEN` / `SERPRO_API_URL` | Provider autorizado de consulta CPF (opcional) |

## Funcionalidades

- **Cadastro público** de associado com validação CPF/CNPJ (mod-11) → status
  *pendente* → aprovação em massa no admin → *ativo*
- **Área logada**: painel com solicitações, pagamentos, dados cadastrais e
  atalhos (recuperar senha incluída)
- **Consulta CNPJ** em tempo real (BrasilAPI) com cache 24h, rate-limit por IP
  e log de auditoria (hash SHA-256 do documento, nunca o número cru)
- **Consulta CPF**: valida dígitos; provider externo plugável (Serpro) via
  `.env` — dado de PF não é público (conformidade LGPD)
- **Solicitação de serviços** com máquina de status:
  `aguardando_pagamento → em_analise → aprovado → em_andamento → concluido`
  (ou `cancelado`)
- **PIX**: payload EMV/copia-e-cola com CRC16-CCITT + QR Code (client-side),
  confirmação pelo associado e baixa pelo staff no admin
- **Admin Django** customizado: aprovação de associados, mudança de status em
  massa, confirmação de pagamentos, auditoria de consultas

## Segurança

- CSRF + sessões nativas do Django; senhas com validadores (PBKDF2)
- Views protegidas com `@login_required`; painel restrito ao usuário logado
- Rate-limit + cache nas consultas (proteção contra abuso da API externa)
- Inputs validados/sanitizados nos Forms; autoescape nos templates
- `prod.py`: `DEBUG=False`, HSTS, redirect SSL, cookies `Secure`/`SameSite`
- Auditoria de consultas com hash do documento (LGPD)

## Testes

```bash
uv run python manage.py test
```

Cobertura: cadastro → login → painel, consulta CNPJ real, rate-limit,
solicitação → PIX (validação TLV/CRC do payload) → confirmação de pagamento.

## Rotina de produção (checklist)

Passo a passo detalhado: [DEPLOY.md](DEPLOY.md).

1. `SECRET_KEY` forte e `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` reais no `.env`
2. `ASSOCIACAO_PIX_CHAVE` com a chave PIX oficial da associação
3. HTTPS ativo (Traefik no VPS obtém e renova o certificado)
4. `./deploy.sh superuser` + revisão de permissões
5. Backup do Postgres (`./deploy.sh backup` + cron — ver DEPLOY.md)
6. E-mail transacional configurado (`EMAIL_BACKEND` SMTP) para recuperação de senha
