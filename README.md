# Estoque Leigo (V1)

Base do sistema de estoque para rodar **localmente** (web) com persistência em **SQLite**, usando **Docker Compose**.

## Stack

- Backend: **FastAPI**
- Banco: **SQLite** (arquivo em volume)
- Frontend: **HTML/JS** estático (servido pelo próprio FastAPI)

## Requisitos

- Docker + Docker Compose

## Rodar com Docker (recomendado)

1. Copie o `.env.example` para `.env` e **configure o login**:

```bash
cp .env.example .env

# Gere um hash para a senha e coloque em ADMIN_PASSWORD_HASH
python -c "from passlib.context import CryptContext; ctx=CryptContext(schemes=['pbkdf2_sha256']); print(ctx.hash('sua-senha-aqui'))"
```

> Importante: `SESSION_SECRET` é obrigatório.

2. Suba tudo:

```bash
docker compose up --build
```

3. Abra no navegador:

- http://localhost:8000

Você será redirecionado para `/login` se não estiver autenticado.

Endpoints úteis:

- `GET /health` (público)
- `GET /api/products` (protegido)
- `POST /api/login` (público)
- `POST /api/logout` (protegido)

## Persistência do SQLite

O SQLite fica em `./data/app.db` (mapeado para `/data/app.db` dentro do container). Isso garante persistência entre restarts.

Para testar rapidamente:

1. Acesse a UI, crie uma nota.
2. Pare e suba novamente:

```bash
docker compose down
docker compose up
```

As notas devem continuar.

## Rodar sem Docker (opcional)

Requer Python 3.12+

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e "./backend[dev]"

export SQLITE_PATH=./data/app.db
uvicorn app.main:app --reload --port 8000
```

## QA / Testes

```bash
bash scripts/qa.sh
```

## Estrutura

- `backend/` — FastAPI + SQLite
- `frontend/static/` — página simples para validar que o app está no ar
- `data/` — volume local do SQLite (gitignored)
