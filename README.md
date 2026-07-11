# Encurtador API

Backend do **LinkLab** — API de encurtamento de URLs com contagem de cliques,
construída com FastAPI e Postgres.

## O que este projeto faz

- Encurta uma URL longa em um código curto (`/shorten`)
- Redireciona quem acessa o código curto para a URL original, registrando o clique (`/{codigo}`)
- Lista os links do usuário logado (`/links`)
- Mostra estatísticas de cliques de um link (`/stats/{codigo}`)
- Autenticação de usuários com JWT (`/auth/registrar`, `/auth/login`, `/auth/me`)

Cada link pertence a um usuário — não é mais possível criar ou listar links sem
estar autenticado.

## Stack

- **FastAPI** — framework web
- **SQLAlchemy** — ORM
- **Postgres** — banco de dados
- **psycopg (v3)** — driver de conexão com o Postgres
- **Passlib (bcrypt)** — hash de senha
- **python-jose** — geração e validação de JWT

## Rodando localmente

### Pré-requisitos

- **Python 3.13** (versão travada do projeto — veja `.python-version`).
  Versões mais novas (3.14+) ainda não têm suporte oficial de algumas
  dependências (`pydantic-core`/PyO3), então evite usá-las aqui.
- Docker (para subir o Postgres) ou um Postgres já rodando na sua máquina

No Ubuntu/WSL, se você tiver uma versão diferente instalada, adicione o
Python 3.13 sem remover a que já existe:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.13 python3.13-venv -y
```

### 1. Clonar e criar o ambiente virtual

```bash
python3.13 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Subir o banco de dados

```bash
docker compose up -d
```

Isso sobe um Postgres em `localhost:5432` com usuário `admin`, senha `admin123`
e banco `encurtador` (valores definidos em `docker-compose.yml`).

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Os valores padrão do `.env.example` já são compatíveis com o `docker-compose.yml`.
Ajuste `JWT_SECRET_KEY` se quiser (para desenvolvimento local, o padrão já funciona).

Repare que a `DATABASE_URL` usa o prefixo `postgresql+psycopg://` — isso indica
ao SQLAlchemy para usar o driver psycopg v3.

### 4. Rodar a API

```bash
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`. A documentação interativa (Swagger) fica
em `http://localhost:8000/docs`.

### 5. Rodar os testes

Com o Postgres do passo 2 rodando:

```bash
pytest
```

## Estrutura do projeto
app/
main.py       # instancia o FastAPI, CORS e inclui as rotas
database.py   # conexão com o Postgres (SQLAlchemy)
models.py     # modelos de tabela: User, Link, Click
schemas.py    # schemas Pydantic (validação de entrada/saída)
routes.py     # todas as rotas da API
auth.py       # hash de senha, criação/validação de JWT
tests/
test_api.py   # testes automatizados (pytest)

## Endpoints principais

| Método | Rota               | Autenticação | Descrição                          |
|--------|--------------------|--------------|--------------------------------------|
| POST   | `/auth/registrar`  | não          | Cria uma conta                      |
| POST   | `/auth/login`      | não          | Retorna um token JWT                |
| GET    | `/auth/me`         | sim          | Dados do usuário logado             |
| POST   | `/shorten`         | sim          | Encurta uma URL (vira dona do link) |
| GET    | `/links`           | sim          | Lista os links do usuário logado    |
| GET    | `/stats/{codigo}`  | não          | Estatísticas de um link             |
| GET    | `/{codigo}`        | não          | Redireciona e conta o clique        |

Rotas protegidas exigem o header `Authorization: Bearer <token>`, obtido em
`/auth/login`.
