# Estoque Leigo (V1)

Base do sistema de estoque para rodar **localmente** (web) com persistência em **SQLite**, usando **Docker Compose**.

## Stack

- Backend: **FastAPI**
- Banco: **SQLite** (arquivo em volume)
- Frontend: **HTML/JS** estático (servido pelo próprio FastAPI)

## Requisitos

- Docker + Docker Compose

## Rodar com Docker (recomendado)

1. (Opcional) Copie o `.env.example` para `.env` e ajuste se quiser:

```bash
cp .env.example .env
```

2. Suba tudo:

```bash
docker compose up --build
```

3. Abra no navegador:

- http://localhost:8000

Endpoints úteis:

- `GET /health`
- `GET /api/notes`
- `POST /api/notes` com body `{"content":"..."}`

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
