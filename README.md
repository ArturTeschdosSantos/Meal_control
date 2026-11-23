# Meal Control 🍽️

**API REST para controle de entrada e saída de estudantes no refeitório escolar e contabilização de almoços.** O projeto foi projetado para evoluir para um SaaS multi-instituição, com isolamento lógico por escola.

> **Estado:** MVP de backend funcional para desenvolvimento e demonstração; **não está pronto para uso com dados reais de menores em produção** sem as medidas da seção Segurança e produção.

## Stack

- **Python 3.12 + FastAPI** — API REST e OpenAPI/Swagger.
- **PostgreSQL 17** — banco de dados relacional.
- **SQLAlchemy 2 + Alembic** — ORM e migrações versionadas.
- **JWT (PyJWT) + Argon2** — autenticação e hash de senhas.
- **Docker Compose** — API e PostgreSQL para desenvolvimento.
- **Pytest + HTTPX** — testes de integração HTTP.

## Funcionalidades implementadas

- Criar escola e seu primeiro administrador (bootstrap de demonstração).
- Login com escola, e-mail e senha; emissão de JWT.
- Cadastro/listagem paginada de alunos por escola.
- Entrada e saída no almoço com registro de horário e operador.
- Bloqueio de segunda entrada do mesmo aluno no mesmo dia, **protegido por índice UNIQUE no banco**.
- Bloqueio de saída sem entrada ou repetida.
- Relatório diário com almoços, saídas e pessoas ainda no refeitório.
- Relatório por período (até 366 dias), com total consolidado por dia.
- Isolamento por `school_id` em todas as consultas de alunos/refeições.
- Testes automatizados e CI básico.

## Execução com Docker (recomendado)

Pré-requisitos: [Docker](https://www.docker.com/) + Docker Compose.

```bash
cp .env.example .env
# Troque JWT_SECRET por uma chave longa, aleatória e secreta.
docker compose up --build
```

A API estará em `http://localhost:8000`, Swagger em `http://localhost:8000/docs`, esquema OpenAPI em `/openapi.json` e saúde em `/health`.

Em PowerShell, use `Copy-Item .env.example .env` no lugar de `cp`.

> O `.env.example` usa `db` como host; ele só funciona dentro da rede Docker. **Não publique a porta PostgreSQL diretamente.**

Para desligar: `docker compose down`. Para excluir os dados locais também: `docker compose down -v` (**irreversível**).

## Execução local sem Docker

Requer Python 3.12 e PostgreSQL, ou SQLite apenas para experimentação.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
```

Configure `DATABASE_URL` e `JWT_SECRET` no arquivo `.env`. Para teste rápido, `DATABASE_URL=sqlite:///./meal_control.db` (SQLite não é a configuração indicada para produção). Depois:

```bash
alembic upgrade head
uvicorn app.main:app --reload
pytest -q
```

## Exemplo de fluxo API

### 1. Criar escola e admin (somente ambiente local de avaliação)

`POST /v1/schools`:

```json
{
  "name": "Escola Exemplo",
  "slug": "escola-exemplo",
  "admin_email": "admin@example.com",
  "admin_password": "SenhaForteDeTeste2026!"
}
```

### 2. Autenticar

`POST /v1/auth/login`:

```json
{"school_slug":"escola-exemplo","email":"admin@example.com","password":"SenhaForteDeTeste2026!"}
```

Copie o campo `access_token`. Nas rotas protegidas, envie o cabeçalho `Authorization: Bearer SEU_TOKEN` ou use o botão **Authorize** no Swagger.

### 3. Cadastrar estudante

`POST /v1/students` (requer perfil `admin`):

```json
{"enrollment":"2026001","name":"Aluno Exemplo","classroom":"3A","shift":"manha"}
```

Guarde o `id` retornado.

### 4. Registrar entrada e saída

`POST /v1/meals/{student_id}/entry`: cria o almoço de hoje. Nova tentativa retorna **409 Conflict**.

`POST /v1/meals/{student_id}/exit`: registra a saída do almoço de hoje. Sem entrada retorna **404**, repetição retorna **409**.

### 5. Consultar totais

`GET /v1/reports/daily` ou `GET /v1/reports/daily?day=2026-11-19`:

```json
{"date":"2026-11-19","lunches_served":1,"exits":1,"inside":0}
```

`GET /v1/reports/period?start=2026-11-01&end=2026-11-30` retorna totais por dia e acumulado no intervalo.

**Contagem:** cada entrada validada representa um almoço servido. A saída **não** aumenta esse número. O dia de referência usa o fuso `TIMEZONE` (padrão `America/Sao_Paulo`); timestamps são salvos com timezone.

## Principais rotas

| Método | Rota | Permissão |
|---|---|---|
| GET | `/health` | Pública |
| POST | `/v1/schools` | Pública **apenas no MVP local** |
| POST | `/v1/auth/login` | Pública |
| POST | `/v1/students` | Admin |
| GET | `/v1/students` | Usuário autenticado |
| POST | `/v1/meals/{student_id}/entry` | Usuário autenticado |
| POST | `/v1/meals/{student_id}/exit` | Usuário autenticado |
| GET | `/v1/reports/daily` | Usuário autenticado |
| GET | `/v1/reports/period` | Usuário autenticado |

## Organização

```text
app/
  main.py       # rotas e regras do MVP
  models.py     # entidades, constraints e relacionamentos
  schemas.py    # esquemas de entrada/saída
  security.py   # senha, JWT, autorização
  settings.py   # variáveis de configuração
  db.py         # conexão e sessão SQLAlchemy
migrations/      # esquema inicial Alembic
tests/           # testes de integração
.github/workflows/tests.yml
docs/RELATORIO_TECNICO.md
Dockerfile
docker-compose.yml
.env.example
```

## Segurança e produção — pendências obrigatórias

1. **Fechar o cadastro público de escolas (`POST /v1/schools`)**: substituir por provisionamento autenticado de superadmin ou convites autorizados; com rate limit/CAPTCHA se aplicável.
2. Armazenar `JWT_SECRET` em gerenciador de segredos, nunca versionar `.env`; remover o segredo de desenvolvimento e negar início sem segredo de produção.
3. Implantar HTTPS/TLS, políticas de CORS por origem, rate limiting de login e cadastros, observabilidade e trilha de auditoria para ações críticas.
4. Criar gestão de operadores (cadastro, desativação, reset, MFA para administradores), RBAC mais granular e política de expiração/revogação de tokens.
5. Avaliar LGPD, base legal, minimização/retenção de dados, direitos de titulares e responsáveis, contrato com escolas e acesso por perfil; não cadastrar dados reais de menores antes disso.
6. Adicionar testes com **PostgreSQL real** (incluindo concorrência e transações), testes de autorização e varredura de dependências.
7. Criar backups automáticos, restaurá-los em ensaio periódico, configurar monitoramento, logs sem dados sensíveis e plano de resposta a incidentes.
8. Avaliar isolamento por RLS do PostgreSQL, ou banco por escola conforme risco; filtros por `school_id` são apenas a camada inicial.
9. Definir tratamento de correções manuais, relógio/fuso das unidades, dias letivos, tipos de refeição, capacidade, operação offline e política de exclusão/anonimização.

Veja [o relatório técnico](docs/RELATORIO_TECNICO.md) para arquitetura, domínio, riscos, roadmap e critérios de aceite.

## Desenvolvimento

```bash
pytest -q
alembic revision --autogenerate -m "descricao da alteracao"
alembic upgrade head
```

**Contribuições:** faça alterações em uma branch, execute os testes e abra Pull Request. Evite enviar nomes reais de alunos, senhas ou arquivos `.env`.

**Repositório de destino:** https://github.com/ArturTeschdosSantos/Meal_control
