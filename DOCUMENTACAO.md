# Documentação — Solicitações e Respostas

Registro do que foi solicitado no prompt e do que foi respondido/aprovado,
aplicado à versão **Python/Django** do projeto.

---

## 1. Solicitação inicial (prompt)

### 1.1 Papel assumido

> "Atue como uma especialista em criação de sites com páginas dinâmicas,
> responsivas, estáveis, confiáveis e seguras. Padrões de design e arquitetura
> limpas, autenticação e autorização."

**Resposta:** atuação confirmada com foco em:

- Frontend dinâmico, responsivo e acessível
- Backend com arquitetura limpa, APIs estáveis e confiáveis
- Segurança: autenticação, autorização e boas práticas (OWASP)
- Qualidade: padrões de design, testes e manutenibilidade

### 1.2 Solicitação do site

> "Preciso criar um site para atender a uma associação comercial para oferecer
> serviços como: consulta de cpf/cnpj, criação de certificado digital, cadastro
> de associados e etc."

**Resposta:** levantamento de requisitos por perguntas ao cliente (seção 2),
seguido de plano de arquitetura (seção 3) e implementação (seção 5).

### 1.3 Mudança de direção solicitada

> "Refaça a estrutura para usar Python e não wordpress."

**Resposta:** arquitetura redesenhada em **Python + Django**, mantendo 100%
dos requisitos aprovados. Motivo da escolha de Django:

- Admin completo de fábrica (gestão de associados, solicitações, pagamentos)
- Auth maduro (login, senhas, sessões, CSRF, reset de senha)
- Forms com validação server-side e ORM
- Templates responsivos sem SPA pesada

> Alternativa avaliada: FastAPI exigiria construir admin e auth do zero —
> não compensa para este caso.

### 1.4 Aprovação para iniciar

> "Deixe configurável no .env e pode iniciar a implementação com essa estrutura"

**Resposta:** implementação concluída com todas as configurações (identidade,
valores, chave PIX, limites) externalizadas no `.env`.

---

## 2. Perguntas e respostas (requisitos)

| # | Pergunta | Resposta escolhida | Como foi implementado (Python) |
|---|---|---|---|
| 1 | Stack tecnológica | ~~WordPress~~ → **Python (mudança posterior)** | Django 5 + Templates + CSS/JS próprios |
| 2 | Área logada | **Sim, com login completo** | `django.contrib.auth` + User custom + painel (`apps/associados`) |
| 3 | Consulta CPF/CNPJ | **API externa (BrasilAPI)** | Proxy server-side via `httpx` com cache e rate-limit (`apps/consultas`); CPF com provider plugável (Serpro) por conformidade LGPD |
| 4 | Escopo inicial | **Completo com painel** | Site institucional + cadastro + consulta + painel do associado + solicitações |
| 5 | Pagamentos | **Sim, apenas PIX** | Payload EMV/BR Code próprio + QR client-side (`apps/pagamentos`) |

---

## 3. Plano aprovado (arquitetura Python/Django)

### 3.1 Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 + Django |
| Banco | SQLite (dev local) / PostgreSQL 16 (Docker/prod) |
| Frontend | Django Templates + CSS mobile-first + JS leve |
| Consulta CNPJ | BrasilAPI (gratuita, `httpx`, cache + rate-limit) |
| PIX | Payload EMV gerado em Python puro + QR client-side |
| Deploy | Docker Compose (app + Postgres) ou `uv run`; produção com Caddy (HTTPS) |

### 3.2 Estrutura de apps

```
config/        # settings (base/dev/prod), urls, wsgi/asgi
apps/
  core/           # páginas institucionais + identidade (context processor)
  associados/     # User custom, perfil, cadastro, auth, painel
  consultas/      # validador CPF/CNPJ, BrasilAPI, cache, rate-limit, log
  solicitacoes/   # catálogo de serviços + máquina de status
  pagamentos/     # payload PIX EMV + registro de pagamentos
templates/        # base + páginas
static/           # css/, js/
```

### 3.3 Modelo de dados

- **User** (AbstractUser) com `role`: associado | staff
- **Associado** (OneToOne → User): documento (CPF/CNPJ), razão social, endereço,
  matrícula automática (`ASS000001`), status `pendente | ativo | inativo`
- **Servico**: catálogo com valor e slug (taxa-associancao, certificado-digital…)
- **Solicitacao**: protocolo (`SOL000001`), serviço, valor, status, datas
- **Pagamento**: OneToOne com Solicitacao, payload PIX, flag `pago`, confirmação
- **ConsultaLog**: auditoria de consultas (hash SHA-256 do documento)

### 3.4 Fluxos aprovados

**Cadastro:**
form público → valida CPF/CNPJ (mod-11) → cria User + Associado(`pendente`)
→ admin aprova em massa → `ativo` → painel liberado

**Painel do associado:**
dados da conta · serviços disponíveis · minhas solicitações · pagamentos ·
atalho para consulta · edição de perfil

**Solicitação + PIX:**
1. Associado solicita serviço → `aguardando_pagamento`
2. Payload EMV (chave do `.env`) → QR Code + copia-e-cola
3. "Já realizei o pagamento" → `em_analise`
4. Staff confirma no admin → `aprovado` → `em_andamento` → `concluido`
   (ou `cancelado`)

**Consulta CNPJ:**
form → validação de dígitos → `wp_remote_get` equivalente (`httpx.get` na
BrasilAPI) → cache 24h + rate-limit 10/min por IP → exibe razão social,
situação, endereço, CNAE, quadro societário

**Consulta CPF:**
MVP valida formato + dígitos (dado de PF não é público — LGPD); interface de
provider plugável pronta (Serpro via `SERPRO_API_TOKEN`/`SERPRO_API_URL`)

### 3.5 Segurança (checklist aprovado)

- CSRF + sessões nativas do Django; senhas com validadores (PBKDF2)
- `@login_required` em toda view protegida
- Validação/sanitização nos Forms; autoescape nos templates
- Rate-limit + cache nas consultas; auditoria com hash (não guarda CPF/CNPJ cru)
- `prod.py`: `DEBUG=False`, HSTS, redirect SSL, cookies `Secure`
- Escapamento de output (`esc_*` no plano → autoescape do Django na entrega)

---

## 4. Configuração via `.env` (solicitada pelo cliente)

| Variável | Descrição |
|---|---|
| `ASSOCIACAO_NOME` | Nome no site e no payload PIX |
| `ASSOCIACAO_CIDADE` / `ASSOCIACAO_UF` | Cidade/UF (cidade entra no payload PIX) |
| `ASSOCIACAO_TELEFONE` / `ASSOCIACAO_EMAIL` | Contatos |
| `ASSOCIACAO_PIX_CHAVE` | Chave PIX estática (placeholder em dev) |
| `TAXA_ASSOCIACAO_VALOR` | Valor da taxa anual |
| `CERTIFICADO_DIGITAL_VALOR` | Valor do certificado digital |
| `CONSULTA_RATE_LIMIT` | Consultas/min por IP (padrão 10) |
| `CONSULTA_CACHE_HORAS` | Cache das consultas (padrão 24h) |
| `SERPRO_API_TOKEN` / `SERPRO_API_URL` | Provider opcional de consulta CPF |
| `POSTGRES_*` | Banco em Docker/prod (vazio = SQLite em dev) |

---

## 5. Entrega final (estado implementado)

### 5.1 Funcionalidades entregues

- [x] Site institucional responsivo (Home, Sobre, Serviços, Contato)
- [x] Cadastro público de associado com validação CPF/CNPJ (mod-11)
- [x] Autenticação completa (login, logout, reset de senha por e-mail)
- [x] Painel do associado (solicitações, pagamentos, dados, atalhos)
- [x] Consulta CNPJ real (BrasilAPI) com cache e rate-limit
- [x] Consulta CPF: validação + provider plugável
- [x] Solicitação de serviços com máquina de status
- [x] Pagamento PIX: payload EMV + QR Code + confirmação
- [x] Admin customizado (aprovações, status em massa, pagamentos, auditoria)
- [x] Configuração tudo via `.env`
- [x] Docker Compose (app + Postgres) e execução local com `uv`
- [x] Deploy de produção: `docker-compose.prod.yml` (Caddy/HTTPS) + `deploy.sh` + `DEPLOY.md`
- [x] Testes automatizados (12) cobrindo o fluxo completo

### 5.2 Bugs corrigidos durante a implementação

1. **Validador de CNPJ** — indexação incorreta dos pesos do algoritmo mod-11
2. **Conflito de URL** — `/servicos/` ambígua entre `core` e `solicitacoes`
   (app de solicitações movido para `/solicitacoes/`)
3. **Payload PIX EMV** — descrição longa gerava length de 3 dígitos no campo 26
   (máx. EMV = 99 chars / 2 dígitos); corrigido com orçamento de bytes e
   validação `_tlv`
4. **Compose** — comando multi-linha quebrava gunicorn (bind em `127.0.0.1`);
   corrigido para comando em linha única

### 5.3 Validações executadas

- 12/12 testes automatizados OK (`uv run python manage.py test`)
- Fluxo via HTTP: cadastro → login → painel → solicitação → PIX → confirmação
- Consulta CNPJ real (BrasilAPI) validada fora e dentro do container
- Estrutura TLV e CRC16 do payload PIX validados por teste e manualmente
- `manage.py check --deploy` (com valores reais de produção)

### 5.4 Credenciais de demonstração

- Admin: `admin` / `Admin#123456` (criado só para dev — trocar em produção)
- Chave PIX de dev no `.env`: `a1b2c3d4-e5f6-7890-abcd-1234567890ef`
  (substituir pela chave oficial da associação)
