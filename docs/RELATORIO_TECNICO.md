# RELATÓRIO TÉCNICO — MEAL CONTROL

**Data:** 19 de novembro de 2026  
**Entrega:** MVP de backend + roadmap de evolução para SaaS  
**Repositório previsto:** https://github.com/ArturTeschdosSantos/Meal_control

## 1. Resumo executivo

Meal Control é uma proposta de plataforma SaaS para que escolas gerenciem os acessos ao refeitório e contabilizem almoços efetivamente registrados. A primeira entrega prioriza a integridade do histórico e a segurança dos registros: autenticação, separação lógica por escola, operações de entrada/saída e relatório consolidado. A interface gráfica, QR Codes, integrações com catracas e faturamento pertencem às fases seguintes.

O repositório remoto foi verificado como vazio na data da análise; a implementação deste pacote é nova e **não foi enviada ao GitHub**. Os arquivos são entregues para publicação pelo proprietário.

## 2. Problema e objetivos

A gestão manual dos almoços gera retrabalho, subnotificação, duplicidade e pouca visibilidade do consumo real. O sistema deve permitir registrar cada acesso, evitar duplicidades, consultar quem entrou e quem saiu e emitir números confiáveis para a cozinha e para a gestão.

**Objetivos:** registrar a refeição servida; impedir que o mesmo estudante seja contado duas vezes no mesmo dia; permitir acesso por diferentes escolas sem exposição cruzada; oferecer indicadores diários e históricos; manter a arquitetura pronta para expansão.

## 3. Personas e permissões

- **Administrador escolar:** gerencia estudantes, acessa dados e relatórios de sua escola.
- **Operador do refeitório:** registra entradas e saídas e consulta os totais necessários à operação.
- **Gestor da rede:** papel planejado, para visualizar apenas escolas autorizadas.
- **Superadministrador SaaS:** papel planejado para provisionar novas escolas, suspender contas e administrar planos. Não implementado.

A versão inicial cria apenas o primeiro administrador por escola; a inclusão/gestão de novos operadores é planejada. As rotas de registro aceitam qualquer usuário autenticado e ativo.

## 4. Requisitos funcionais

| ID | Requisito | Entrega |
|---|---|---|
| RF01 | Registrar escola e primeiro administrador | MVP local; endpoint aberto, não apto a produção |
| RF02 | Login por escola + e-mail + senha | Implementado |
| RF03 | Cadastrar e listar alunos, matrícula única por escola | Implementado |
| RF04 | Registrar entrada do almoço (data/hora/operador) | Implementado |
| RF05 | Impedir almoço duplicado por aluno/dia | Implementado com restrição no banco |
| RF06 | Registrar saída vinculada à entrada | Implementado |
| RF07 | Contabilizar almoços, saídas e presentes | Implementado |
| RF08 | Relatório de totais por intervalo | Implementado |
| RF09 | QR Code / leitor de cartão | Planejado |
| RF10 | Exportação CSV/PDF e filtros por turma | Planejado |
| RF11 | Planejamento de demanda e alertas de capacidade | Planejado |
| RF12 | Várias refeições por dia (café, lanche, jantar) | Planejado; MVP apenas almoço |
| RF13 | Gestão de funcionários, turnos e permissões | Planejado |
| RF14 | Portal do gestor com visão multiunidade autorizada | Planejado |
| RF15 | Auditoria de correções manuais | Planejado |

## 5. Requisitos não funcionais

**Segurança:** credenciais protegidas com Argon2, JWT de curta duração, autorização por organização, HTTPS obrigatório na implantação; logging e revogação evolutivos. **Integridade:** unicidade por `(student_id, meal_date)` no banco; entrada/saída não removidas pela interface. **Disponibilidade:** backups, alertas, health checks e restore testado antes de produção. **Usabilidade:** operação rápida em tablets e desktops, poucos cliques e busca de aluno; interface não entregue. **Privacidade:** minimização e política de retenção de dados de menores à luz da LGPD; avaliação jurídica antes de produção. **Desempenho:** paginação, índices e testes de carga antes de definição de SLO.

## 6. Seleção tecnológica

| Item | Ferramenta | Critério |
|---|---|---|
| API | Python 3.12 / FastAPI | Validação declarativa, documentação OpenAPI automática, produtividade |
| Modelo relacional | SQLAlchemy 2 | Transações e mapeamento estruturado |
| Banco | PostgreSQL 17 | ACID, unicidade, índices, possibilidade de RLS |
| Migrações | Alembic | Mudanças versionadas e reproduzíveis |
| Identidade | PyJWT / Argon2-cffi | Tokens e hash resistente de senhas |
| Infra local | Docker / Compose | Ambiente reprodutível |
| Testes | Pytest / HTTPX | Fluxos HTTP e regras críticas |
| Pipeline | GitHub Actions | Execução dos testes em push e PR |
| Futuro frontend | React + TypeScript | Componentização e UX de operação |
| Futuro monitoramento | OpenTelemetry + Prometheus/Grafana/Sentry | Métricas, tracing e erros (não instalados) |

**Arquitetura escolhida:** monólito modular. Uma API serve diversas escolas; cada registro de usuário, aluno e refeição contém `school_id`. A opção reduz custo operacional, sem bloquear extração futura de serviços. Não iniciar com Kubernetes, Kafka ou microsserviços antes de medir a necessidade.

## 7. Modelo de dados

```text
SCHOOL (id, name, slug, active)
  ├── USER (id, school_id, email, password_hash, role, active)
  ├── STUDENT (id, school_id, enrollment, name, classroom, shift, active)
  └── MEAL (id, school_id, student_id, meal_date, entered_at, exited_at,
             entered_by, exited_by)
```

Constraints: `UNIQUE(school_id, enrollment)` em STUDENT; `UNIQUE(school_id, email)` em USER; `UNIQUE(student_id, meal_date)` em MEAL. As chaves estrangeiras mantêm vínculos básicos. No futuro adicionar restrições compostas para integridade de `school_id` no nível relacional, RLS, trilha de auditoria e índices compostos específicos de consulta.

## 8. Jornada do usuário e regras de contagem

1. Administrador provisona a escola e efetua login.
2. Cadastra aluno com matrícula e turma.
3. No refeitório, operador identifica aluno (na versão inicial, por UUID consultado via API).
4. `POST /entry` verifica existência e atividade na escola e insere uma refeição do dia. Outra entrada no mesmo dia retorna HTTP 409, inclusive sob corrida de requisições no PostgreSQL, graças ao índice UNIQUE.
5. `POST /exit` localiza o almoço do dia ainda aberto, grava saída e operador; repetição retorna 409.
6. Relatório diário apresenta: **almoços = entradas únicas**, **saídas = almoços com `exited_at`**, **dentro = almoços − saídas**.

**Exemplo:** 500 alunos cadastrados; 321 entradas; 290 saídas. Resultado: 321 almoços contabilizados, 290 saídas e 31 registros ainda abertos. Atenção: “dentro” é uma estimativa operacional baseada em registros; saídas não registradas podem distorcê-la.

**Regra de escopo:** uma refeição almoço por estudante por data local, no fuso configurado; múltiplos serviços/dias noturnos ainda precisam de desenho próprio. Registro de saída ocorre apenas no dia da entrada no MVP.

## 9. Contrato de API

- `POST /v1/schools`: provisionamento inicial local (não expor publicamente em produção).
- `POST /v1/auth/login`: token Bearer.
- `POST /v1/students`: cadastro (admin).
- `GET /v1/students?limit=100&offset=0`: listagem paginada da escola autenticada.
- `POST /v1/meals/{student_id}/entry`: registra almoço do dia, 201 ou 409.
- `POST /v1/meals/{student_id}/exit`: registra saída, 200 ou 404/409.
- `GET /v1/reports/daily?day=YYYY-MM-DD`: totais de um dia.
- `GET /v1/reports/period?start=YYYY-MM-DD&end=YYYY-MM-DD`: agregação por dia (máx. 366 dias).
- `GET /health`, `/docs`, `/openapi.json`: observabilidade básica e documentação.

## 10. Implementação e execução

Ver `README.md` do pacote: configurar `.env` a partir do exemplo, gerar JWT_SECRET forte, executar `docker compose up --build`, testar em `/docs`. O Compose usa PostgreSQL e aplica a migração inicial Alembic ao iniciar a API. Sem Docker, instalar requirements, usar PostgreSQL externo ou SQLite local para laboratório, aplicar `alembic upgrade head` e iniciar `uvicorn`.

## 11. Qualidade e validação

A suíte Pytest cobre: entrada válida, tentativa duplicada, saída sem entrada, saída repetida, números do dia, isolamento de escola, proteção de listagem não autenticada e matrícula duplicada. Testes rodam com SQLite em memória para velocidade; isso **não comprova comportamento do PostgreSQL sob concorrência**. O pipeline Actions executa os testes nos commits e PRs. Antes de produção, rodar integração PostgreSQL, teste de concorrência, pen test, migração rollback, recuperação de backup, avaliação de segurança e LGPD.

## 12. Riscos e limitações conscientes

- Endpoint de criação de escola é intencionalmente aberto no MVP local e precisa ser fechado antes de qualquer exposição pública.
- `JWT_SECRET` possui um fallback somente de desenvolvimento; é obrigatório definir segredo aleatório gerenciado para qualquer ambiente compartilhado.
- Não há refresh/revogação de tokens, MFA, recuperação de conta, rate limit, CORS definido ou operação offline.
- Não existe gestão de operadores, cadastro/edição/desativação via endpoint, exclusão segura, trilha completa de auditoria nem processo de retificação de lançamentos.
- O MVP não oferece UI, QR Code, cartão NFC/RFID, integração com catracas, cobrança, gestão de planos ou relatórios em PDF/CSV.
- `school_id` é filtrado pelas rotas, mas RLS e invariantes de integridade multi-tenant ainda precisam de testes e reforço em banco.
- O campo `lunches_served` representa entradas registradas, não uma prova física independente da entrega do alimento.

## 13. Roadmap de evolução

**Fase 1 — MVP técnico (entregue):** API FastAPI, DB, migração, login, alunos, entrada, saída e dashboards de contagem em JSON; testes de comportamento central.

**Fase 2 — MVP piloto supervisionado:** bloquear provisionamento público; contas de operadores, RBAC e revisão de LGPD; UI web responsiva; QR Code com identificador não sensível; busca por matrícula; logs/auditoria; backup e restauração; integração PostgreSQL e testes de segurança; observação piloto em escola com dados autorizados.

**Fase 3 — SaaS comercial:** onboarding/convites, domínios e branding, planos e faturamento, medição de uso, relatórios CSV/PDF, central de atendimento, notificações, RLS ou isolamento mais forte, métricas de latência/SLO, política de suporte e recuperação de desastre.

**Fase 4 — Inteligência operacional:** projeção de demanda por histórico e calendário, cardápio, desperdício, integração com ERP escolar, múltiplas refeições, captura offline com reconciliação idempotente, alertas e dashboard multiunidade.

## 14. Critérios de aceite da próxima entrega

Uma instituição deve conseguir cadastrar 100 alunos de teste e registrar 100 entradas distintas sem duplicidade; cada repetição deve retornar 409. Uma segunda escola não pode visualizar alunos, refeições nem totais da primeira. As contagens devem ser reproduzíveis por consulta ao banco. Os testes precisam passar em PostgreSQL sob requisições concorrentes. A UI deve ser acessível por teclado e oferecer feedback claro de entrada/saída. O piloto com dados reais só deve ocorrer após revisão de LGPD, segurança, retenção e autorização escolar.

## 15. Conclusão

A solução entregue oferece uma base de backend executável, orientada às regras essenciais do refeitório, com rastreabilidade básica e preparação para múltiplas escolas. Não deve ser confundida com uma plataforma SaaS finalizada. O próximo investimento prioritário é segurança de produção + experiência do operador + testes de banco real, antes de funções avançadas e cobrança.
