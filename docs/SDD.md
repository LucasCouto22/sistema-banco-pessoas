# SDD — Sistema Banco de Pessoas (Qualy Vortice)

> Este é o documento condutor do desenvolvimento. Antes de continuar qualquer fase futura,
> leia este arquivo inteiro — ele é atualizado ao final de cada fase concluída e é a fonte
> de verdade sobre o que já existe, o que falta e por quê.

## 1. Visão geral

Sistema de gestão de captação de participantes de pesquisa ("Qualy Vortice"), construído em
**Django**, a partir do protótipo estático `prototipo-qualyvortice-v14.html` (2783 linhas —
dashboards, banco de pessoas, projetos, pipeline kanban, termos/contratos, auditoria LGPD,
wizard de importação e página pública de cadastro).

Diferente do protótipo (que simulava papéis com um "entrar como" fake e permissões
hardcoded em JS), este sistema tem **login multiusuário real** e um **painel de permissões**
de verdade — uma matriz nível × permissão gravada no banco e editável pela própria interface
(`/accounts/permissoes/`), com 4 níveis de acesso: **Administrador, Operador, Visualizador,
Freelancer**.

## 2. Como rodar o projeto

```bash
cd sistema-banco-pessoas
.venv/Scripts/python.exe manage.py runserver
```

O ambiente virtual `.venv` já tem `django` e `psycopg[binary]` instalados (Python 3.13.3).
Se recriar o ambiente do zero: `python -m venv .venv && .venv/Scripts/pip install django "psycopg[binary]"`.

Se o schema `pessoas` ainda não existir no banco (banco novo/limpo), rode **antes** do
`migrate`:

```bash
.venv/Scripts/python.exe manage.py ensure_schema
.venv/Scripts/python.exe manage.py migrate
```

(`ensure_schema` existe porque o Django precisa que o schema já exista antes de criar
qualquer tabela — o `search_path` do Postgres não valida isso na conexão, só na hora de
resolver nomes.)

### Usuários para teste (semeados pela migração `accounts.0002_seed_permissoes`)

| Usuário | Senha | Nível |
|---|---|---|
| `admin_demo` | `QualyVortice#2026` | Administrador |
| `operador_demo` | `QualyVortice#2026` | Operador |
| `visualizador_demo` | `QualyVortice#2026` | Visualizador |
| `freelancer_demo` | `QualyVortice#2026` | Freelancer |

Também existe um superusuário real do Django (`/admin/`) chamado `super` — a senha foi
definida na criação e não fica registrada aqui; troque-a se for usar em produção.

Todos os testes de fluxo completo (login, criar projeto, criar participante com CPF válido,
associar a um projeto, avaliar, revelar PII com registro de auditoria, e os bloqueios de
permissão por nível) foram executados manualmente contra o banco Postgres remoto real
durante a Fase 1 e passaram.

### Deploy em produção (Railway)

Desde 2026-08-09 o projeto está preparado para rodar no Railway (o usuário já tinha o
serviço criado, ligado a este repositório no GitHub, mas o primeiro deploy falhou porque
**nenhum código Django tinha sido commitado ainda** — só existia o "Initial commit"
original. Isso foi corrigido: todo o app foi commitado e enviado pra `origin/main`.

Arquivos/config adicionados especificamente para o deploy:

- **`Procfile`** — `web: python manage.py migrate --noinput && python manage.py collectstatic
  --noinput && gunicorn bancopessoas.wsgi:application --bind 0.0.0.0:$PORT --workers 2
  --log-file -`. Roda migração e coleta de estáticos a cada deploy (idempotente — as
  migrações de seed usam `get_or_create`, então rodar de novo não duplica nada) antes de
  subir o servidor.
- **`.python-version`** (`3.13`) — pro Nixpacks (builder do Railway) usar a mesma versão de
  Python do ambiente de desenvolvimento.
- **`requirements.txt`** — adicionado `gunicorn` (servidor WSGI de produção) e `whitenoise`
  (serve os arquivos estáticos direto pela aplicação Django, sem precisar de um serviço de
  storage/CDN separado — suficiente pro tamanho deste projeto).
- **`bancopessoas/settings.py`** — detecta se está rodando no Railway via
  `RAILWAY_ENVIRONMENT`/`RAILWAY_PROJECT_ID` (variáveis que o Railway sempre define) e ajusta
  sozinho, sem precisar configurar nada manualmente na aba Variables:
  - `DEBUG` — `True` localmente (como sempre foi), `False` no Railway por padrão.
  - `ALLOWED_HOSTS` — inclui automaticamente `RAILWAY_PUBLIC_DOMAIN` quando existir; antes
    disso (ou se ainda não gerou domínio), libera `.up.railway.app` como rede de segurança.
  - `SECURE_PROXY_SSL_HEADER` + `SECURE_SSL_REDIRECT` — o Railway termina o HTTPS na borda e
    repassa pra aplicação em HTTP puro com um cabeçalho indicando o protocolo original; sem
    isso o Django acha que toda requisição é insegura.
  - Arquivos estáticos: `STATIC_ROOT` + `STORAGES["staticfiles"]` apontando pro
    `WhiteNoiseMiddleware` (adicionado logo depois do `SecurityMiddleware`), com
    `CompressedManifestStaticFilesStorage` (comprime e versiona os arquivos por hash).
  - **Decisão do usuário**: a senha do banco e a `SECRET_KEY` **continuam fixas no código**
    (não foram movidas pra variável de ambiente) — pergunta feita explicitamente antes do
    primeiro push, o usuário optou por manter como estava desde a Fase 1.
- **Bug real encontrado ao testar `collectstatic` localmente antes de subir**: o
  `chart.umd.js` vendorizado (Fase 2) tem uma referência a um arquivo de sourcemap
  (`chart.umd.js.map`) que nunca foi baixado — o `WhiteNoiseMiddleware`, ao processar os
  arquivos estáticos, tenta resolver essa referência e falha se o arquivo não existir,
  quebrando o `collectstatic` (e portanto o deploy inteiro, já que ele roda no `Procfile`
  antes do servidor subir). Corrigido removendo a linha `//# sourceMappingURL=...` do fim do
  arquivo (só afeta debug no DevTools, não a execução) — testei rodando `collectstatic`
  localmente antes de commitar, exatamente pra pegar esse tipo de coisa antes do Railway.

**O que o usuário ainda precisa fazer manualmente na interface do Railway** (não dá pra
fazer isso por aqui, não tenho acesso à conta/CLI do Railway):
1. Conferir se o novo deploy (disparado automaticamente pelo push) terminou com sucesso na
   aba Deployments.
2. Gerar o domínio público do serviço — aba **Settings → Networking → Generate Domain** (o
   print que o usuário mandou mostrava "Unexposed service", ou seja, isso ainda não tinha
   sido feito).
3. Se quiser trocar a senha do superusuário `super` (criado durante a Fase 1) antes de
   divulgar o link publicamente, pode fazer isso depois pelo próprio `/admin/` ou por
   `manage.py changepassword` (precisaria rodar localmente, apontando pro mesmo banco).

## 3. Decisões técnicas

- **Django 6.1** + **psycopg 3** (`psycopg[binary]`), Python 3.13.3.
- Banco **PostgreSQL remoto (RDS)**, schema `pessoas`. Credenciais ficam **direto em
  `bancopessoas/settings.py`** (decisão explícita do usuário — sem `.env`). Isso significa
  que, se este repositório for para um Git remoto público, a senha do banco vai junto no
  histórico. Se isso mudar no futuro, mover para variáveis de ambiente é a única alteração
  necessária em `settings.py`.
- `DATABASES.OPTIONS.options = '-c search_path=pessoas,public'` reproduz o
  `connect_args={"options": "-csearch_path=pessoas"}` do snippet Flask original.
  `CONN_MAX_AGE=1800` e `CONN_HEALTH_CHECKS=True` cobrem o mesmo objetivo do
  `pool_recycle`/`pool_pre_ping` do SQLAlchemy. **Não há equivalente nativo** no Django para
  `pool_size`/`max_overflow` (um pool de conexões real) — se isso virar gargalo em produção,
  a solução é colocar um PgBouncer na frente do banco (fica no backlog).
- Templates Django server-rendered. O CSS do protótipo foi portado (não 100%, só o
  necessário para as telas atuais) para `static/css/base.css`, mantendo as variáveis de cor,
  sidebar/topbar, badges, tabelas, kanban e formulários. Sem build step de frontend.
- Permissões: **não** é o sistema `django.contrib.auth.Permission` — é um catálogo próprio
  (`accounts/permissions.py::CATALOGO_PERMISSOES`) de permissões nomeadas por ação
  (ex.: `participantes.revelar_pii`, `pagamento.ver`), guardadas em `Permissao` +
  `NivelPermissao` (nível × permissão × concedida). O motivo de não usar o sistema padrão do
  Django é granularidade: as regras do protótipo são por ação de negócio, não por
  modelo/CRUD. `Usuario.tem_permissao(codigo)` é o método central; `is_superuser` sempre
  passa (bypass, para a conta técnica `/admin/`).

## 4. Modelo de dados (Fase 1)

| App | Modelo | Campos principais |
|---|---|---|
| `accounts` | `Usuario` (AUTH_USER_MODEL) | username, password, first/last_name, email, **nivel** (ADMINISTRADOR/OPERADOR/VISUALIZADOR/FREELANCER), telefone |
| `accounts` | `Permissao` | codigo (único), descricao, grupo |
| `accounts` | `NivelPermissao` | nivel, permissao (FK), concedida — matriz editável pelo painel |
| `accounts` | `PreferenciaAvisos` | usuario (OneToOne), triagem_pendente, projetos_vagas, termos_vencendo (bool, opt-out pessoal por categoria de aviso) |
| `accounts` | `AvisoDispensado` | usuario (FK), chave, conteudo, dispensado_em — único por (usuario, chave, conteudo); some da sidebar até o texto do aviso mudar |
| `pessoas` | `Participante` | codigo (gerado `P-AAAA-NNNN`), nome, cpf (validado por dígito verificador), data_nascimento, genero, telefone, email, cidade, uf, cep, escolaridade, profissao, faixa_renda, situacao, forma_pagamento, chave_pix, consentimento_lgpd, **consentimento_versao (FK para `termos.VersaoTermo`, preenchida automaticamente)**, origem_recrutador (FK Usuario), criado_por, timestamps |
| `projetos` | `Projeto` | nome, cliente, metodologia, status, **segmento** (Saúde/Cosméticos/Alimentação/Banco/Tecnologia/Outro), datas, incentivo, valor_perfil, vagas, descricao, perfil_idade_min/max, perfil_genero, perfil_regiao, perfil_renda, perfil_criterios_livres |
| `participacoes` | `Participacao` | participante (FK), projeto (FK), etapa (5 estágios do funil), status, responsavel (FK Usuario), observacao — únique por (participante, projeto) |
| `participacoes` | `Avaliacao` | participacao (1:1), comunicacao/pontualidade/repertorio/nota_geral (1–5), comentario, avaliado_por |
| `auditoria` | `RegistroAcesso` | quando, usuario (FK), titular (código do participante), acao (Visualização/Pagamento/Alteração), detalhe |
| `termos` | `Termo` | nome, tipo (Consentimento/Contrato/Confidencialidade/Cessão de Imagem e Voz) |
| `termos` | `VersaoTermo` | termo (FK), versao (`vAAAA.N`, gerada automaticamente), texto, inicio/fim_vigencia, status (Vigente/Substituída/Agendada/Expirada), autor, publicado_em — única por (termo, versao); `aceites` é uma property calculada, não campo |
| `termos` | `LogAlteracao` | versao (FK), quando, usuario, acao (texto livre) |

Todas as tabelas foram criadas e confirmadas no schema `pessoas` do Postgres remoto
(verificado via `information_schema.tables` ao final da Fase 1).

## 5. Papéis e matriz de permissões

Mapeamento acordado com o usuário: **Freelancer ≈ "Avaliador"** do protótipo (só avalia
participações e vê projetos, sem dados sensíveis, sem pagamento, sem gestão).

| Permissão | Administrador | Operador | Visualizador | Freelancer |
|---|---|---|---|---|
| `participantes.ver` | ✔ | ✔ | ✔ | – |
| `participantes.gerenciar` | ✔ | ✔ | – | – |
| `participantes.excluir` | ✔ | ✔ | – | – |
| `participantes.revelar_pii` | ✔ | ✔ | – | – |
| `projetos.ver` | ✔ | ✔ | ✔ | ✔ |
| `projetos.gerenciar` | ✔ | ✔ | – | – |
| `projetos.excluir` | ✔ | ✔ | – | – |
| `participacoes.ver` | ✔ | ✔ | ✔ | ✔ |
| `participacoes.mover_etapa` | ✔ | ✔ | – | – |
| `participacoes.excluir` | ✔ | ✔ | – | – |
| `avaliacao.criar` | ✔ | ✔ | – | ✔ |
| `pagamento.ver` | ✔ | – | – | – |
| `usuarios.gerenciar` | ✔ | – | – | – |
| `usuarios.excluir` | ✔ | – | – | – |
| `permissoes.gerenciar` | ✔ | – | – | – |
| `auditoria.ver` | ✔ | – | – | – |
| `termos.ver` | ✔ | ✔ | ✔ | – |
| `termos.gerenciar` | ✔ | – | – | – |
| `avisos.triagem_pendente` | ✔ | ✔ | – | – |
| `avisos.projetos_vagas` | ✔ | ✔ | – | – |
| `avisos.termos_vencendo` | ✔ | – | – | – |

As permissões de **excluir** foram desenhadas separadas de `gerenciar` (que cobre
criar/editar) de propósito — dá para o Administrador tirar a permissão de excluir de um
nível sem tirar a de criar/editar, ajustando só o painel de permissões, sem mexer em código.
Default: Operador tem excluir de participantes/projetos/participações (já tinha CRUD
completo nessas áreas); excluir usuários fica só com Administrador (área mais sensível).

Esta matriz é **editável em produção** pelo Administrador em `/accounts/permissoes/` — a
tabela acima é só o estado inicial semeado pela migração `accounts.0002_seed_permissoes`.

## 6. Roadmap de fases

### Fase 1 — MVP (núcleo funcional) — **✅ concluída em 2026-08-09**

- Projeto Django configurado contra o Postgres remoto (schema `pessoas`).
- Login multiusuário real + logout.
- Painel de permissões (matriz nível × permissão, editável).
- Gestão de usuários (criar usuário, definir nível).
- Banco de Pessoas: lista (PII sempre mascarada), detalhe (revela PII com permissão +
  grava auditoria), criar/editar (com validação real de CPF).
- Projetos: lista em cards, detalhe com participantes vinculados, criar/editar.
- Participações: lista com filtros, kanban simples (mover etapa), avaliação (notas 1–5 +
  comentário).
- Registro de auditoria (modelo + gravação automática ao revelar PII) — sem tela dedicada
  ainda.
- Layout visual baseado no protótipo (sidebar escura, cards rosa/violeta, badges, tabelas).

### Fase 2 — **✅ concluída em 2026-08-09**

Ordem sugerida (negociável com o usuário a cada item):

1. **Tela de Auditoria LGPD** (`auditoria.ver`) — ✅ concluída em 2026-08-09. Lista em `/auditoria/` com filtros por usuário, titular, ação e intervalo de datas (máx. 500 registros por consulta — paginação real fica para a Fase 3 se o volume crescer). Link no menu lateral só aparece para quem tem `auditoria.ver` (hoje só Administrador).
2. **Termos e Contratos versionados** — ✅ concluída em 2026-08-09. Novo app `termos`
   (`Termo`, `VersaoTermo`, `LogAlteracao`) em `/termos/`. `Participante.consentimento_versao`
   deixou de ser texto livre e virou **FK real para `VersaoTermo`** — ao cadastrar/editar um
   participante com o consentimento marcado, o sistema grava automaticamente a versão vigente
   do "Termo de Consentimento LGPD" naquele momento (`pessoas/views.py::_versao_lgpd_vigente`).
   Publicar uma nova versão marca a anterior como "Substituída" e gera entrada no log — as
   versões em si nunca são editadas, só substituídas (imutabilidade). O contador de
   "aceites" de cada versão é calculado ao vivo pela contagem de participantes com aquela FK
   (`VersaoTermo.aceites`), não é um campo solto. Uma migração de dados semeou o primeiro
   documento (Termo de Consentimento LGPD, v{ano}.1) para o sistema não nascer vazio.
3. **Wizard de importação em massa** — ✅ concluída em 2026-08-09. 4 passos em `/participantes/wizard/…`
   (Banco de dados → Novos participantes → Dados → Revisão), iguais aos do protótipo. Passo
   "Dados" tem dois caminhos: **CSV** (upload + link para baixar um modelo com cabeçalho e
   linha de exemplo — `pessoas/wizard_csv.py` faz o parse, detecta separador `,`/`;`, tenta
   utf-8/latin-1, e mapeia valores comuns em português para os `choices` do modelo — ex.
   "Médio"→`MEDIO`, "Classes A/B"→`A_B`) e **manual** (formset Django de N linhas, com botão
   para carregar mais linhas). Os dois caminhos convergem para a mesma validação
   (`ParticipanteWizardForm`, que reaproveita `ParticipanteForm` e por consequência
   `pessoas/validators.py::validar_cpf`) e o mesmo estado de sessão
   (`request.session["wizard_importacao"]`). O consentimento LGPD é confirmado **linha a
   linha na Revisão** (não é herdado em lote) — só participantes com consentimento marcado
   e sem erro de validação são gravados; a Revisão também recusa CPF duplicado dentro do
   próprio lote e CPF já existente no banco (o `ModelForm` já rejeita duplicata contra o
   banco sozinho, por `cpf` ser `unique=True`; a checagem extra em
   `pessoas/views.py::_cpf_ja_cadastrado` cobre duplicata dentro do lote, comparando os
   CPFs sem pontuação via `Replace` do ORM). Se um projeto foi escolhido no passo 1, cada
   participante importado também vira uma `Participacao` em "Análise de Perfil". Gate de
   permissão único: `participantes.gerenciar` (Administrador/Operador).
4. **Página pública de cadastro** — ✅ concluída em 2026-08-09. Fluxo sem login:
   `/projetos/<id>/link/` (permissão `projetos.gerenciar`) gera um **link com token assinado
   e opaco** (`django.core.signing.dumps`/`loads`, `pessoas/links.py`) contendo
   `projeto_id`+`recrutador_id`, **válido por 48 horas** (decisão do usuário) — não fica
   nada gravado no banco, o próprio token carrega e autentica os dados, e expira sozinho
   (`SignatureExpired`) sem precisar de rotina de limpeza. `/participantes/cadastro/<token>/`
   é uma página **standalone** (não usa `base.html`/o shell autenticado — é sempre pública,
   mesmo que quem clique esteja logado) que reaproveita o CSS do card de login. Ao
   submeter, cria o `Participante` (`situacao=PENDENTE`, `origem_recrutador` = o usuário do
   token) e a `Participacao` na etapa "Análise de Perfil" do projeto. Também entrou a
   **triagem** (aprovar/descartar) no detalhe do participante — 2 ações (não as 3 do
   protótipo; ver nota abaixo), visíveis só quando `situacao=PENDENTE` e o usuário tem
   `participantes.gerenciar`; descartar também remove a `Participacao` ainda em "Análise de
   Perfil". Simplificação assumida: o protótipo tinha 3 botões de triagem ("aprovar e
   associar ao projeto de entrada" / "aprovar só para projetos futuros" / "descartar"); como
   aqui a associação ao projeto já acontece no próprio cadastro (não fica numa espécie de
   "limbo" pré-pipeline), a distinção dos dois primeiros botões deixou de fazer sentido e
   virou só "Aprovar".
5. **Dashboards analíticos** — ✅ concluída em 2026-08-09, com **Chart.js 4.4.4** — inicialmente
   via CDN jsdelivr com SRI, depois **vendorizado** em `static/js/vendor/chart.umd.js` e
   servido pelo próprio Django (sem dependência de rede externa) — ver correção de
   2026-08-09 no log de progresso. Virou a própria
   tela inicial pós-login (`core:home` — é exatamente o que o protótipo fazia: o dashboard
   "Visão participantes" era a home). 8 gráficos, todos vindos de **dados reais do banco**
   (não da massa sintética de 1.000 linhas do protótipo, que não existe aqui): participantes
   por UF (barra horizontal, top 10), principais cidades (rosca, top 5), situação dos
   participantes (rosca, com as mesmas cores dos badges: âmbar/verde/vermelho), gênero
   (rosca), classe social/faixa de renda (barra vertical), escolaridade (barra vertical),
   faixa etária calculada a partir da data de nascimento (barra vertical), e participações
   por etapa do funil (barra horizontal, com as mesmas 5 cores do protótipo — azul, violeta,
   âmbar, rosa, verde — que o `ETAPA_COR` original usava). Estilo "profissional" pedido pelo
   usuário: paleta idêntica à do protótipo, barras com gradiente (via `createLinearGradient`
   no canvas), cantos arredondados, tooltip escuro, sem grid nos eixos de categoria, legenda
   com `pointStyle: circle`. Os dados são calculados no servidor (`core/views.py`, agregações
   com `Count` do ORM) e passados ao JS via `{{ dado|json_script:"id" }}` — sem endpoint de
   API novo, sem dado sensível exposto além do que a permissão do usuário já libera (cada
   bloco de gráfico só é montado no contexto se o usuário tiver `participantes.ver` e/ou
   `participacoes.ver`, então um Freelancer nunca recebe os dados de participantes, nem
   mascarados).

   **Atualização de 2026-08-09 (correções pós-Fase 2)**: a "Visão por segmento" original
   ficou de fora nesta entrega porque "segmento" não existia no modelo de dados real — só
   nos dados sintéticos do protótipo. O usuário pediu para trazê-la de volta, então:
   `Projeto` ganhou um campo `segmento` (Saúde/Cosméticos/Alimentação/Banco/Tecnologia/Outro)
   e uma nova tela `core:dashboard_segmento` (`/segmento/`) mostra abas por segmento + um
   gráfico comparativo entre todos + (ao selecionar um) gráficos de cidade/gênero/classe
   social/faixa etária **só dos participantes que já passaram por algum projeto daquele
   segmento** (`Participante.objects.filter(participacoes__projeto__segmento=X).distinct()`).
   O diagrama de Venn de sobreposição entre segmentos ficou fora do escopo nesta entrega —
   Chart.js não tem isso nativamente. **Atualização de 2026-08-10: implementado depois**, ver
   entrada de log correspondente — não usa Chart.js, é SVG puro, igual ao protótipo.

### Fase 4 — Variáveis dinâmicas, formulários e projetos (em andamento)

Usuário trouxe um plano de ação pronto (genérico, escrito sem conhecimento do projeto real —
citava "ORM que você usa, ex: Entity Framework Core" como placeholder) pra permitir cadastrar
**variáveis** (campos configuráveis com tipo de resposta), combiná-las em **formulários**,
associar formulários a **projetos**, e gravar **respostas** estruturadas por participação,
preparando o terreno pra um scoring/matching futuro. Antes de implementar, adaptei o plano ao
sistema real (evitando duplicar `Participante`/`Projeto`/`Participacao`, que já existem) e
levantei 4 decisões de arquitetura com o usuário — respostas em
`docs/SDD.md` §7 "2026-08-10 (variáveis dinâmicas)".

Roadmap completo do plano original (numeração do próprio plano do usuário):
1. ✅ **Banco de dados** — concluída em 2026-08-10.
2. ✅ **CRUD de Variáveis** — concluída em 2026-08-10.
3. ⏳ CRUD de Formulários (associar variáveis escolhidas, com ordem; retornar o "schema"
   completo pronto pra renderizar).
4. ⏳ CRUD de Projetos × Formulários (a ligação N:N já existe no banco desde a Etapa 1 —
   falta só a tela).
5. ⏳ Respostas — endpoint/tela pra submeter e listar respostas de uma participação a um
   formulário.
6. ✅ Tela de cadastro de variáveis — concluída em 2026-08-10 (junto com a Etapa 2).
7. ⏳ Montador de formulário (seleção + reordenação das variáveis + preview).
8. ⏳ Tela de criação de projeto × formulário(s).
9. ⏳ Preenchimento do formulário (renderização dinâmica por `tipo_resposta`).
10. ⏳ View "achatada" (`pessoas` + `respostas_variaveis`) pra alimentar scoring futuro.

### Fase 3 — polimento (backlog, sem data)

- Testes automatizados (pytest-django) cobrindo o sistema de permissões e a validação de CPF.
- Paginação nas listas (participantes/projetos/participações) quando o volume crescer.
- Pool de conexões real (PgBouncer) se a concorrência exigir.
- Exportações (CSV/Excel) das listas.
- Notificações/alertas no sidebar (ex.: vagas faltando, consentimentos a renovar).

## 7. Log de progresso

- **2026-08-09** — Fase 1 (MVP) entregue: projeto Django criado, conectado ao Postgres
  remoto informado pelo usuário (schema `pessoas`, todas as tabelas confirmadas), sistema de
  login multiusuário com 4 níveis, painel de permissões editável, CRUD de Participantes/
  Projetos/Participações, kanban básico, avaliação, mascaramento de PII com revelação
  auditada. Testado ponta a ponta via requisições HTTP reais (login por nível, bloqueios de
  permissão, criação de projeto/participante/participação/avaliação, revelação de PII com
  gravação em auditoria). Usuários de demonstração e superusuário criados. Próximo passo:
  usuário validar o MVP rodando e decidir a ordem da Fase 2.
- **2026-08-09** — Fase 2, item 1 entregue: tela de **Auditoria LGPD** (`/auditoria/`) com
  filtros por usuário/titular/ação/data, restrita a quem tem `auditoria.ver` (só
  Administrador na matriz atual). Testado via requisição HTTP real: admin vê e filtra os
  registros (inclusive o gerado pela revelação de PII na Fase 1); operador recebe 403 como
  esperado.
- **2026-08-09** — Fase 2, item 2 entregue: **Termos e Contratos versionados** (`/termos/`).
  `Participante.consentimento_versao` virou FK para `VersaoTermo` (antes era texto livre sem
  uso real) — uma migração zerou o único valor existente (estava em branco) antes de trocar
  o tipo da coluna, e outra semeou o primeiro documento LGPD para o sistema não começar
  vazio. Testado: lista/detalhe, permissões (`termos.ver` para Administrador/Operador/
  Visualizador, `termos.gerenciar` só Administrador, Freelancer sem acesso), publicar nova
  versão (marca a anterior como Substituída) e o vínculo automático ao cadastrar um
  participante com consentimento marcado (a versão vigente naquele momento fica gravada e o
  contador de aceites sobe). Apareceu um bug real de template durante o teste —
  `{{ a|default:b.c }}` lança `VariableDoesNotExist` quando `b` é `None` (aconteceu com o
  autor/log da versão semeada, sem usuário associado) — corrigido com um filtro
  `nome_usuario` em `accounts/templatetags/perms_extras.py`, também aplicado em
  `participacoes/lista.html` e `projetos/detalhe.html`, que tinham o mesmo padrão de risco
  com `responsavel` (FK opcional).
- **2026-08-09** — Fase 2, item 3 entregue: **wizard de importação em massa** de
  participantes (`/participantes/wizard/…`), com os dois caminhos (CSV e manual) e a etapa
  de revisão com consentimento por linha. Testado ponta a ponta com um CSV de 6 linhas
  cobrindo os casos reais: 2 válidas simples, 2 com o mesmo CPF dentro do lote (só a
  primeira é criada, a segunda é pulada), 1 com CPF já cadastrado no banco (recusada já na
  validação, pelo `unique=True` do modelo) e 1 com CPF inválido (dígito verificador) —
  resultado: 3 criadas, 3 puladas, exatamente como esperado. Testado também o caminho com
  projeto escolhido (participante importado aparece no projeto e no kanban em "Análise de
  Perfil"), o modo manual (uma linha preenchida + quatro em branco) e os bloqueios de
  permissão (Freelancer e Visualizador recebem 403; só quem tem `participantes.gerenciar`
  acessa). Um bug real apareceu no teste do modo manual: o campo `situacao` do formulário
  tinha um valor padrão sempre presente ("Pendente"), o que impedia o Django de reconhecer
  uma linha do formset como "em branco" (toda linha parecia parcialmente preenchida, então
  linhas vazias geravam erro de campo obrigatório em vez de serem ignoradas) — corrigido
  removendo `situacao` do `ParticipanteWizardForm` (o valor é sempre definido como Pendente
  no servidor, tanto no caminho CSV quanto no manual, então o formulário nem precisa dele).
- **2026-08-09** — Fase 2, item 4 entregue: **página pública de cadastro** com link de
  recrutador (token assinado, validade de 48h) e **triagem** de participantes pendentes.
  Testado ponta a ponta: gerar link como Operador, acessar `/participantes/cadastro/<token>/`
  **sem nenhum cookie de sessão** (simulando um visitante externo real) e submeter um
  cadastro válido — o participante criado ficou com `origem_recrutador` correto, apareceu no
  projeto e no kanban em "Análise de Perfil". Testado token adulterado (`BadSignature`) →
  página amigável com HTTP 410, não um erro 500. Testado aprovar (muda para "Aprovado") e
  descartar (muda para "Descartado" **e** remove a `Participacao` de "Análise de Perfil" —
  confirmado no banco, não só na tela) em dois participantes diferentes. Freelancer e
  Visualizador recebem 403 tanto para gerar link quanto para aprovar/descartar, como
  esperado (só quem tem `projetos.gerenciar`/`participantes.gerenciar`). Ajuste cosmético
  encontrado no caminho: o badge de "Situação" no detalhe do participante estava sempre
  roxo, sem variar por status como na lista — corrigido para usar verde/vermelho/âmbar
  igual à lista.

- **2026-08-09** — Fase 2, item 5 entregue: **dashboards analíticos com Chart.js**, virando
  a nova tela inicial pós-login. 8 gráficos com dados reais (UF, cidades, situação, gênero,
  faixa de renda, escolaridade, faixa etária, funil do pipeline), paleta e cores fiéis ao
  protótipo (inclusive as cores por etapa do funil). Testado: dados agregados batem com o
  que existe no banco (conferido com `grep` no HTML renderizado), hash SRI do Chart.js
  verificado batendo com o arquivo real baixado do CDN (não só copiado de algum lugar), e a
  lógica do script testada rodando de verdade em Node com um DOM/Chart.js simulados (os 8
  gráficos são instanciados sem exceção, incluindo os callbacks de gradiente). Também
  testado por nível: Freelancer só vê o gráfico de pipeline (não tem `participantes.ver`,
  então nenhum dado de participante — nem os gráficos, nem o KPI — chega a ser calculado ou
  enviado pro template); Visualizador vê o dashboard completo. "Visão por segmento" (com
  Venn) ficou de fora — ver a justificativa na seção de roadmap acima.

Com isso, **todos os 5 itens do roadmap da Fase 2 estão concluídos**. O sistema cobre hoje o
fluxo operacional completo de captação: login multiusuário por nível, painel de permissões
editável, banco de pessoas, projetos, pipeline/kanban, termos e contratos versionados,
auditoria LGPD, importação em massa (CSV/manual), captação pública com link de recrutador e
triagem, e dashboards analíticos. O que ficou de fora está documentado como backlog de Fase
3 (testes automatizados, paginação, pool de conexões real, exportações, notificações).

- **2026-08-09** — Rodada de correções pós-Fase 2, depois que o usuário comparou a aplicação
  lado a lado com o protótipo e apontou 5 lacunas reais. O que mudou:
  1. **Revelação de PII virou por campo**, na lista **e** no detalhe (antes só existia no
     detalhe, e revelava CPF/telefone/e-mail juntos via query string `?revelar=1`). Agora
     cada campo tem seu próprio ícone 👁, com um endpoint dedicado
     (`pessoas:revelar_campo`, POST, whitelist de campos `cpf`/`telefone`/`email`, 404 para
     qualquer outro) que audita cada revelação individualmente. JS novo e pequeno
     (`static/js/pii.js`, ~40 linhas) faz o fetch com o cookie CSRF (por isso `lista` e
     `detalhe` agora usam `@ensure_csrf_cookie`) e evita rebater no servidor num
     esconde/mostra local (só revela de verdade — e audita — na primeira vez).
  2. **Menu "Dashboards" com submenu** ("Visão participantes" / "Visão por segmento") — não
     existia nenhum link de sidebar para o dashboard antes, só dava pra chegar lá clicando
     na logo. Sidebar reorganizada em grupos recolhíveis com `<details>`/`<summary>` (zero
     JS) — "Dashboards" e "Banco de Pessoas" (que passou a agrupar Pessoas/Projetos/
     Participações/Pipeline/Novos participantes, igual ao protótipo).
  3. **Tela "Visão por segmento" nova** (`/segmento/`) — ver detalhes na seção 6 do roadmap
     acima. Exigiu adicionar o campo `segmento` em `Projeto`.
  4. **Termos com múltiplos tipos**: investiguei e não havia bug — `TermoForm` já permitia
     escolher entre Consentimento/Contrato/Confidencialidade/Cessão de Imagem e Voz, e
     testei criando um "Contrato de Participação Remunerada" com sucesso. O que corrigi foi
     um bug latente adjacente: `_versao_lgpd_vigente()` fazia `.filter(tipo=CONSENTIMENTO).first()`
     sem `order_by` — se alguém cadastrasse um segundo documento do tipo Consentimento por
     engano, qual dos dois contaria como "o" termo LGPD oficial ficaria indefinido
     (dependente da ordem física no banco). Agora é `order_by("id")` — sempre o mais antigo.
  5. **Botões de Editar/Excluir nas páginas de detalhe**, com permissões novas e
     independentes: `participantes.excluir`, `projetos.excluir`, `participacoes.excluir`,
     `usuarios.excluir` — todas configuráveis no painel de permissões (que já é genérico e
     absorveu as novas linhas sozinho, sem mudança de template). Exclusão sempre passa por
     uma **página de confirmação** (GET mostra o aviso — inclusive quantas participações
     serão arrastadas junto — POST executa), não só um `confirm()` do navegador. Usuários
     também ganharam tela de edição (nível, status, telefone) que não existia — só dava para
     criar, nunca editar. Auto-exclusão bloqueada (um usuário não pode se excluir).
  6. **Lista de participantes reformulada** para bater com as colunas do protótipo: avatar
     com iniciais (cores cíclicas g0–g4), CPF e Contato (telefone/e-mail) com sigilo e
     revelação por campo, Idade (propriedade nova no model `Participante.idade`, calculada
     a partir da data de nascimento), Classe social, Última participação, Consentimento
     (badge com a versão aceita).
  Refatoração colateral: extraí a lógica repetida de inicialização dos gráficos Chart.js
  (que já existia em `core/home.html`) para `static/js/charts.js` (namespace `QV`), reusado
  agora também pela tela de segmento — evita duplicar ~140 linhas de JS por dashboard novo.
  Tudo testado ponta a ponta via requisições HTTP reais: criar termo de outro tipo, revelar
  campo (com verificação da entrada correspondente na auditoria), excluir participante/
  projeto/usuário (confirmação + execução + confirmação de que sumiu), bloqueio de
  Visualizador em todas as exclusões (403) e ausência dos botões na tela, painel de
  permissões com as 18 permissões × 4 níveis (72 checkboxes), e os dois dashboards
  (incluindo os scripts rodando de verdade em Node com Chart.js simulado).
- **2026-08-09** — Segunda rodada de correções, depois que o usuário testou no navegador de
  verdade e reportou 3 problemas: cards de Projetos ainda muito simples (comparando com o
  protótipo lado a lado), dashboards sem nenhum gráfico aparecendo, e os "Alertas" da
  sidebar do protótipo (demo, hardcoded) não existiam na aplicação.
  1. **Cards de Projetos** — refeitos para bater com o protótipo: aba recortada no topo
     (`.folder::before` com `skewX`), ícone, badge do cliente, caixa "Perfil: …" (nova
     property `Projeto.perfil_resumo`, que compõe um resumo legível a partir de
     `perfil_idade_min/max`, `perfil_genero`, `perfil_regiao`, `perfil_renda`,
     `perfil_criterios_livres`), barra de ocupação com fração, e rodapé com
     R$/perfil + botão "Acessar ›".
  2. **Dashboards sem gráfico — causa raiz: dependência de CDN externo.** O Chart.js estava
     sendo carregado de `cdn.jsdelivr.net` com SRI; isso funciona em teste automatizado (que
     não depende de internet de verdade), mas falha silenciosamente em qualquer navegador
     sem acesso a esse domínio específico no momento — rede corporativa, proxy, ad-blocker,
     ou simplesmente offline. **Corrigido vendorizando o Chart.js dentro do próprio projeto**
     (`static/js/vendor/chart.umd.js` — o mesmo arquivo já verificado por SHA-256 na entrega
     anterior, agora servido pelo próprio Django via `{% static %}`, sem depender de rede
     externa nenhuma). Também adicionei uma rede de segurança: se por algum motivo o Chart.js
     ainda assim não carregar, cada painel de gráfico mostra um aviso visível em vez de ficar
     em branco silenciosamente (`QV.configurarPadroes()` em `static/js/charts.js`). Testado
     de duas formas: servindo o arquivo estático local (200, mesmo tamanho em bytes do
     original) e carregando o `chart.umd.js` de verdade — não um mock — em Node, confirmando
     que ele define `Chart` global corretamente (`Chart.version === "4.4.4"`).
  3. **Alertas da sidebar** — o protótipo tinha 2 cards de alerta fixos/decorativos (dados
     inventados, nunca mudavam). Implementei um equivalente com **dados reais**, via
     `core/context_processors.py::alertas` (roda em toda página autenticada, cada bloco
     condicionado à permissão do usuário): triagem pendente (participantes com
     `situacao=PENDENTE`), projetos com vagas em aberto e campo começando nos próximos 14
     dias, e termos vigentes vencendo nos próximos 30 dias. Testado com dados reais no banco:
     "Triagem pendente — 5 participante(s)…" e "Teste Bancos Digitais — Faltam 8 vaga(s) e o
     campo começa em 6 dia(s)." apareceram corretamente na sidebar.
- **2026-08-09** — Terceira rodada de correções. O usuário mandou print de novo mostrando
  texto corrompido em vários lugares, o card de projeto ainda esticando 100% da tela com só
  1 projeto, dropdowns em inglês, e confirmando que **os gráficos continuavam não
  aparecendo mesmo depois da vendorização do Chart.js**. Essa última exigiu instalar
  Playwright (`npx playwright install chromium`) e abrir a aplicação de verdade num
  Chromium headless — nenhum teste em Node com mocks pega esse tipo de bug, só um
  navegador real. Achados e correções:
  1. **Texto corrompido** — não era bug da aplicação, era **dado de teste meu**. Vários
     registros que criei via `curl --data-urlencode` no Git Bash (nome do contrato, texto
     de uma versão de termo, um campo de perfil de projeto) ficaram com os acentos
     transformados em `�` porque o Git Bash nesta máquina não repassa corretamente
     caracteres acentuados como argumento de linha de comando para um `.exe` nativo do
     Windows como o curl. Corrigido reescrevendo os 3 registros afetados com um script
     Python (arquivo `.py`, não argumento de shell — arquivo `.py` é sempre lido como UTF-8,
     então não tem esse problema). Confirmei que nenhum outro registro do banco tem
     caractere de substituição (`�`). **Isso não afeta dados reais**: formulário HTML
     enviado por um navegador de verdade sempre manda UTF-8 corretamente — o problema só
     existia nos meus dados de teste injetados por linha de comando. Lição anotada: para
     qualquer teste futuro com acento, usar um script Python/arquivo, nunca argumento de
     `curl` direto no Git Bash.
  2. **Card de projeto esticando 100%** — `.folders` usava
     `grid-template-columns:repeat(auto-fit,minmax(220px,1fr))`; o `1fr` faz o único card
     ocupar toda a largura sobrando quando há poucos itens. Trocado para
     `repeat(auto-fill,minmax(220px,260px))` — cada card tem no máximo 260px, sobra vira
     espaço vazio em vez de esticar o card.
  3. **Dropdowns em inglês** — não eram um "default do navegador", eram o
     `("", "---------")` que o Django gera automaticamente pra campo de modelo com
     `choices` — como o texto era só traços, alguns navegadores/situações mostram um
     texto de sistema no lugar. Criado `core/form_utils.py::personalizar_opcoes_vazias()`,
     chamado no `__init__` de todo formulário com `<select>` (Participante, Projeto, Termo,
     Usuário), trocando a opção em branco por "Selecione…". Também faltavam `labels`
     explícitos em português nos `Meta` dos ModelForms — os campos apareciam com o nome
     bruto do atributo Python capitalizado (`Genero`, `Cpf`, `Uf`, `Data nascimento`, sem
     acento). Adicionados labels corretos (`Gênero`, `CPF`, `UF`, `Data de nascimento`,
     `Profissão`, `Faixa de renda` etc.) em `pessoas`, `projetos`, `termos`, `accounts` e
     `participacoes`.
  4. **Gráficos realmente não apareciam — causa raiz encontrada com Playwright**:
     `console --errors` mostrou `ReferenceError: QV is not defined`. O motivo é uma
     particularidade pouco conhecida do HTML: **o atributo `defer` não tem nenhum efeito em
     `<script>` inline (sem `src`)** — só funciona em scripts externos. Os dois scripts
     externos (`chart.umd.js` e `charts.js`, que define o objeto `QV`) tinham `defer` e
     corretamente esperavam o documento terminar de parsear; mas o terceiro `<script defer>`
     inline, por não ter `src`, **ignorava o `defer` e executava imediatamente**, no meio do
     parsing — antes de `charts.js` sequer ter rodado. Por isso `QV` não existia ainda.
     Corrigido trocando o `defer` (inútil ali) por um listener explícito de
     `DOMContentLoaded` nos dois templates de dashboard (`core/home.html` e
     `core/dashboard_segmento.html`) — isso sim garante que os scripts externos deferred já
     rodaram antes. **Confirmado com o navegador real**: antes da correção, os `<canvas>`
     ficavam com o tamanho padrão do HTML (300×150, prova de que o Chart.js nunca desenhou
     nada neles); depois da correção, cada canvas aparece redimensionado para o tamanho real
     do painel (ex.: 459×300) e os gráficos aparecem nos screenshots exatamente como
     desenhados — sem nenhum erro no console.
  **Lição de processo**: qualquer alteração que dependa de JavaScript rodando no navegador
  (não só HTML/CSS estático) precisa ser verificada com um navegador de verdade antes de
  reportar como concluída — testar a lógica isolada em Node (como fiz nas rodadas
  anteriores) prova que o *código* está certo, mas não prova que ele *executa* na ordem
  certa dentro de uma página HTML real. Nas próximas fases, qualquer entrega com JS deve
  passar por Playwright (`npx playwright install chromium` + um script de navegação) antes
  de ser dada como pronta.
- **2026-08-09** — Usuário perguntou como fechar os avisos da sidebar e pediu uma página de
  perfil próprio (trocar senha + escolher quais avisos receber) com o controle de quem
  recebe cada tipo de aviso indo para o painel de permissões. Implementado com **duas
  camadas de controle**, que é o desenho que faz sentido pro pedido:
  1. **Nível (papel) — painel de permissões**: 3 permissões novas, grupo "Avisos"
     (`avisos.triagem_pendente`, `avisos.projetos_vagas`, `avisos.termos_vencendo`),
     independentes das permissões funcionais que já existiam (ex.: um nível pode gerenciar
     participantes sem necessariamente *receber aviso* de triagem pendente, e vice-versa —
     antes isso estava amarrado a `participantes.gerenciar`/`projetos.ver`/`termos.gerenciar`,
     agora é uma escolha própria do Administrador no painel).
  2. **Usuário — "Meu perfil"** (`/accounts/perfil/`, novo link clicando no avatar/nome no
     rodapé da sidebar): dentro do que o nível permite receber, cada usuário liga/desliga
     individualmente (`PreferenciaAvisos`, um registro por usuário, `default=True` — começa
     recebendo tudo que o nível permite, cada um desliga o que não quiser). Essa mesma
     página também deixa editar nome/sobrenome/e-mail/telefone e tem um botão para
     **trocar a própria senha** (`accounts:trocar_senha`, reaproveitando o
     `PasswordChangeForm` do próprio Django — pede a senha atual, valida a nova contra
     `AUTH_PASSWORD_VALIDATORS`, não desloga o usuário — só troquei os labels pro
     português; o texto de ajuda dos validadores de senha já vinha em português sozinho,
     graças ao `LANGUAGE_CODE='pt-br'` já configurado desde a Fase 1).
  3. **Fechar (dispensar) um aviso** — cada aviso tem um botão × que grava um
     `AvisoDispensado (usuario, chave, conteudo)` e o remove da lista. A "chave" identifica o
     tipo (`triagem_pendente`, `termos_vencendo`) ou o tipo+id pra avisos por projeto
     (`projetos_vagas:3`); o "conteudo" é o texto exato do aviso no momento da dispensa. Como
     a comparação na hora de montar a lista é por (chave, conteudo) **exato**, um aviso
     dispensado só fica escondido enquanto a situação não muda — se o texto mudar (ex.: "5
     participantes" virar "6 participantes", ou vagas de um projeto mudarem), ele volta a
     aparecer sozinho, sem precisar de rotina de expiração nem de "snooze por X dias".
  Testado com Playwright (navegador real, não curl — o formulário de "Meu perfil" e o botão
  de dispensar envolvem texto acentuado, e o Git Bash desta máquina corrompe acento em
  argumento de `curl`, como já registrado antes; um teste em bash bateria de novo nesse
  problema e não provaria nada sobre a aplicação): clique no × removeu o aviso da tela;
  desligar as 3 categorias em "Meu perfil" e salvar fez a seção "Alertas" inteira sumir da
  sidebar (nenhum badge, nenhum card); Freelancer (sem nenhuma permissão `avisos.*` por
  padrão) não vê a seção de Alertas mas consegue acessar `/accounts/perfil/` normalmente
  (toda conta pode editar o próprio perfil, isso não depende de permissão nenhuma); a página
  de trocar senha mostrou os labels e os avisos dos validadores 100% em português.
- **2026-08-09** — Preparação para deploy no Railway. O usuário já tinha o serviço criado e
  ligado ao GitHub, mas o build falhou porque nenhum código Django tinha sido commitado
  ainda (só o "Initial commit" original, sem o app). Adicionados `Procfile`,
  `.python-version`, `gunicorn`+`whitenoise` no `requirements.txt`, e configuração de
  produção em `settings.py` (detecção automática de ambiente Railway, `DEBUG`/
  `ALLOWED_HOSTS` dinâmicos, cabeçalho de proxy HTTPS, WhiteNoise pros estáticos) — detalhes
  completos na seção "Deploy em produção (Railway)" acima. Testei `collectstatic` localmente
  antes de subir e achei um bug real: o `chart.umd.js` vendorizado referenciava um sourcemap
  que não existe, o que quebrava o WhiteNoise (e teria quebrado o deploy inteiro,
  silenciosamente, já que `collectstatic` roda dentro do `Procfile`) — corrigido removendo a
  referência. Perguntei ao usuário se quereria mover a senha do banco/`SECRET_KEY` pra
  variável de ambiente agora que o repositório vai ficar de fato acessível no GitHub; ele
  optou por manter fixo no código, como já era desde a Fase 1 — respeitei a decisão e só
  registrei o risco de novo. Commitei tudo (141 arquivos, primeiro commit real da aplicação)
  e enviei pro `origin/main`, que dispara o redeploy automático no Railway via a integração
  GitHub já existente. Falta o usuário conferir se o build passou e gerar o domínio público
  (Settings → Networking → Generate Domain) — não tenho acesso à conta do Railway para fazer
  isso por ele.
- **2026-08-10** — Usuário comparou "Visão participantes" lado a lado com o protótipo de
  novo e apontou que ainda estava muito diferente: sem o mapa de estados, sem números nos
  gráficos, sem destaque pras 5 capitais, sem diagrama de Venn. Perguntou se isso era
  limitação do Chart.js. **Resposta: em parte.** Reli o JS do próprio protótipo
  (`renderDashPart`, `svgVenn2`/`svgVenn3`) pra confirmar: **o protótipo não usa Chart.js
  nem nenhuma outra lib de gráfico nessa tela** — é tudo HTML/CSS/SVG artesanal (grade de UF
  em `<div>`s coloridos por `rgba()`, rosca via `conic-gradient` do CSS com texto no centro
  via `content:attr(data-center)`, barra de gênero é uma `<div>` só com pedaços coloridos,
  barras verticais são só `<b style="height:X%">` com o número ao lado em texto puro, e o
  Venn é SVG com círculos e texto posicionados na mão). Ou seja: o Chart.js genuinamente não
  faz Venn e não desenha texto centralizado numa rosca por padrão, mas o resto (números nas
  barras, layout do mapa) era só eu não ter replicado o componente certo — não era uma
  limitação real da lib. Corrigido trocando esses componentes por HTML/CSS/SVG puro,
  reproduzindo o protótipo quase literalmente (mesmas posições de UF no cartograma, mesmas
  cores, mesma fórmula de intensidade), com os dados vindos do banco real:
  - `core/dashviz.py` (novo): `mapa_estados()` (cartograma, todas as 27 UFs), `construir_donut()`
    (rosca com `conic-gradient` + legenda com contagem e %, reusada em "5 principais capitais"
    E "Situação dos participantes"), `construir_stackbar()` (barra de gênero), `construir_barras_verticais()`
    (classe social / faixa etária, com o número já embutido), e `montar_venn()` +
    `svg_venn2`/`svg_venn3` (tradução literal das funções JS do protótipo pra Python, gerando
    SVG server-side com `mark_safe`, contagens reais via `Participacao.objects.filter(projeto__segmento__in=...)`).
  - "5 principais capitais" ficou com a mesma lista fixa do protótipo (Rio de Janeiro, São
    Paulo, Brasília, Fortaleza, Salvador) — é uma escolha editorial, não estatística, então
    não faz sentido calcular dinamicamente.
  - O Venn agora mora na própria "Visão participantes" (igual ao protótipo — no protótipo não
    é a tela "Visão por segmento" que tem o Venn, é a "Visão participantes" mesmo), com um
    seletor de 2 a 3 segmentos via pills (`?segs=BANCO,SAUDE`, recarrega a página — sem JS).
  - **Bug real encontrado no meio do processo**: `Projeto.Segmento` tem uma opção "Outro"
    (catch-all) que não existe no protótipo (lá só tem os 5 segmentos nomeados) — o código
    tentava buscar a cor dela em `COR_SEGMENTO` e caía num `KeyError('OUTRO')`, 500 em toda a
    home. Corrigido excluindo "Outro" da lista de segmentos válidos pro Venn/seletor.
  - Testado com Playwright: screenshots batendo visualmente com o protótipo (cartograma,
    rosca com texto no centro, barra de gênero com legenda, barras com número em cima) e o
    Venn testado de verdade com dados reais de sobreposição (criei e depois apaguei 2
    projetos de teste com segmentos diferentes e participações cruzadas só pra gerar overlap
    de 2 e de 3 vias e conferir visualmente — os números bateram exatamente com o esperado
    em ambos os casos).
  - Simplificação assumida: os cliques em tile/legenda/barra do protótipo filtravam a base
    (era um recorte interativo tipo "clique no RJ pra ver só quem é do RJ"). Isso **não** foi
    replicado — os componentes aqui são só visualização, sem interação de filtro. Se fizer
    falta, é um próximo passo natural (cada elemento já tem os dados pra virar um link de
    filtro por querystring, no mesmo estilo do seletor de segmentos do Venn).
  - **Nada disso foi commitado ainda** — usuário pediu pra ver antes. `git status` mostra as
    mudanças pendentes: `core/dashviz.py` (novo), `core/views.py`, `templates/core/home.html`,
    `static/css/base.css`.
- **2026-08-10 (mesma sessão, correções seguintes)** — Usuário testou o resultado acima e
  reportou dois problemas pontuais por screenshot: (1) o gráfico de "Pipeline de captação"
  (barra horizontal via Chart.js, herdado da versão anterior) estava "ruim e feio, muito
  grande" pra só 5 categorias com números pequenos; (2) no mapa de estados, o texto ficava
  branco sobre fundo ainda claro em vários estados, ilegível.
  - **Mapa — causa raiz real**: a regra que decide se o texto do tile fica claro ou escuro
    era `intensidade > 0.5`, mas a cor de fundo é `rgba(242,41,91,intensidade)` sobre fundo
    branco — nessa mistura, em `intensidade=0.5` o tile ainda fica com RGB≈(248,148,173), que
    é visualmente bem claro (o rosa só fica escuro o suficiente pra pedir texto branco lá
    perto de `intensidade≈0.78`). Troquei o corte fixo por um cálculo real de luminância
    perceptual (`0.299R+0.587G+0.114B`, mesma fórmula usada em acessibilidade) em
    `core/dashviz.py::_fundo_e_escuro()`, que decide "texto escuro" quando a luminância
    calculada é `< 140`. Verifiquei os dois extremos rodando a função pra intensidade de
    0.0 a 1.0 (crossover real fica em ~0.8) e depois visualmente: criei 9 participantes de
    teste em SP (script `C:/tmp/seed_map_test.py`, apagados logo depois via
    `Participante.objects.filter(nome__startswith="Teste Mapa ").delete()`) pra forçar um
    tile de intensidade alta e conferi por screenshot do Playwright que SP ficou com fundo
    escuro e texto branco legível, enquanto os demais estados (intensidade baixa) mantiveram
    texto escuro sobre fundo claro.
  - **Pipeline — não era limitação do Chart.js, era o componente errado de novo**: o próprio
    protótipo já tem um componente pronto pra "poucas categorias com contagem", usado lá na
    tela "Visão por segmento" pra top-estados: `.hbar-row` (barra horizontal simples em CSS,
    sem lib nenhuma, com rótulo à esquerda, barra ao centro, contagem+% à direita). Troquei o
    canvas Chart.js do pipeline por esse mesmo componente: `construir_barras_horizontais()`
    (novo, em `core/dashviz.py`) calcula largura% proporcional ao máximo e % do total por
    etapa; `.hbar-row`/`.hbar` (novo, em `static/css/base.css`) estilizam; `core/views.py`
    monta `contexto["barras_pipeline"]` a partir de `Participacao.Etapa.choices` com as
    cores de `COR_ETAPA` (novo dict, uma cor por etapa do funil); `templates/core/home.html`
    itera `barras_pipeline.barras`. Como essa era a última coisa em `home.html` que ainda
    dependia de Chart.js, removi o `{% block scripts %}` inteiro (carregamento de
    `chart.umd.js`/`charts.js` e o script de inicialização) — a página não usa mais Chart.js
    em nenhum ponto. `dashboard_segmento.html` continua usando Chart.js normalmente (fora do
    escopo desse pedido).
  - Testado visualmente com Playwright (screenshot completo da home + recorte do mapa antes
    e depois de forçar intensidade alta em SP) — ambas as correções confirmadas.
  - **Segue sem commitar** — mesmo pedido do usuário de revisar antes. `git status` agora
    também inclui `core/views.py`, `templates/core/home.html` e `static/css/base.css` com as
    mudanças desta rodada em cima das da rodada anterior.
- **2026-08-10 (mesma sessão, reescrita pra interatividade real)** — Usuário testou de novo
  e foi direto ao ponto real do problema, que as duas rodadas anteriores não tinham resolvido:
  "o gráfico por estado não consegue selecionar filtrar os outros dados, o diagrama de venn
  ficou ruim demais a usabilidade... quero igual [ao protótipo]". Reli `renderDashPart` e
  `renderVenn` do protótipo com atenção no que eu tinha deixado de fora da primeira vez: lá,
  **cada elemento clicável (tile do mapa, legenda de gênero/capital, barra de classe/faixa)
  aplica um filtro (`filtros={uf,gen,cls,fx,cid}`) que refiltra e redesenha o dashboard
  inteiro na hora, no cliente**, com uma barra de chips mostrando os filtros ativos e um
  botão "limpar tudo" — e o Venn recalcula a sobreposição em cima desse mesmo recorte
  filtrado. A versão que eu tinha construído nas duas rodadas anteriores era só HTML estático
  gerado no servidor (nada clicável) e o Venn recarregava a página inteira via querystring
  a cada troca de segmento — daí a reclamação de usabilidade ruim, era literal: o Venn do
  jeito que estava dava um reload cheio a cada clique.
  - **Mudança de arquitetura pra essa seção**: em vez de montar HTML no servidor a cada
    request, `core/views.py::home()` agora serializa uma vez por request os campos que o
    dashboard usa pra filtrar — `core/dashviz.py::dados_participantes_dashboard()` devolve
    uma lista de `{uf, gen, cls, fx, cid, segs}` por participante (mesmo formato de registro
    do `base1000` do protótipo) — e manda isso pro template via `json_script`. Todo o resto
    (contagem, filtro, cartograma, rosca, barra empilhada, barras verticais e o diagrama de
    Venn com `svgVenn2`/`svgVenn3`) foi **portado pra `static/js/dashboard.js`**, reescrito
    em JS quase linha a linha a partir do protótipo (`TILES`, `filtros`, `toggleF`,
    `limparFiltros`, `renderDashPart`→`render()`, `renderVenn`, `svgVenn2`/`svgVenn3` — até a
    fórmula de luminância pro contraste do mapa, corrigida na rodada anterior, foi só
    traduzida de Python pra JS). `dashviz.py` ficou bem mais enxuto: perdeu tudo que virou
    JS (`mapa_estados`, `construir_stackbar`, `construir_barras_verticais`, `montar_venn`,
    `svg_venn2/3`, `TILES_UF`, `COR_CAPITAL`, `COR_GENERO`, `COR_SEGMENTO`) e ficou só com o
    que ainda é montado no servidor: a serialização acima, e a "Situação dos participantes" +
    "Pipeline de captação" (que continuam server-side porque não são interativos nem no
    protótipo).
  - CSS: adicionei `.filters-bar`/`.fchip`/`.fclear` (barra de chips de filtro) e os estados
    `.tile.sel`/`.lg.sel`/`.vbar.sel` (destaque de seleção) em `static/css/base.css` — cópia
    direta das mesmas classes do protótipo, que já existiam parcialmente aqui mas sem o
    estado `.sel` nem o componente de chips.
  - Testado com Playwright clicando de verdade nos elementos (não só olhando screenshot
    estático): clicar na legenda "Feminino" filtrou o mapa, a rosca de capitais, classe
    social e faixa etária todos juntos e instantaneamente (sem reload — confirmado pela
    ausência de navegação no Playwright), mostrou o chip "Gênero: Feminino ✕" na barra de
    filtros, e clicar de novo desmarcou. Sem erros no console do navegador.
  - **Segue sem commitar**, mesmo pedido de revisão prévia. `git status`: `core/dashviz.py`
    (reescrito), `core/views.py`, `templates/core/home.html`, `static/css/base.css`
    (modificados), `static/js/dashboard.js` (novo).
- **2026-08-10 (mesma sessão, "Visão por segmento")** — Usuário pediu pra fazer "a mesma
  coisa" na tela "Visão por segmento": ela ainda era a versão antiga, 100% Chart.js, com
  troca de segmento recarregando a página inteira via `?segmento=` — o mesmo padrão que
  acabou de ser trocado na Visão participantes por ser lento e pouco refinado.
  - Reli `renderDashSeg` do protótipo (abas de segmento, 4 KPIs — participantes no
    segmento/capital líder/gênero predominante/classe predominante —, comparativo entre
    segmentos em barras clicáveis, top-6 estados em `.hbar-row`, pizza de profissão, e
    gênero/classe/faixa etária específicos do segmento) e portei pra
    `static/js/dashboard_segmento.js` no mesmo molde do `dashboard.js` da tela anterior:
    nenhuma requisição ao servidor ao trocar de segmento, só refiltra o array local e
    redesenha.
  - Boa notícia: **não precisou de nenhum dado novo do servidor** — o mesmo registro que já
    ia pra Visão participantes (`uf/gen/cls/fx/cid/segs`) serve as duas telas, porque "estar
    num segmento" já é só `p.segs.includes(segSel)`. Só adicionei um campo a mais,
    `prof` (a profissão de texto livre do cadastro), em
    `dados_participantes_dashboard()`. Resultado: `core/views.py::dashboard_segmento()`
    caiu de ~35 linhas com 3 helpers auxiliares (`_grafico_ordenado`, `_grafico_top`,
    `_grafico_faixa_etaria`, todos removidos) pra 6 linhas.
  - **Profissão é texto livre no cadastro** (não é um campo de opções fixas como no
    protótipo, que usa uma lista fake de 8 categorias com cor própria cada). Adaptei pra
    dado real: agrupa as 7 profissões mais frequentes no segmento + um bucket "Outro" pro
    resto (mesma ideia do protótipo, só que calculado, não hardcoded), com uma paleta fixa
    de 8 cores por posição de rank.
  - CSS: faltavam `.chip` (selo redondo com ícone dentro do KPI), `display:flex` em
    `.kpi-top` (pra alinhar o chip com o texto) e `.kpi .foot` (linha de rodapé do card) —
    completados, cópia direta do protótipo. Também `.donut.pie::after{display:none}` pra
    pizza de profissão não ganhar o buraco/texto central do donut comum.
  - Testado com Playwright: 3 participantes reais associados a projetos do segmento
    "Banco" (via `Participacao`) apareceram corretamente em todos os painéis — capital
    líder deu "—" porque nenhum dos três mora numa das 5 capitais principais (comportamento
    correto, não bug). Troquei de aba e conferi que recalcula tudo sem reload e sem erro no
    console.
  - Com isso, `static/js/vendor/chart.umd.js` e `static/js/charts.js` ficaram sem nenhum uso
    em lugar nenhum do app (a última tela que ainda usava Chart.js era esta). Não apaguei os
    arquivos agora — não fazia parte do pedido — mas fica registrado que são candidatos a
    remoção numa limpeza futura.
  - **Segue sem commitar.** `git status` agora inclui também
    `templates/core/dashboard_segmento.html` (reescrito) e `static/js/dashboard_segmento.js`
    (novo), além do que já estava pendente da rodada da Visão participantes.
- **2026-08-10 (mesma sessão, formulários de Novo projeto / Novo participante)** — Usuário
  comparou os formulários de criação com o protótipo e apontou que ficaram muito menores/
  menos visíveis. Causa: os dois templates (`templates/projetos/form.html` e
  `templates/pessoas/form.html`) eram um loop genérico `{% for field in form %}` dentro de
  um `.panel` com `max-width` fixo (720px / 680px) — sem nenhum agrupamento visual. O
  protótipo usa `<fieldset><legend>` pra seccionar os campos ("Dados da pesquisa" / "Perfil
  desejado"; "Dados pessoais" / "Contato e endereço" / "Perfil para segmentação" / ...) e o
  painel não tem limite de largura, então cada campo fica bem mais largo e o formulário
  inteiro mais fácil de escanear.
  - Reescrevi os dois templates com a mesma estrutura de `<fieldset>` do protótipo — campo a
    campo, explicitamente (`form.nome`, `form.cliente`, etc.), já que agrupar por seção não
    dá pra fazer com o loop genérico. Pra não repetir o bloco de label+campo+erro em cada
    campo, criei um include reutilizável, `templates/core/_campo_form.html`
    (`{% include "core/_campo_form.html" with campo=form.nome %}`), no mesmo espírito do
    padrão que a tela "Meu perfil" já usava com `<fieldset>` por form.
  - Removi o `max-width` do `.panel` — sem limite nenhum, exatamente como o protótipo (a
    largura real vem só do container `.content`, que já ocupa a área útil ao lado do menu).
  - "Novo projeto" ficou com "Dados da pesquisa" (nome, cliente, metodologia, status,
    segmento, datas de campo, incentivo, valor por perfil, vagas, descrição) e "Perfil
    desejado" (idade mín/máx, gênero, região, faixa de renda, critérios livres) — Status e
    Segmento entraram em "Dados da pesquisa" mesmo não existindo no formulário simplificado
    do protótipo, porque são campos reais do nosso modelo (Segmento inclusive alimenta os
    dois dashboards reescritos nas rodadas anteriores).
  - "Novo participante" ficou com "Dados pessoais", "Contato e endereço", "Perfil para
    segmentação" (as três do protótipo) mais duas seções que o protótipo tem só no modal
    completo, mas que o nosso formulário de página cheia também precisa: "Situação e
    pagamento do incentivo" (oculta o rótulo de pagamento e os dois campos de pagamento
    quando `pode_ver_pagamento=False`, via `{% if form.forma_pagamento %}` — o campo some do
    form no `__init__` quando o usuário não tem a permissão `pagamento.ver`, e o template só
    precisa checar se ele existe) e "Consentimento LGPD".
  - Testado com Playwright em `/projetos/novo/` e `/participantes/novo/`: layout batendo
    com o protótipo (fieldsets com legenda e badge, formulário ocupando a largura toda,
    botões Cancelar/Salvar alinhados à direita, "‹ Voltar" no canto do título), sem erros no
    console.
  - **Segue sem commitar.** `git status` agora também inclui `templates/projetos/form.html`
    e `templates/pessoas/form.html` (reescritos) e `templates/core/_campo_form.html` (novo).
- **2026-08-10 (mesma sessão, formulário de Usuários)** — Usuário pediu pra aplicar a mesma
  correção de tamanho no formulário de usuários (`templates/accounts/usuario_form.html`,
  usado tanto pra cadastro quanto pra edição — mesmo `max-width:560px` e loop genérico das
  outras duas telas). O protótipo não tem uma tela de gestão de usuários de verdade (login
  lá é só um seletor "entrar como" fake, sem CRUD), então não havia markup pra copiar aqui —
  apliquei o mesmo padrão de `<fieldset>`/`_campo_form.html`/painel sem `max-width` já
  estabelecido nas duas rodadas anteriores, com seções que fazem sentido pro nosso modelo:
  "Acesso" (usuário, senha provisória, confirmação), "Dados" (nome, sobrenome, e-mail,
  telefone) e "Permissões" (nível de acesso, + "usuário ativo" na edição).
  - O mesmo template atende `UsuarioCreateForm` (cadastro) e `UsuarioEditForm` (edição), que
    têm campos diferentes — `username`/`password1`/`password2` só existem no cadastro,
    `is_active` só na edição. Resolvido com os mesmos guards `{% if form.username %}` /
    `{% if form.is_active %}` já usados no formulário de participante pra esconder os campos
    de pagamento condicionalmente — aqui escondem a fieldset inteira "Acesso" na edição, e
    revelam o checkbox "Usuário ativo" só nela.
  - Testado com Playwright em `/accounts/usuarios/novo/` (mostra "Acesso" com usuário/senha)
    e `/accounts/usuarios/5/editar/` (esconde "Acesso", mostra "Usuário ativo" marcado) — os
    dois sem erro no console.
  - **Segue sem commitar.** `git status` agora também inclui `templates/accounts/usuario_form.html`.
- **2026-08-10 (variáveis dinâmicas — Etapa 1 + Etapa 2)** — Usuário trouxe um plano de ação
  pronto (SQL genérico, "cole no Claude Code") pra um sistema de variáveis/formulários/
  respostas dinâmicas. Antes de tocar em qualquer migration, apontei que o plano foi escrito
  sem conhecimento do projeto real (citava até "ORM que você usa — ex: Entity Framework
  Core" como placeholder) e que **"respostas (pessoa_id, projeto_id) UNIQUE" já existe** — é
  exatamente `Participacao` (`participante`+`projeto`, já com `UniqueConstraint`). Levantei 4
  decisões de arquitetura via pergunta direta ao usuário em vez de assumir:
  - **Chave primária das tabelas novas: UUID** (o usuário preferiu isso à minha recomendação
    de inteiro auto-incremento, que teria sido consistente com as ~15 tabelas existentes).
    Efeito colateral real encontrado depois: como o UUID é gerado no **Python**
    (`default=uuid.uuid4`), `instance.pk` já vem preenchido *antes* de salvar — diferente de
    um `AutoField`, que só ganha valor após o INSERT. Isso quebrou a lógica ingênua "mostra o
    campo X só se `instance.pk` existir" (usada pra esconder "Variável ativa" no formulário
    de criação) — corrigido usando `instance._state.adding` (o jeito correto de perguntar
    "isso ainda não tem linha no banco", independente da estratégia de PK).
  - **`tipos_resposta`: tabela no banco**, não um `TextChoices` fixo (diferente de todo outro
    catálogo do sistema — Gênero, Situação, Segmento, etc.). Documentado no docstring do
    model `TipoResposta` que isso é uma faca de dois gumes: cadastrar um tipo novo não exige
    deploy, mas também não ganha renderização/validação sozinho — quem cadastra é responsável
    por saber que só os 8 códigos semeados (`texto`, `inteiro`, `decimal`, `booleano`, `data`,
    `select`, `radio`, `multipla_escolha`) têm suporte real no formulário hoje.
  - **Formulário × Projeto: N:N**, via tabela de ligação `ProjetoFormulario` (não FK direto)
    — um projeto pode reunir mais de um formulário (ex.: screener + perfil detalhado) e um
    formulário-modelo pode ser reaproveitado em vários projetos. Isso está pronto no banco
    desde já (Etapa 1), mas **sem tela ainda** (Etapa 4 do roadmap).
  - **Escopo desta leva: Etapa 1 (modelagem) + Etapa 2 (CRUD de Variáveis)** — o resto do
    roadmap (Formulários, Projetos×Formulários, Respostas, telas 7–10) fica pra próximas
    conversas, confirmando escopo antes de cada uma (como o próprio plano do usuário pediu).
  - **Modelagem** (novo app `formularios`, `formularios/models.py`): `TipoResposta`,
    `Variavel` (com `chave` auto-gerada a partir do `nome` via slug + sufixo numérico em caso
    de colisão — mesmo padrão de `Participante._gerar_codigo()`), `VariavelOpcao`,
    `Formulario`, `FormularioVariavel` (liga formulário↔variável, com ordem),
    `ProjetoFormulario` (liga projeto↔formulário, N:N real), `RespostaFormulario` (liga
    `Participacao`↔`Formulario`, `JSONField` pras respostas dinâmicas + índice GIN via
    `django.contrib.postgres.indexes.GinIndex` — precisou adicionar `django.contrib.postgres`
    a `INSTALLED_APPS`, não estava lá). Todas as FKs pra `Variavel`/`Formulario` em uso usam
    `on_delete=PROTECT` — a forma de "excluir" uma variável/formulário em uso é desativá-la
    (`ativa`/`ativo`), não apagar. `Projeto` e `Participacao` **não foram alterados** — a
    ligação é só via FK reversa (`projeto.projeto_formularios`,
    `participacao.respostas_formularios`), então nenhuma migration nos apps `projetos`/
    `participacoes` foi necessária.
  - **Permissões**: `variaveis.ver`/`variaveis.gerenciar`/`variaveis.excluir` seguindo o
    padrão de 3 níveis já usado por `participantes.*`/`projetos.*` (migração de dados
    `accounts/migrations/0007_seed_variaveis_permissoes.py`, mesmo formato das seeds
    anteriores) — Administrador e Operador com as três, Visualizador só com `.ver`,
    Freelancer sem nenhuma. Item "Variáveis" adicionado ao menu lateral dentro de "Banco de
    Pessoas", ao lado de "Projetos".
  - **CRUD de Variáveis** (`formularios/views.py`, `formularios/forms.py`,
    `templates/formularios/`): lista (`/formularios/variaveis/`, tabela com nome/chave/tipo/
    obrigatória/status), criar/editar num só template com `<fieldset>` (mesmo padrão dos
    formulários de projeto/participante/usuário desta sessão), e excluir com confirmação
    (bloqueia com mensagem amigável se a variável já estiver em uso — `ProtectedError`
    capturado na view). O formulário de opções (só relevante pra `select`/`radio`/
    `multipla_escolha`) usa um `inlineformset_factory` (mesmo mecanismo já usado no wizard de
    importação em massa) — variável e opções são validadas e salvas juntas numa
    `transaction.atomic()`, com uma regra de negócio própria: **tipo que exige opção não
    salva sem pelo menos uma opção preenchida** (senão a variável ficaria inutilizável). O
    campo "Opções de resposta" aparece/some no formulário via um JS pequeno
    (`static/js/variavel_form.js`) que lê o `codigo` do tipo selecionado (mandado como JSON
    pro cliente, não hardcoded no JS, pra não desalinhar com `CODIGOS_COM_OPCOES` do
    servidor).
  - Testado de ponta a ponta com Playwright contra o banco real: criar variável tipo texto
    (bloco de opções escondido), criar variável tipo select com 2 opções (bloco visível,
    salva certo), tentar criar select **sem** nenhuma opção (bloqueado com a mensagem de
    erro esperada, não salva), editar pra desativar, excluir. Um detalhe curioso do processo
    de teste: os primeiros scripts de teste clicavam sem querer no botão "Sair" da barra
    lateral em vez de "Salvar" (os dois são `button[type="submit"]`, e o seletor não estava
    específico o bastante) — não era bug da aplicação, só do script de teste; corrigido
    escopando o clique ao formulário certo. Dados de teste (variáveis criadas durante os
    testes) foram excluídos ao final.
  - **Segue sem commitar** — mesma prática desta sessão inteira de só commitar quando o
    usuário pedir. `git status`: app `formularios/` inteiro (novo), `accounts/permissions.py`,
    `accounts/migrations/0007_seed_variaveis_permissoes.py` (novo), `bancopessoas/settings.py`
    e `bancopessoas/urls.py` (registram o app novo), `templates/base.html` (item de menu).
- **2026-08-10 (variáveis dinâmicas — reorganização de menu + Etapa 3)** — Antes de seguir
  pro resto do roadmap, usuário pediu pra mover "Variáveis" (e o "Formulários" que ia nascer
  na Etapa 3) pra dentro de um submenu novo, "Configurações de Formulários", abaixo de
  "Banco de Pessoas" — até então "Variáveis" estava solta dentro do próprio grupo "Banco de
  Pessoas". Em `templates/base.html`: tirei "Variáveis" de lá (revertendo a condição do
  grupo "Banco de Pessoas" pro que era antes) e criei um novo `<details class="nav-group">`
  "Configurações de Formulários" (abre sozinho quando `request.resolver_match.app_name ==
  "formularios"`, mesmo padrão do grupo "Dashboards"), com "Variáveis" e "Formulários" dentro,
  cada um com o próprio realce de item ativo por `url_name`.
  - **Etapa 3 do roadmap — CRUD de Formulários** (`Formulario` já existia desde a Etapa 1,
    só faltava a tela): lista em `/formularios/` (nome, se inclui os campos fixos do
    participante, quantas variáveis tem, status), criar/editar num só template e excluir com
    confirmação — mesmo padrão de `<fieldset>` já estabelecido. A parte de "escolher quais
    variáveis entram, em que ordem" **não é um `ModelForm` comum** (é gerenciar a tabela de
    ligação `FormularioVariavel`, que carrega um campo extra, `ordem`, além do M2M), então
    usei um `formset_factory` simples (`VariavelSelecaoForm`: `variavel_id` oculto +
    `incluir` (checkbox) + `ordem` (número)) — uma linha por variável **ativa** existente,
    pré-marcada com o estado atual quando editando. `formularios/forms.py::
    montar_formset_variaveis()` casa cada `Variavel` com seu subformulário numa lista de
    tuplas, pra o template iterar num `{% for variavel, subform in linhas %}` só. Salvar
    sincroniza a tabela de ligação inteira numa transação: apaga as associações desmarcadas,
    faz `update_or_create` nas marcadas com a `ordem` enviada. Reordenação por
    arrastar-e-soltar (pedida no plano original só na Etapa 7, como polimento de UX) **não**
    entrou aqui — por ora a ordem é um campo numérico comum, que já resolve o "com ordem" da
    Etapa 3.
  - Permissões: `formularios.ver`/`.gerenciar`/`.excluir`, mesma migração-padrão
    (`accounts/migrations/0008_seed_formularios_permissoes.py`), mesma matriz de
    `variaveis.*` (Administrador e Operador com as três, Visualizador só `.ver`).
  - Testado com Playwright: reorganização do menu confirmada visualmente (submenu
    "Configurações de Formulários" com os dois itens, abre e realça certo); criei 2
    variáveis, montei um formulário marcando as duas com ordens 1 e 2, salvei, reabri pra
    editar e conferi que os checkboxes e as ordens persistiram exatamente como gravadas.
    Dados de teste excluídos ao final (o formulário primeiro, pra liberar as variáveis do
    `PROTECT`).
  - **Segue sem commitar.** `git status` agora também inclui `templates/formularios/
    formularios_lista.html`, `formulario_form.html`, `formulario_excluir.html` (novos),
    `formularios/forms.py`/`views.py`/`urls.py` (modificados) e
    `accounts/migrations/0008_seed_formularios_permissoes.py` (novo).
  - Próximas etapas do roadmap (confirmar escopo antes de cada uma, como já vinha sendo
    feito): Etapa 4 (associar Formulários a Projetos — o banco já suporta N:N via
    `ProjetoFormulario`, falta só a tela), Etapa 5 (Respostas).
- **2026-08-10 (variáveis dinâmicas — Etapa 4)** — Associar Formulários a Projetos. Reusei o
  mesmo mecanismo da Etapa 3 (`formset_factory` com `incluir`+`ordem` por linha, uma linha
  por item disponível) só que na direção Projeto→Formulário: `FormularioSelecaoForm`/
  `montar_formset_formularios()` em `formularios/forms.py`, espelhando
  `VariavelSelecaoForm`/`montar_formset_variaveis()` quase campo a campo.
  - Nova view `formularios:projeto_formularios` (`/formularios/projetos/<id_do_projeto>/`,
    permissão `projetos.gerenciar` — decidi que "quais formulários este projeto usa" é
    configuração do projeto, não do catálogo de formulários, então a permissão certa é a do
    projeto, não `formularios.gerenciar`) fica no app `formularios` (é lá que `Formulario` e
    `ProjetoFormulario` moram), mas é alcançada a partir da tela do projeto — sem gerar mais
    um item de menu, é sempre "de dentro" de um projeto específico.
  - `templates/projetos/detalhe.html` ganhou um painel novo, "Formulários associados"
    (nome, se inclui campos fixos, quantas variáveis — mesmas colunas da lista de
    Formulários), com um botão "Gerenciar formulários" que só aparece pra quem já vê os
    botões "Editar"/"Excluir" do projeto (`pode_editar`). `Projeto`/`projetos/views.py` não
    precisaram de nenhuma mudança — o painel lê direto `projeto.projeto_formularios.all`
    (FK reversa que já existia desde a Etapa 1, ordenada por `ordem` via `Meta.ordering` do
    `ProjetoFormulario`).
  - Testado com Playwright: criei um formulário, associei ao projeto de teste existente
    ("Teste Bancos Digitais") marcando a caixa e definindo ordem, salvei, confirmei que o
    painel "Formulários associados" na tela do projeto mostra a linha certa e a mensagem de
    sucesso apareceu. Limpeza ao final teve uma pegadinha: `ProjetoFormulario.formulario` é
    `PROTECT` (decisão da Etapa 1 — não se apaga um formulário em uso), então excluir o
    formulário de teste direto deu `ProtectedError`; precisei apagar a ligação
    (`ProjetoFormulario`) primeiro e o formulário depois — comportamento correto do sistema,
    não um bug (é exatamente a mesma trava que protege contra apagar uma variável em uso).
  - **Segue sem commitar.** `git status` agora também inclui `templates/formularios/
    projeto_formularios.html` (novo), `templates/projetos/detalhe.html`,
    `formularios/forms.py`/`views.py`/`urls.py` (modificados).
  - Falta a **Etapa 5 (Respostas)** — a mais decisão-pesada do roadmap (como um operador
    efetivamente "responde" um formulário pra uma participação, tela de preenchimento,
    listagem de respostas por projeto). Confirmar escopo antes de começar, como o usuário já
    vinha pedindo desde o plano original.
- **2026-08-10 (variáveis dinâmicas — Etapa 5, Respostas)** — Perguntei 2 decisões antes de
  começar: **onde preencher** (o usuário escolheu: na própria tela da Participação, não um
  fluxo separado) e **o que fazer com tipo de resposta sem renderização própria** (escolheu:
  cai em texto livre, não bloqueia).
  - **Achado real ao investigar**: não existia tela de detalhe de Participação nenhuma —
    o app `participacoes` só tinha lista, kanban, "nova" e "avaliar" (um form solo). Pra
    cumprir a decisão do usuário ("na tela da Participação") precisei criar essa tela
    primeiro: `participacoes:detalhe` (`/participacoes/<pk>/`, nova view + novo template
    `templates/participacoes/detalhe.html`) — participante/projeto/etapa, avaliação (se
    houver), e o painel novo "Respostas de formulário". Também troquei o redirect de
    `avaliar()` pra cair aqui em vez de voltar pra lista, e linkei "Ver" na lista e o nome
    do card no kanban pra essa tela nova.
  - **Formulário de resposta dinâmico** (`formularios/respostas.py`, novo módulo): monta um
    `forms.Form` **em tempo real** — uma pergunta por `FormularioVariavel` do formulário,
    na ordem cadastrada — via `type("...", (forms.Form,), campos)` (padrão Django normal pra
    formulário dinâmico, não é gambiarra). Um campo por tipo de resposta: `IntegerField`
    (inteiro), `DecimalField` (decimal), `DateField` (data), `ChoiceField`/`RadioSelect`/
    `MultipleChoiceField` (select/radio/múltipla escolha, com as opções cadastradas na
    variável), `TypedChoiceField` com radio Sim/Não pro booleano (decisão de correção: um
    `BooleanField` comum e obrigatório forçaria "Sim" como única resposta válida — errado
    pra uma pergunta Sim/Não, onde "Não" é resposta tão definitiva quanto "Sim"), e
    `CharField`/`Textarea` pra texto **e pra qualquer tipo sem suporte específico** (a
    decisão do usuário). As respostas gravam em `RespostaFormulario.respostas_variaveis`
    (JSONB) com a **chave da variável** como chave do JSON — bate exatamente com o exemplo
    do plano original (`{"rotina_skincare": "diaria", ...}`).
  - **Bug real encontrado e corrigido pelo teste**: o campo de data vinha salvo certo, mas
    ao reabrir pra editar aparecia **vazio**. Causa: `forms.DateInput(attrs={"type":
    "date"})` sem um `format` explícito usa o formato localizado (pt-br → dd/mm/aaaa) pra
    desenhar o valor inicial — só que um `<input type="date">` HTML5 só aceita
    `aaaa-mm-dd`; o navegador recebe um valor num formato que não reconhece e mostra o
    campo em branco, mesmo com o dado salvo certinho no banco. Corrigido forçando
    `format="%Y-%m-%d"` no widget. Serialização de Decimal/date pro JSON também precisou de
    ajuste: `RespostaFormulario.respostas_variaveis` ganhou `encoder=DjangoJSONEncoder`
    (o encoder padrão do `JSONField` não sabe serializar esses tipos sozinho).
  - Segurança: a view `responder_formulario` confere que o formulário realmente está
    associado ao projeto daquela participação (via `ProjetoFormulario`) antes de deixar
    responder — sem isso, dava pra montar a URL na mão e responder um formulário de
    qualquer outro projeto.
  - Permissões novas: `respostas.ver` (ver o painel/status) e `respostas.preencher`
    (responder/editar), mesmo padrão de seed (`accounts/migrations/
    0009_seed_respostas_permissoes.py`) — Administrador e Operador com as duas,
    Visualizador só `.ver`, Freelancer sem nenhuma (pode reconsiderar depois, é editável no
    Painel de Permissões).
  - Testado com Playwright de ponta a ponta contra o banco real: criei 6 variáveis (uma de
    cada tipo com suporte — texto, inteiro, decimal, booleano, data, select), montei um
    formulário com as seis, associei ao projeto de teste, abri a participação, respondi
    tudo, salvei, reabri pra editar e conferi que **todos os 6 valores** vieram
    pré-preenchidos exatamente como gravados (incluindo o de data, depois da correção).
    Dados de teste excluídos ao final — inclusive um formulário e uma variável de teste
    esquecidos de uma rodada anterior desta mesma sessão, achados na limpeza.
  - **Segue sem commitar.** `git status` agora também inclui `formularios/respostas.py`
    (novo), `templates/participacoes/detalhe.html`, `templates/formularios/
    responder_formulario.html` (novos), `participacoes/views.py`/`urls.py`,
    `templates/participacoes/lista.html`/`kanban.html`, `formularios/models.py`/`views.py`/
    `urls.py`, `accounts/permissions.py` (modificados) e as 2 migrações novas
    (`formularios/migrations/0003_...`, `accounts/migrations/0009_...`).
  - **Roadmap completo desde o plano original agora está com as etapas core prontas**
    (1–5). Restam as etapas de polimento de UX (6 já saiu junto da 2; 7 reordenação
    drag-and-drop; 8 é redundante — já coberto pela Etapa 4; 9 já saiu junto da 5; 10 é a
    view achatada pra scoring, ainda não pedida). Perguntar ao usuário se quer seguir pra
    alguma dessas ou considerar o essencial do plano concluído por ora.
- **2026-08-10 (variáveis dinâmicas — 2 correções pós-uso real)** — Usuário testou por conta
  própria (criou "Formulário de Teste" com 2 variáveis reais — CPF e Data de Nascimento) e
  reportou dois problemas: (1) não dá pra ver uma prévia do formulário com as perguntas, só
  a contagem de variáveis; (2) não dá pra associar formulário a projeto "como estava
  previsto".
  - **(1) Prévia do formulário** — reaproveitei o mesmo renderizador dinâmico da Etapa 5
    (`formularios/respostas.py::construir_form_resposta`), que já sabe montar um campo por
    variável no tipo certo — só precisou ganhar um modo `somente_leitura=True` (desabilita
    os campos, sem exigir preenchimento). Nova tela `formularios:formulario_visualizar`
    (`/formularios/<id>/visualizar/`, permissão só `formularios.ver` — qualquer um que
    enxerga a lista consegue ver o conteúdo, não só quem gerencia), com link "Visualizar" na
    lista de Formulários, na tabela "Formulários associados" do projeto, e um link
    "visualizar" (abre em nova aba, pra não perder marcações não salvas) na própria tela de
    seleção.
  - **(2) Associar a projeto "como estava previsto"** — reexaminando o texto original do
    plano ("Endpoint pra **criar projeto associando** um formulário existente"), a intenção
    sempre foi a escolha acontecer **dentro do próprio formulário de Novo/Editar Projeto**,
    não só numa tela solta alcançada depois de já ter salvado (a "Gerenciar formulários" da
    Etapa 4). Testei a tela solta isoladamente pra descartar bug — ela salva e persiste
    normalmente — então o problema real era de local, não de funcionamento. Corrigido:
    `templates/projetos/form.html` ganhou a fieldset "Formulários associados" (mesma tabela
    de sempre — nome, campos fixos, variáveis, ordem — com link de prévia), e
    `projetos/views.py::novo`/`editar` agora validam e sincronizam esse formset na mesma
    transação que salva o projeto. Pra não duplicar a lógica de sincronização, extraí
    `sincronizar_formularios_projeto()` pra `formularios/forms.py` e passei a chamá-la tanto
    daqui quanto da view antiga `projeto_formularios` (que continua existindo como atalho
    rápido pra ajustar só os formulários sem abrir o formulário inteiro do projeto — os dois
    caminhos agora usam exatamente a mesma função de sincronização, garantindo que ficam
    consistentes entre si).
  - **Nota de transparência**: na limpeza de dados de teste do fim da rodada anterior, apaguei
    um "Formulário de Teste 1" e uma variável "Faixa de Renda" presumindo que fossem sobras
    dos meus próprios testes (mesma conta `admin_demo` que eu uso para testar) — não dava pra
    diferenciar com certeza dados meus dos do usuário, já que os dois usam a mesma conta
    demo. Como o "Formulário de Teste" (sem o "1") que o usuário está usando agora sobreviveu
    intacto com as 2 variáveis reais dele, o que foi apagado parece mesmo ter sido uma sobra
    de tentativa anterior — mas registro aqui porque não tenho certeza absoluta, e não devia
    ter apagado sem confirmar antes. Devo evitar isso daqui pra frente: só apagar dados
    criados dentro do próprio script de teste da mesma rodada, nunca "parece teste" por
    inferência de nome.
  - Testado com Playwright: prévia mostrando as 2 perguntas reais do usuário certinho
    (rótulo, tipo, obrigatoriedade); criação de projeto novo já com formulário marcado na
    hora, confirmando associação imediata na tela de detalhe. Projeto de teste apagado ao
    final (o formulário e a variável do usuário não foram tocados desta vez).
  - **Segue sem commitar.** `git status` agora também inclui `formularios/respostas.py`,
    `formularios/forms.py`/`views.py`/`urls.py`, `templates/formularios/formularios_lista.html`,
    `templates/formularios/projeto_formularios.html`, `templates/projetos/detalhe.html`/
    `form.html`, `projetos/views.py` (modificados) e `templates/formularios/
    formulario_visualizar.html` (novo).
- **2026-08-10 (variáveis dinâmicas — página pública de cadastro)** — Usuário testou o ciclo
  completo (criou formulário, associou variáveis, associou o formulário a um projeto) e
  reportou que o **link público de cadastro** gerado pelo projeto (`/participantes/cadastro/
  <token>/` — o link sem login que um recrutador manda pro participante preencher sozinho,
  já existia desde a Fase 2) não vinha com as perguntas do formulário associado — só os
  campos fixos de sempre (nome, CPF, contato...).
  - Causa: `pessoas/views.py::cadastro_publico` foi escrito antes do sistema de variáveis
    dinâmicas existir e nunca foi atualizado — ele só conhece `CadastroPublicoForm` (campos
    fixos do `Participante`), sem nenhuma ideia de `Formulario`/`ProjetoFormulario`.
  - Corrigido reaproveitando outra vez `formularios/respostas.py::construir_form_resposta`
    (a terceira vez que essa peça é reutilizada, depois de "Responder" na tela de
    Participação e da prévia de Formulário — confirma que valeu a pena ter feito como função
    genérica reutilizável em vez de código dedicado a cada tela). Novo helper
    `pessoas/views.py::_forms_dinamicos_do_projeto()` monta **um formulário dinâmico por
    `Formulario` ativo associado ao projeto** (um projeto pode ter mais de um, por causa do
    N:N decidido lá na Etapa 1) — a página pública agora renderiza os campos fixos de sempre
    **e** uma seção por formulário associado, tudo no mesmo POST. No envio, grava
    `Participante` + `Participacao` (como já fazia) **e** um `RespostaFormulario` por
    formulário que tiver pelo menos uma variável, numa única transação.
  - Testado com Playwright de ponta a ponta, em duas abas de navegador separadas (uma logada
    como Administrador pra gerar o link, outra sem sessão nenhuma simulando o participante
    real): o "Formulário de Teste" do usuário (agora com 3 variáveis — ele adicionou "Nome
    Completo" desde a última rodada) apareceu certinho na página pública, com os 3 campos
    preenchíveis; enviei o cadastro e confirmei no banco que `Participante`, `Participacao`
    **e** `RespostaFormulario` foram criados juntos, com as 3 respostas gravadas certas
    (inclusive a data, no formato certo). Dado de teste apagado ao final.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/views.py` e
    `templates/publico/cadastro.html`.
- **2026-08-12 (variáveis dinâmicas + auditoria de aceite LGPD)** — Usuário testou de novo a
  página pública e pediu 3 ajustes de layout, mais um recurso novo: registro de auditoria de
  aceite de termo (data/hora/IP) visível no perfil do participante, pra todos os documentos e
  versões que ele já aceitou.
  1. **Campo de texto muito grande** — os campos "texto livre" (textarea) ficavam
     desproporcionais ao lado dos campos fixos (input de uma linha). Em vez de mudar o "Texto
     livre" existente (que ainda faz sentido pra resposta longa), criei um **tipo novo**,
     `texto_curto` ("Texto curto (uma linha)") — migração de seed
     `formularios/migrations/0004_seed_tipo_texto_curto.py`, suporte de renderização em
     `formularios/respostas.py::_campo_para_variavel` (`forms.CharField` com
     `forms.TextInput` em vez de `Textarea`). Os dois tipos de texto convivem agora — quem
     cadastra a variável escolhe qual cabe melhor pra cada pergunta.
  2. **Título "Formulário de Teste" na página pública** — o `<fieldset><legend>` que
     envolvia cada formulário associado ao projeto foi removido; as perguntas de todos os
     formulários associados agora entram direto na mesma grade dos campos fixos, sem
     seção/caixa separada — "é só continuar o formulário", como pedido.
  3. **Checkbox de LGPD reposicionado** — antes vinha no meio da grade de campos (porque
     `consentimento_lgpd` é só mais um campo do `CadastroPublicoForm`); agora é
     explicitamente pulado no loop principal e renderizado à parte, logo abaixo do texto do
     termo vigente (`versao_lgpd.texto`) e acima do botão de enviar.
  4. **Auditoria de aceite** — novo modelo `termos.AceiteTermo` (`participante`, `versao`,
     `origem` [`PUBLICO`/`STAFF`], `aceito_em`, `ip`, `user_agent`, `registrado_por`) — um
     registro **imutável por aceite**, diferente de `Participante.consentimento_versao` (que
     só guarda a versão *atual*, sobrescrevível, sem histórico). `termos/models.py::
     registrar_aceite()` é o único ponto que grava, chamado nos **4 lugares** onde
     `consentimento_lgpd`/`consentimento_versao` já eram setados
     (`pessoas/views.py::novo`, `editar`, `wizard_revisao`, `cadastro_publico`) — cada um
     passando a `origem` certa (`STAFF` pros três primeiros, já que é um operador logado
     preenchendo; `PUBLICO` só no cadastro público, onde quem aceita é a própria pessoa,
     sem login, e o IP/user-agent capturados são dela de fato). `registrado_por` é sempre um
     `Usuario` interno — nos três primeiros é `request.user`; no público é o `recrutador`
     (dono do link, não quem aceitou — não existe um "Usuario" pra a pessoa pública).
     - **IP real por trás de proxy**: não existia nenhum helper de IP no projeto ainda —
       `REMOTE_ADDR` sozinho dá o IP do proxy do Railway em produção, não o do participante.
       Novo `core/request_utils.py::ip_cliente()` prioriza `X-Forwarded-For` (primeiro IP da
       cadeia) e só cai pra `REMOTE_ADDR` se esse cabeçalho não existir (rodando local, sem
       proxy).
  5. **Painel "Termos aceitos" no perfil do participante** — nova seção em
     `templates/pessoas/detalhe.html`, entre "Dados cadastrais" e "Triagem": lista **todos**
     os aceites do participante (documento, versão, data/hora, origem, IP, quem registrou),
     com um `<details>` por linha pra ver o texto completo daquela versão sem precisar sair
     da página nem carregar nada por JS.
  - Testado com Playwright: criei variáveis dos dois tipos de texto num formulário próprio,
    conferi visualmente que "Texto curto" ficou do mesmo tamanho dos campos fixos e "Texto
    livre" continua maior; conferi que não sobrou nenhum `<fieldset><legend>` na página
    pública e que a ordem dos elementos no HTML é texto do termo → checkbox → botão enviar;
    enviei um cadastro público completo e confirmei no banco um `AceiteTermo` com
    `origem=PUBLICO`, IP e user-agent reais capturados, `registrado_por` = o recrutador do
    link; testei também o cadastro interno (`pessoas:novo`) e confirmei um segundo
    `AceiteTermo` com `origem=STAFF`; conferi visualmente o painel "Termos aceitos" no
    perfil do participante, mostrando a linha certa com o "Ver texto" funcionando. Dados de
    teste apagados ao final — confirmei que o "Formulário de Teste" e as 3 variáveis reais
    do usuário continuam intactos.
  - **Segue sem commitar.** `git status` agora também inclui `formularios/respostas.py`
    (modificado), `formularios/migrations/0004_seed_tipo_texto_curto.py`,
    `termos/models.py`, `termos/migrations/0003_aceitetermo.py`, `core/request_utils.py`
    (novos/modificados), `templates/publico/cadastro.html`, `templates/pessoas/detalhe.html`
    e `pessoas/views.py`.
- **2026-08-12 (endereço com busca de CEP)** — No cadastro principal de participante
  (interno e público), usuário pediu: CEP primeiro (antes de Cidade/UF), busca automática de
  Estado/Cidade a partir do CEP, campo Bairro novo, e Estado/Cidade virarem listas suspensas
  — a de Cidade também alimentada por API, listando em ordem alfabética as cidades do estado
  escolhido.
  - **Modelo** (`pessoas/models.py`): `Participante.UF` — `TextChoices` com as 27
    siglas/nomes (substitui o `RegexValidator` de 2 letras que existia antes, agora
    redundante já que `choices` garante uma sigla válida); novo campo `bairro`
    (`CharField`, opcional). Campos reordenados no próprio modelo: `cep`, `bairro`, `uf`,
    `cidade` (a ordem de declaração no modelo não importa pro banco, mas importa pra ordem
    default nos formulários que só fazem `{% for field in form %}`, como o cadastro
    público).
  - **`pessoas/forms.py`**: `uf` declarado explicitamente como `ChoiceField` com opção em
    branco "Selecione…" na frente. `cidade` continua `CharField` no banco (não dá — nem
    faz sentido — hardcodar os +5.000 municípios do Brasil como `choices` do Django), mas
    ganha `widget=forms.Select()`: o HTML nasce só com um placeholder e a lista de opções de
    verdade é populada inteiramente no navegador, via JS, depois que o Estado é escolhido —
    exatamente por isso continua sendo `CharField` (aceita qualquer string que o JS colocar
    lá, sem exigir que o Django conheça a lista inteira de antemão). Editar um participante
    já cadastrado precisa mostrar a cidade atual antes do JS rodar — `__init__` injeta a
    cidade da instância como única opção válida até a lista de verdade chegar.
    `ParticipanteWizardForm` (formset de N linhas do wizard de importação em massa)
    **explicitamente volta** UF e Cidade a serem texto livre — não vale a pena religar
    CEP→Estado→Cidade por JS em cada linha de um formset, e CSV já manda essas colunas como
    texto puro mesmo.
  - **`static/js/endereco_cep.js`** (novo): duas APIs públicas, sem chave — **ViaCEP**
    (`viacep.com.br/ws/{cep}/json/`) no blur do campo CEP, preenchendo Bairro/UF e
    disparando a busca de cidades; **IBGE** (`servicodados.ibge.gov.br/.../municipios?
    orderBy=nome`) sempre que o Estado muda (por CEP ou escolha manual), já vindo do
    servidor do IBGE em ordem alfabética. Usado nas duas telas de cadastro principal —
    `templates/pessoas/form.html` (interno) e `templates/publico/cadastro.html` (público,
    sem login — script solto antes do `</body>` já que a página não estende `base.html`).
  - Ordem dos campos: "Contato e endereço" (interno) e a grade do cadastro público agora
    seguem CEP+Bairro numa linha, UF+Cidade na próxima.
  - `templates/pessoas/detalhe.html` ganhou linhas de Bairro e CEP na tabela "Dados
    cadastrais" (só tinha Cidade/UF antes).
  - Testado com Playwright nas duas telas, com um CEP real (Av. Paulista → Bela Vista, São
    Paulo/SP) e outro (Centro, Rio de Janeiro/RJ): Bairro/UF/Cidade preenchidos sozinhos,
    dropdown de cidade carregado com as cidades certas do estado (646 pra SP, 93 pra RJ,
    batendo com a contagem real de municípios), reordenação confirmada visualmente, e um
    cadastro completo enviado com sucesso pela página pública, confirmando no banco que
    `cep`/`bairro`/`uf`/`cidade` gravaram exatamente os valores buscados pela API. Dados de
    teste apagados ao final.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/models.py`,
    `pessoas/forms.py`, `pessoas/migrations/0003_participante_bairro_alter_participante_uf.py`,
    `static/js/endereco_cep.js` (novo), `templates/pessoas/form.html`,
    `templates/pessoas/detalhe.html` e `templates/publico/cadastro.html`.
  - **Ajuste rápido de ordem**: usuário corrigiu a ordem final — era CEP→Bairro→UF→Cidade,
    o certo é **CEP→UF→Cidade→Bairro**. `ParticipanteForm.Meta.fields` reordenado (isso
    também resolve a ordem no cadastro público, que só faz `{% for field in form %}`) e
    `templates/pessoas/form.html` (interno) reordenado junto. Sem migration — é só ordem de
    exibição, não mexe no banco. Confirmado com Playwright nas duas telas.
- **2026-08-12 (avaliação vira modal com estrelas)** — Usuário pediu 4 coisas na tela de
  avaliação de participações: (1) modal em vez de página separada, (2) estrelas de 1 a 5 em
  vez dos rádios simples, (3) "nota final" deixar de ser digitada e virar a média dos 3
  quesitos, aparecendo na lista de participações, (4) essa nota (e link pro detalhe com nota
  + comentário) aparecer também nas participações listadas dentro do perfil do participante.
  - **`Avaliacao.nota_geral` virou `@property`** (`round((comunicacao+pontualidade+
    repertorio)/3, 1)`) em vez de campo digitado — migração remove a coluna do banco.
    `AvaliacaoForm` perdeu o campo `nota_geral` (só resta comunicação/pontualidade/
    repertório/comentário). Uma casa decimal de propósito — arredondar pra inteiro
    esconderia a diferença entre, por exemplo, 4+4+4 e 5+4+3 (as duas dariam "4").
  - **Modal, do zero** — não existia nenhuma infraestrutura de modal no projeto Django (só
    no protótipo). Portei `.overlay`/`.modal`/`.modal-head`/`.modal-body`/`.modal-foot`/
    `.modal-x` pro `static/css/base.css` e criei `static/js/modal.js`
    (`QVModal.abrir/fechar`, clique no fundo fecha, Esc fecha) — genérico, qualquer modal
    futuro reaproveita.
  - **Estrelas de verdade** (glifo ★, não os "pills" numéricos que o protótipo usa) — CSS
    puro, sem JS: `NOTAS` em `participacoes/forms.py` foi invertido pra `5,4,3,2,1` (rádios
    nascem nessa ordem no HTML) e `.star-rating` usa `flex-direction:row-reverse` +
    `input:checked ~ label`/`label:hover ~ label` pra pintar a estrela clicada/passada e
    todas à esquerda dela na tela — é o truque clássico de "star rating" só em CSS. Dois
    jeitos de desenhar: `templates/core/_campo_estrelas.html` (a partir de um `BoundField`
    Django de verdade, usado no modal servidor-renderizado do detalhe da participação — o
    pré-preenchimento ao editar já vem pronto do próprio Django, sem JS) e
    `templates/core/_estrelas_input.html` (rádios soltos por nome/valor, usado no modal
    compartilhado da lista, onde `static/js/avaliar_modal.js` marca os valores certos via
    `data-*` de cada botão "Avaliar"/"Editar" da linha antes de abrir).
  - **Dois modais, dois jeitos de preencher, mesma URL de POST**: `templates/participacoes/
    detalhe.html` (uma participação por vez) usa um modal com o `AvaliacaoForm(instance=...)`
    de verdade vindo da view — edição já chega pré-marcada certinha. `templates/
    participacoes/lista.html` (N linhas, N avaliações possíveis) usa **um modal só,
    reaproveitado**: cada botão da linha carrega `data-comunicacao`/`data-pontualidade`/
    `data-repertorio`/`data-comentario`/`data-url` (vazios se ainda não avaliada), e
    `abrirModalAvaliar()` aponta o `<form>` pra URL certa e marca os rádios antes de abrir —
    sem fetch, sem JSON, o `<form>` continua sendo um POST normal (recarrega a página no
    fim, só que agora sempre de volta pro detalhe da participação, onde o resultado
    aparece).
  - **`participacoes:avaliar` virou uma view só de POST** (`@require_POST`) — GET redireciona
    pro detalhe (a página separada não existe mais, template
    `templates/participacoes/avaliar.html` apagado). Em erro de validação, `messages.error`
    + redirect de volta ao detalhe (não tenta re-renderizar um modal específico com erro
    campo a campo — os 3 campos são obrigatórios e sempre visíveis, então "esqueceu de
    marcar uma estrela" é o único jeito de falhar, e a mensagem genérica já deixa claro o
    que fazer).
  - **Prévia da nota final ao vivo**: enquanto marca as estrelas no modal, um texto "Nota
    final (média)" atualiza em tempo real (JS simples, sem servidor) — não é só cosmético,
    é a resposta direta ao pedido "a nota final... é média de 1 a 5 dos quesitos": a pessoa
    vê a média sendo calculada na hora, antes mesmo de salvar.
  - **Nota na lista de participações** (`templates/participacoes/lista.html`) e **nas
    participações do perfil do participante** (`templates/pessoas/detalhe.html`, tabela
    "Participações") — a segunda também ganhou linha inteira clicável (`onclick` no `<tr>`)
    levando pro detalhe da participação, que já mostra nota (em estrelas, somente leitura)
    e comentário.
  - Testado com Playwright: modal abrindo pela lista, clique nas estrelas atualizando a
    prévia da nota em tempo real (4+5+3 → "4.0"), salvar e conferir no detalhe da
    participação (estrelas certas, nota 4,0, comentário), reabrir o modal de edição no
    detalhe e confirmar que os 3 valores vêm pré-marcados certos (o Django cuidando disso
    sozinho, sem JS), e a tabela de Participações no perfil mostrando a nota e navegando
    pro detalhe ao clicar na linha. Avaliação de teste apagada ao final.
  - **Segue sem commitar.** `git status` agora também inclui `participacoes/models.py`,
    `participacoes/forms.py`, `participacoes/views.py`,
    `participacoes/migrations/0002_remove_avaliacao_nota_geral.py`, `static/js/modal.js`
    (novo), `static/js/avaliar_modal.js` (novo), `templates/core/_campo_estrelas.html`
    (novo), `templates/core/_estrelas_input.html` (novo), `templates/participacoes/
    lista.html`, `templates/participacoes/detalhe.html`, `templates/pessoas/detalhe.html`
    (modificados) e `templates/participacoes/avaliar.html` (removido).
- **2026-08-12 (link de captação: sem prazo, só por status)** — Usuário pediu 2 mudanças na
  regra do link público de cadastro: tirar a validade fixa de 48h, e só deixar responder o
  formulário enquanto o projeto está com status "Recrutando" (antes aceitava qualquer status
  exceto "Concluído" — ou seja, "Em campo" também deixava cadastrar, o que não fazia sentido
  pro fluxo real).
  - `pessoas/links.py::ler_token_captacao()` parou de passar `max_age` pro `loads()` do
    Django (o token em si não guarda mais uma "validade embutida" — sem `max_age`, o
    `django.core.signing` nunca expira por tempo, só invalida se a assinatura estiver
    errada). Removido `TOKEN_MAX_AGE` e o tratamento de `SignatureExpired` (não tem mais
    como ser levantado sem `max_age`).
  - `pessoas/views.py::cadastro_publico` trocou `.exclude(status=CONCLUIDO)` por
    `.filter(status=RECRUTANDO)` — a mensagem de erro pro visitante ("Este projeto não está
    mais recebendo cadastros") já servia pra esse caso, não precisou mudar.
  - `projetos/views.py::gerar_link` e `templates/projetos/link.html` perderam a menção a
    "válido por X horas" e ganharam um aviso visível pro operador quando o projeto **não**
    está "Recrutando" no momento de gerar o link (ex.: "Este projeto está com status 'Em
    campo' — o link só aceita cadastros enquanto o status for 'Recrutando'") — sem isso a
    pessoa geraria um link morto sem saber por quê.
  - Testado com Playwright: link funcionando normalmente com o projeto em "Recrutando";
    mudei o status pra "Em campo" na marra (via shell, sem passar pela UI) e confirmei que o
    mesmo link passou a devolver HTTP 410 com a mensagem de indisponível — sem precisar
    gerar um link novo nem esperar nenhum prazo, a mudança de status já basta. Status do
    projeto restaurado pra "Recrutando" ao final.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/links.py`,
    `pessoas/views.py`, `projetos/views.py`, `templates/projetos/link.html`.
- **2026-08-12 (modal de avaliação "quebrado" — era cache do navegador, não bug)** — Usuário
  reportou o modal de avaliação renderizando quebrado (estrelas e rádios sem estilo nenhum,
  empilhados na página em vez de flutuar por cima). Investiguei antes de mexer em qualquer
  código: reli o CSS adicionado na rodada anterior (`.overlay`/`.modal`/`.star-rating`),
  sintaticamente correto; rodei dois testes de ponta a ponta em contexto de navegador
  **novo** (Playwright, sem histórico nenhum) — nos dois, o modal abriu certinho, com as
  estrelas alinhadas e o `getComputedStyle` confirmando `display:flex` no overlay,
  `position:absolute`/`opacity:0` nos rádios, e o `fetch` direto em `/static/css/base.css`
  trazendo o arquivo certo, já com `.star-rating` dentro. Ou seja: **o código sempre esteve
  correto** — o navegador do usuário só estava servindo uma cópia antiga do `base.css` do
  cache, porque o arquivo já tinha sido editado várias vezes nesta sessão (avaliação,
  estrelas, dashboards, formulários...) sempre na mesma URL (`/static/css/base.css`), sem
  nenhum jeito de o navegador saber que o conteúdo mudou sem um hard refresh manual.
  - Em vez de só pedir pra apertar Ctrl+Shift+R (resolve uma vez, mas o mesmo susto ia
    voltar na próxima rodada de CSS), corrigi a causa: `core/templatetags/static_v.py`
    (novo) — tag `{% static_v 'css/base.css' %}` que gruda `?v=<data de modificação do
    arquivo>` na URL. Como a URL muda sozinha toda vez que o arquivo muda, o navegador é
    obrigado a buscar a versão nova — sem precisar de `collectstatic` nem de nada manual,
    funciona liso durante o `runserver` (o `mtime` é lido do disco a cada request, e o
    projeto já roda com `DEBUG=True` localmente). Em produção (Railway, `collectstatic` +
    `ManifestStaticFilesStorage`) o arquivo já ganha hash no nome sozinho — a tag detecta
    que não encontra o caminho original via `finders.find()` nesse caso e só devolve a URL
    normal, sem duplicar cache-busting.
  - Trocado `{% static 'css/base.css' %}` por `{% static_v 'css/base.css' %}` em
    `templates/base.html` (a página logada, todas as telas) e nas 3 páginas públicas que
    carregam o CSS por conta própria (`templates/publico/cadastro.html`, `cadastro_ok.html`,
    `link_invalido.html` — não estendem `base.html` de propósito, então cada uma tem seu
    próprio `<link>`). Só o CSS por enquanto — os arquivos JS têm sido editados com bem
    menos frequência que o `base.css` nesta sessão, então não valia a pena mexer em todo
    template só por precaução; se acontecer de novo com algum JS, aplico o mesmo padrão lá.
  - Confirmado com Playwright que a URL do CSS agora sai com `?v=<timestamp>` e que o resto
    do sistema (dashboard, navegação) continua renderizando normal.
  - **Segue sem commitar.** `git status` agora também inclui `core/templatetags/
    static_v.py` (novo, com `__init__.py` do pacote), `templates/base.html`,
    `templates/publico/cadastro.html`, `cadastro_ok.html`, `link_invalido.html`
    (modificados).
- **2026-08-13 (filtros na lista de Participações: nome, projeto, etapa e nota)** — A tela
  `/participacoes/` já aceitava `?projeto=`/`?etapa=`/`?status=` na URL desde a implantação
  original, mas nenhuma UI de filtro nunca chegou a ser desenhada no template — os
  parâmetros existiam só de "curto-circuito" sem barra de busca nenhuma na tela. Pedido do
  usuário: adicionar filtro por nome, projeto, etapa e nota.
  - `participacoes/views.py::lista()` ganhou um filtro por `nome`
    (`participante__nome__icontains`) e um por `nota`. O filtro de nota é o mais delicado:
    `Avaliacao.nota_geral` é uma `@property` em Python (média de comunicação/pontualidade/
    repertório arredondada), não uma coluna do banco — não dá pra fazer `.filter()` direto
    nela. Resolvido anotando a mesma conta na própria queryset via `F()`:
    `.annotate(nota_media=(F("avaliacao__comunicacao") + F("avaliacao__pontualidade") +
    F("avaliacao__repertorio")) / 3.0)`. Como o Django faz LEFT JOIN pra alcançar
    `avaliacao__*` num relacionamento opcional (`OneToOneField` que pode não existir),
    participações sem avaliação viram `NULL` nos três campos e a conta inteira já sai `NULL`
    sozinha (aritmética com `NULL` em SQL sempre dá `NULL`) — não precisei de `Case`/`When`
    pra tratar esse caso à parte.
  - O filtro de nota na UI é um `<select>` no estilo "N ou mais" (`nota_media__gte=N`, N de
    1 a 5) em vez de um valor exato — como a média é sempre um número com uma casa decimal
    (ex.: "4,3"), filtrar por igualdade exata praticamente nunca bateria com nada digitado
    manualmente; "4 ou mais" é o padrão que qualquer filtro de estrelas usa (Amazon, Google
    Play etc.) e evita esse problema de vez. Tem também uma opção "Sem avaliação"
    (`avaliacao__isnull=True`) pra achar quem ainda não foi avaliado.
  - `templates/participacoes/lista.html` ganhou uma barra de filtro dentro de um
    `.panel-head` (mesmo padrão do `.search` já usado em Pessoas), com 4 campos: texto
    (nome), select de projeto (populado com `Projeto.objects.all()`), select de etapa
    (reaproveitando o `etapas` que a view já passava pro contexto) e select de nota. Um
    link "Limpar" só aparece quando algum filtro está ativo. Classe nova `.filtros` em
    `static/css/base.css` pra estilizar os `<select>` da barra (o CSS só tinha estilo pronto
    pra `<select>` dentro de `.field`, que é um formulário vertical de tela cheia — não
    servia pra uma barra horizontal compacta).
  - Testado com Playwright (login como Administradora Demo): filtro por nome, "Sem
    avaliação" (voltou só as 2 participações sem nota, todas mostrando "—"), "4 ou mais"
    (voltou só a participação com nota 4,7), e filtro por projeto (voltou só as participações
    do projeto escolhido) — todos combináveis via querystring, sem erros no console.
  - **Segue sem commitar.** `git status` agora também inclui `participacoes/views.py`,
    `templates/participacoes/lista.html`, `static/css/base.css` (modificados).
- **2026-08-13 (exportação de Participações em PDF/XLSX + preparação pra logo oficial)** —
  Pedido do usuário: baixar a lista de Participações em PDF e XLSX com todas as informações,
  "seguindo o mesmo padrão dos PDFs e XLSX de outros downloads do sistema". Busquei no
  código inteiro e não existia nenhum export em PDF/XLSX ainda em lugar nenhum (só CSV, no
  wizard de importação de participantes) — não tinha um "padrão" prévio pra seguir, então
  este vira o padrão novo, documentado aqui pra próximas exportações reaproveitarem.
  - Nenhuma lib de PDF/XLSX estava instalada. Adicionado `openpyxl==3.1.5` (planilha) e
    `reportlab==5.0.0` (PDF) no `requirements.txt` e instalados no `.venv`. `reportlab` foi
    escolhido em vez de `weasyprint`/`wkhtmltopdf` por ser Python puro — não depende de
    binário externo (GTK/Pango, etc.) instalado no sistema, o que evita dor de cabeça tanto
    no Windows local quanto no deploy no Railway.
  - `participacoes/exportacao.py` (novo) — `gerar_xlsx()` e `gerar_pdf()`, as duas recebendo
    a queryset já filtrada e um `pode_revelar_pii` (bool). Os dois formatos respeitam a
    mesma regra de mascaramento de PII que já existe no Banco de Pessoas: quem não tem a
    permissão `participantes.revelar_pii` recebe CPF/telefone/e-mail com `*_mascarado`
    (propriedades que já existiam em `Participante`) em vez do valor real — testado com
    `admin_demo` (vê tudo) e `freelancer_demo` (só vê mascarado) via download autenticado
    (`curl` com sessão de login real) + leitura do `.xlsx` gerado com `openpyxl`.
  - `participacoes/views.py::_participacoes_filtradas()` (novo, extraído de `lista()`) —
    centraliza a aplicação dos filtros de nome/projeto/etapa/status/nota, reaproveitado
    tanto pela tela quanto pela nova view `exportar(request, formato)` — o download sempre
    bate exatamente com o que está sendo visto na tela, incluindo os filtros de nota/sem
    avaliação. Rota nova: `participacoes/exportar/<formato>/` (`formato` = `pdf` ou `xlsx`),
    protegida pela mesma permissão `participacoes.ver` da lista.
  - XLSX: cabeçalho colorido (violeta da marca), largura de coluna automática por conteúdo,
    congelamento da linha de cabeçalho, e 19 colunas (todos os campos da participação,
    inclusive os 3 quesitos da avaliação separados, comentário, quem avaliou e quando).
  - PDF: paisagem A4 (`reportlab`), com título + subtítulo (data de geração e um resumo
    legível dos filtros aplicados, tipo "projeto: X; nota: 4 ou mais"), tabela com
    cabeçalho fixo repetido em toda página nova (`repeatRows=1`) e rodapé com número de
    página. Pra caber em paisagem sem ficar ilegível, algumas colunas foram agrupadas (ex.:
    "Nota (C/P/R → Geral)" numa coluna só, "Cidade/UF" numa coluna só) em vez de uma coluna
    por campo — o dado continua todo lá, só compactado; no XLSX isso não foi necessário
    porque planilha lida bem com muitas colunas.
  - **Logo oficial**: criado `core/relatorios.py::caminho_logo()` — resolve
    `static/img/logo.png` via `finders.find()` e devolve `None` se o arquivo não existir
    ainda, pra nenhum relatório quebrar por causa disso. O cabeçalho do PDF já está pronto
    pra usar a logo assim que o arquivo chegar (`Image(logo, ...)` ao lado do título "Qualy
    Vortice"); por enquanto cai no fallback (só o texto do título, sem imagem), confirmado
    no teste visual (renderizei o PDF gerado com PyMuPDF pra PNG e conferi visualmente).
    Ainda falta: (1) o usuário colocar o arquivo da logo em `static/img/logo.png` (ou me
    passar o caminho de onde salvou), e (2) trocar o `.brand-mark` (hoje só um `<div>`
    estilizado via CSS, sem imagem nenhuma) pela logo de verdade nos 5 lugares que usam esse
    elemento: `templates/base.html`, `templates/accounts/login.html`,
    `templates/publico/cadastro.html`, `cadastro_ok.html`, `link_invalido.html` — fica
    pendente até o arquivo chegar.
  - Testado com Playwright (login `admin_demo`): botões "⬇ PDF"/"⬇ XLSX" aparecem na barra
    de filtro da lista de Participações, e os `href` confirmam que preservam os filtros
    ativos da URL (ex. `?nota=4` no link vira `exportar/pdf/?nota=4`). Download real via
    `curl` autenticado pros dois formatos, `Content-Disposition: attachment` e
    `Content-Type` corretos nos dois, conteúdo verificado (abrindo o `.xlsx` com `openpyxl`
    e renderizando o `.pdf` em imagem com PyMuPDF).
  - **Segue sem commitar.** `git status` agora também inclui `requirements.txt`,
    `core/relatorios.py` (novo), `participacoes/exportacao.py` (novo),
    `participacoes/views.py`, `participacoes/urls.py`, `templates/participacoes/lista.html`
    (modificados).
  - Ajuste rápido a pedido do usuário: a coluna "Nota (C/P/R → Geral)" do PDF ganhou uma
    linha de legenda logo acima da tabela ("Comunicação / Pontualidade / Repertório → nota
    geral") — a sigla sozinha no cabeçalho da coluna não é autoexplicativa. Só no PDF (no
    XLSX as três notas já vêm em colunas separadas com nome completo, não precisa).
- **2026-08-13 (filtros + exportação em Pessoas, com regras de segurança bem mais rígidas
  que em Participações)** — Pedido do usuário: filtros e download PDF/XLSX na tela de
  Pessoas, no mesmo estilo do que foi feito em Participações, mas com 3 restrições de
  segurança explícitas (preocupação dele: alguém baixar a base inteira e vazar isso por
  falha de segurança): (1) nenhuma informação sensível no download, (2) máximo de 50 pessoas
  por download, (3) 1 download a cada 12h por usuário. Diferente de Participações — onde o
  export mostra CPF/telefone/e-mail se quem baixa tiver `participantes.revelar_pii` —, aqui
  a exportação **nunca** inclui esses campos, nem mascarados, pra ninguém, sem exceção.
  - **Filtros** (`templates/pessoas/lista.html` + `pessoas/views.py::_participantes_filtrados()`,
    extraído do antigo corpo de `lista()` pro mesmo motivo de Participações — reaproveitar
    entre a tela e a exportação): mantido o `q` (nome/CPF/código) que já existia, e
    adicionados `situacao`, `faixa_renda` ("classe social" na UI) e `uf`, como
    `<select>` na mesma barra `.filtros` já criada pra Participações — reaproveitando a
    classe CSS, sem estilo novo.
  - **`pessoas/exportacao.py`** (novo) — só inclui campos não sensíveis: código, nome,
    cidade/UF, idade, escolaridade, classe social, situação, última participação, data de
    cadastro e status de consentimento LGPD. Sem CPF, telefone, e-mail, forma de pagamento
    ou chave PIX — de propósito, não dá pra habilitar isso nem por permissão. `LIMITE_LINHAS
    = 50`: a queryset é fatiada (`participantes[:50]`) antes de virar arquivo, e tanto o PDF
    quanto o XLSX mostram "Mostrando 50 de N pessoa(s)" quando o total filtrado passa do
    limite, pra ficar claro que não é a base inteira.
  - **Permissão nova**: `participantes.exportar` (catálogo em `accounts/permissions.py` +
    migração de seed `accounts/migrations/0010_seed_exportar_permissoes.py`, concedida por
    padrão só a Administrador e Operador — mesma trilha das permissões `revelar_pii` e
    `gerenciar`). Aparece automaticamente no Painel de Permissões (que já lê o catálogo do
    banco, não precisou mexer na tela). Testado com `visualizador_demo` (não tem a
    permissão): os botões de download nem aparecem na tela, e acessar a URL de exportação
    direto devolve HTTP 403.
  - **Limite de 1 download a cada 12h**: `auditoria.models.DownloadRegistro` (novo model —
    usuário, tipo, quando) + `verificar_limite_download(usuario, tipo, horas=12)` e
    `registrar_download(usuario, tipo)`. O limite é por usuário **e por área** (`tipo=
    "pessoas"`), não por formato — baixar o PDF consome a mesma cota de baixar o XLSX, senão
    dava pra contornar o limite só trocando de formato. Quando bloqueado, a view redireciona
    de volta pra lista com uma mensagem de erro dizendo a data/hora exata em que a pessoa
    poderá baixar de novo, em vez de simplesmente falhar sem explicação. Testado com
    Playwright: primeiro download (XLSX) completa normalmente; segunda tentativa (PDF),
    poucos segundos depois, é bloqueada e volta pra `/participantes/` com a mensagem "Por
    segurança, exportações da base de Pessoas são limitadas a 1 a cada 12 horas...".
  - Essa restrição de segurança (sem dados sensíveis + limite de linhas + limite de tempo +
    permissão dedicada) foi aplicada só em Pessoas, por ser essa a base que o usuário
    mencionou explicitamente como preocupação. A exportação de Participações (rodada
    anterior) continua do jeito que estava — já tem sua própria trava de PII via
    `participantes.revelar_pii`, mas não tem limite de linhas nem de frequência. Vale
    considerar levar o mesmo padrão de limite de download pra lá também, numa próxima
    rodada, já que o risco de exfiltração em massa é conceitualmente o mesmo — fica
    registrado aqui como sugestão, não fiz sem o usuário pedir.
  - **Segue sem commitar.** `git status` agora também inclui `accounts/permissions.py`,
    `accounts/migrations/0010_seed_exportar_permissoes.py` (novo),
    `auditoria/models.py`, `auditoria/migrations/0002_downloadregistro.py` (novo),
    `pessoas/exportacao.py` (novo), `pessoas/views.py`, `pessoas/urls.py`,
    `templates/pessoas/lista.html` (modificados).
- **2026-08-13 (modelo de importação de participantes agora é XLSX, não CSV)** — Pedido do
  usuário: o arquivo de exemplo baixado no wizard "Importar planilha" vinha em CSV, ele
  queria em XLSX. Como o wizard depende do modelo baixado e do arquivo reenviado serem
  compatíveis, a mudança foi ponta a ponta: gerar o modelo em `.xlsx` **e** ensinar o
  upload a ler `.xlsx` — sem tirar o suporte a `.csv` que já existia, pra não quebrar quem
  já tinha um processo rodando com CSV (o import aceita os dois formatos agora).
  - `pessoas/wizard_csv.py`: `_normalizar_campo()` (novo) extrai a lógica de
    gênero/escolaridade/faixa de renda que já existia em `ler_csv()`, agora reaproveitada
    também por `ler_xlsx()` (novo, lê célula a célula com `openpyxl`). `_texto_celula()`
    (novo) trata as duas pegadinhas de ler planilha Excel com célula tipada: data vira
    `datetime.date` (não string) — convertido pra `AAAA-MM-DD` — e um CPF/CEP digitado só
    com números vira `float` (ex.: `11144477735.0`) — convertido de volta pra string sem
    casas decimais. `ler_planilha()` (novo) é o ponto de entrada único usado pela view:
    despacha pra `ler_xlsx()` ou `ler_csv()` conforme a extensão do arquivo enviado.
  - `pessoas/views.py::wizard_modelo_csv()` reescrita pra gerar `.xlsx` de verdade
    (`openpyxl.Workbook`, mesmo estilo visual dos outros relatórios: cabeçalho violeta da
    marca) em vez de `csv.writer`. As colunas CPF, CEP, Telefone e Data de nascimento saem
    com `number_format="@"` (texto) na linha de exemplo — sem isso o Excel trata como
    número e come o zero à esquerda (CEP "01000-000" viraria "1000-000" quando o usuário
    reabrisse o arquivo).
  - `pessoas/forms.py::UploadCSVForm` ganhou `clean_arquivo()` validando a extensão
    (`.xlsx` ou `.csv`; qualquer outra é rejeitada com mensagem clara) — antes o campo
    aceitava qualquer arquivo sem checagem nenhuma. `pessoas/views.py::wizard_dados_csv()`
    trocou `ler_csv()` por `ler_planilha()` e ganhou um `try/except` em volta da leitura
    (arquivo `.xlsx` corrompido ou renomeado na marra faz o `openpyxl` levantar exceção —
    antes disso não existia, porque o parser de CSV nunca lança exceção pra arquivo
    malformado, só devolve lixo).
  - Textos atualizados em `templates/pessoas/wizard_modo.html` e
    `templates/pessoas/wizard_dados_csv.html` (botão "Baixar modelo (XLSX)", instrução
    "Aceita arquivo .xlsx ou .csv").
  - Testado com Playwright: (1) baixei o modelo `.xlsx` gerado e reenviei ele mesmo pro
    upload — chegou certinho na revisão, CPF com pontuação preservada
    ("111.444.777-35", não virou número); (2) subi um `.csv` novo (formato antigo) pra
    confirmar que continua funcionando igual — também chegou OK na revisão; (3) subi um
    `.txt` qualquer — bloqueado na validação do formulário com "Envie um arquivo .xlsx ou
    .csv." antes mesmo de tentar ler o conteúdo.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/wizard_csv.py`,
    `pessoas/forms.py`, `pessoas/views.py`, `templates/pessoas/wizard_modo.html`,
    `templates/pessoas/wizard_dados_csv.html` (modificados).
- **2026-08-13 (Profissão vira tabela + dropdown, com campo de Especialidade condicional)**
  — Usuário perguntou se dava pra achar uma API grátis pra transformar o campo Profissão
  (texto livre) num dropdown. Pesquisei: não existe API pública oficial "estilo ViaCEP" pra
  isso — só a CBO (Classificação Brasileira de Ocupações, ~2.600 ocupações granulares) sem
  endpoint público mantido, e uns projetos pequenos/não-oficiais no GitHub, arriscados demais
  pra depender em produção. Perguntei ao usuário CBO completa (com busca) vs. lista curta
  curada — escolheu lista curta, mas guardada em **tabela no banco** (não hardcoded no
  código), com uma coluna indicando se a profissão tem especialidade, pra abrir um campo de
  texto livre nesse caso (ex.: Médico → Cardiologista, Professor → disciplina).
  - **`pessoas/models.py`**: `Profissao` (novo model — `nome` único, `tem_especialidade`
    bool). `Participante.profissao` deixou de ser `CharField` livre e virou
    `ForeignKey(Profissao, null=True, blank=True, on_delete=SET_NULL)`; `especialidade`
    (novo `CharField` livre, opcional) guarda o texto quando a profissão escolhida tem
    especialidade.
  - **Migração em 3 passos** (`pessoas/migrations/0004_profissao_model.py`,
    `0005_seed_profissoes.py`, `0006_participante_profissao_fk.py`) — não dava pra trocar
    `CharField`→`ForeignKey` numa `AlterField` direta (o Postgres tentaria converter texto
    tipo "Programador" pra `bigint` e quebraria). Passos: cria `Profissao` + campo
    `especialidade` → semeia ~67 profissões curadas (Saúde, Educação, TI, Direito,
    Engenharia, Administração, Comunicação, Vendas, Ofícios, Outros) → adiciona um campo FK
    temporário, casa o texto antigo de cada participante contra o nome de alguma `Profissao`
    semeada (por nome exato ou por um dicionário de apelidos comuns — "Programador" →
    "Desenvolvedor(a) de Software" etc.), remove o `CharField` antigo e renomeia o campo
    novo pro nome final. Testado: 6 dos 7 participantes de teste migraram certo; só
    "Analista" (genérico demais) ficou sem profissão — aceitável, são dados de teste.
  - **`pessoas/forms.py`**: `SelectProfissao` (novo widget) — cada `<option>` do dropdown
    ganha `data-especialidade="1"` quando aquela profissão tem especialidade (uma única
    query pra montar o conjunto de PKs, não uma por opção). `especialidade` virou parte do
    `ParticipanteForm.Meta.fields` — isso propaga automaticamente pros 3 formulários que
    herdam dele (cadastro individual, formset do wizard manual, cadastro público), sem
    precisar duplicar nada.
  - **`static/js/profissao_especialidade.js`** (novo) — mostra/esconde o campo
    Especialidade lendo o `data-especialidade` da opção selecionada. Usa delegação de
    evento e casa pelo **sufixo** do `name` (`profissao` / `-profissao`) em vez do nome
    exato, então funciona tanto no formulário simples (`name="profissao"`) quanto no
    formset do wizard manual (`name="form-0-profissao"`, `form-1-profissao`...) com o mesmo
    arquivo, sem lógica por linha. Roda também uma vez no carregamento da página (não só em
    `change`), pra já nascer certo ao editar um participante que já tem profissão com
    especialidade preenchida.
  - **Importação CSV/XLSX** (`pessoas/wizard_csv.py`): coluna nova "Especialidade" no
    modelo, logo depois de "Profissão". Texto de profissão do arquivo é casado contra
    `Profissao.objects.all()` por nome (case-insensitive, uma consulta só reaproveitada pra
    todas as linhas, não uma por célula) e vira o PK esperado pelo `ModelChoiceField`; sem
    correspondência, fica em branco (campo é opcional, não quebra a linha).
  - **Bug real pego no caminho**: `pessoas/views.py::wizard_dados_manual()` guardava
    `dict(f.cleaned_data)` inteiro na sessão — com `profissao` agora um `ModelChoiceField`,
    `cleaned_data["profissao"]` vira uma **instância** de `Profissao`, não serializável em
    JSON (a sessão do Django é salva como JSON por padrão). O código já tratava esse mesmo
    problema pra `data_nascimento` (`date` → `.isoformat()`); apliquei o mesmo padrão pra
    profissão (guarda só o `.pk`). Sem isso o wizard manual quebraria com erro 500 ao tentar
    ir pra revisão assim que alguém escolhesse uma profissão numa linha.
  - `core/dashviz.py` e `core/views.py` ajustados (`p.profissao` virou instância, não mais
    string; `select_related("profissao")` nos dois pontos que alimentam os dashboards, pra
    não gerar uma query por participante).
  - Testado com Playwright: (1) formulário Novo Participante — campo Especialidade some por
    padrão, aparece só ao escolher profissão com especialidade (testado Eletricista=não,
    Médico(a)=sim), cadastro completo salvo e exibido como "Médico(a) — Cardiologista" no
    detalhe; (2) wizard manual (formset) — toggle funciona linha a linha, independente,
    via delegação; (3) dashboards (Visão participantes e Visão por segmento) continuam
    carregando normalmente; (4) baixei o modelo XLSX atualizado (já com a coluna
    Especialidade) e confirmei via `ler_planilha()` que "Designer"/"UX/UI" resolvem
    corretamente pro PK da `Profissao` e pro texto livre, respectivamente.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/models.py`,
    `pessoas/migrations/0004_profissao_model.py`, `0005_seed_profissoes.py`,
    `0006_participante_profissao_fk.py` (novos), `pessoas/forms.py`, `pessoas/views.py`,
    `pessoas/wizard_csv.py`, `core/dashviz.py`, `core/views.py`,
    `static/js/profissao_especialidade.js` (novo), `templates/pessoas/form.html`,
    `templates/pessoas/detalhe.html`, `templates/pessoas/wizard_dados_manual.html`,
    `templates/pessoas/wizard_dados_csv.html`, `templates/publico/cadastro.html`
    (modificados).
- **2026-08-13 (projeto: remove "Perfil desejado" do formulário, adiciona campo Marca)** —
  Pedido do usuário: tirar a seção "Perfil desejado" (idade/gênero/região/renda/critérios
  livres) do cadastro/edição de projeto — "não faz sentido agora" pra prática atual — e
  adicionar um campo Marca ao lado de Cliente (ex.: Cliente "Agência XPTO", Marca
  "Adidas").
  - `projetos/forms.py`: removidos `perfil_idade_min`, `perfil_idade_max`, `perfil_genero`,
    `perfil_regiao`, `perfil_renda`, `perfil_criterios_livres` do `Meta.fields` (e seus
    labels/widgets) do `ProjetoForm`; adicionado `marca`.
  - `templates/projetos/form.html`: removido o `<fieldset>` inteiro "Perfil desejado"; campo
    Marca entra na primeira linha do fieldset "Dados da pesquisa", ao lado de Cliente.
    Subtítulo da página ("Defina a pesquisa e o perfil de participantes desejado") virou só
    "Defina a pesquisa".
  - **Decisão consciente**: os campos `perfil_*` **continuam existindo no model e no
    banco** — só saíram do formulário e não são mais editáveis. Rodar uma migração pra
    apagar essas colunas seria uma ação mais destrutiva e difícil de reverter do que o que
    foi pedido (que foi especificamente sobre a *tela* de cadastro/edição); manter as
    colunas é reversível sem custo (não têm efeito nenhum enquanto ninguém as usa) — se
    algum projeto antigo já tinha esses dados preenchidos, `templates/projetos/lista.html`
    continua mostrando o resumo (`perfil_resumo`) normalmente pra ele, só não aparece mais
    pra projetos novos/editados.
  - `projetos/models.py`: campo novo `marca` (`CharField`, opcional). Migração
    `projetos/migrations/0003_add_marca.py`.
  - Exibição de `marca` adicionada ao lado de `cliente` em
    `templates/projetos/detalhe.html` (subtítulo do cabeçalho) e
    `templates/projetos/lista.html` (badge e subtítulo do card) — nos dois casos só
    aparece quando preenchida (`{% if proj.marca %}`), formato "Cliente — Marca".
  - Testado com Playwright: formulário Novo Projeto sem o fieldset "Perfil desejado",
    campo Marca visível ao lado de Cliente; projeto criado com Cliente "Agência XPTO" e
    Marca "Adidas" mostrou "Agência XPTO — Adidas" tanto no detalhe quanto no card da
    lista; sem erros de console.
  - **Segue sem commitar.** `git status` agora também inclui `projetos/models.py`,
    `projetos/forms.py`, `projetos/migrations/0003_add_marca.py` (novo),
    `templates/projetos/form.html`, `templates/projetos/detalhe.html`,
    `templates/projetos/lista.html` (modificados).
- **2026-08-13 (mudança grande: Perfil — participante agora se associa a um Perfil dentro do
  projeto, não mais ao projeto direto)** — Pedido do usuário: um projeto passa a ter de 1 a
  N perfis (ex.: "Mulheres 18-25", "Homens 25-40"), cada perfil com seu próprio formulário, e
  é o perfil — não mais o projeto — que recebe os participantes. Pedido explícito pra
  atualizar todos os pontos que hoje comunicam participante↔projeto: cadastro/edição de
  projeto, associação manual de pessoa, link de captação + formulário de cadastro externo, e
  uma feature nova (associação em lote via Excel). Por ser uma mudança grande (schema,
  formulários, telas públicas), passei por **modo de planejamento** antes de codar — plano
  salvo em `C:\Users\Lucas\.claude\plans\smooth-wondering-thunder.md` — e confirmei 2
  decisões de design com o usuário antes de começar: (1) lote via Excel = escolher 1 perfil
  na tela + planilha só com coluna CPF (não uma planilha mista com coluna "Perfil" por
  linha); (2) link de captação = 1 link por perfil (não 1 link por projeto com escolha de
  perfil na página pública).
  - **`projetos/models.py`**: `Perfil` (novo — `projeto` FK, `nome`, `formulario` FK pra
    `formularios.Formulario` **por string** — `"formularios.Formulario"` em vez de import
    direto, porque `formularios/models.py` já importa `Projeto` daqui; importar `Formulario`
    de volta criaria ciclo). `Projeto.ocupadas` deixou de ser `self.participacoes.count()`
    (reverse FK direto, que não existe mais) e virou uma agregação:
    `Participacao.objects.filter(perfil__projeto=self).count()`.
  - **`ProjetoFormulario` removido** (M2M projeto↔formulário, superado pelo `Perfil.
    formulario` — cada perfil agora carrega só um formulário): `formularios/models.py`
    (model), `formularios/forms.py` (`FormularioSelecaoForm`/`montar_formset_formularios`/
    `sincronizar_formularios_projeto`), `formularios/views.py` (view `projeto_formularios`,
    guard de `responder_formulario` trocado de `ProjetoFormulario.objects.filter(...)` pra
    `participacao.perfil.formulario_id == formulario.pk`), `formularios/urls.py`,
    `templates/formularios/projeto_formularios.html` (apagado). Perfis não entram no
    formulário de *criação* do projeto — são geridos depois, na tela de detalhe do projeto
    já salvo (mesmo padrão de Formulário/Variável, que também são CRUD à parte).
  - **Migração em 2 apps, 6 arquivos** (mesmo padrão da conversão de `Participante.
    profissao` pra FK, feita antes nesta sessão — não dava pra trocar `Participacao.projeto`
    por `Participacao.perfil` numa tacada só):
    1. `projetos/migrations/0004_perfil.py` — cria `Perfil`.
    2. `projetos/migrations/0005_seed_perfis.py` — pra cada `Projeto` existente, cria um
       `Perfil(nome="Perfil único")`; se o projeto já tinha `ProjetoFormulario`, o
       formulário de menor `ordem` vira o formulário desse perfil.
    3. `formularios/migrations/0005_remove_projetoformulario.py` — apaga `ProjetoFormulario`
       (depende da migração 2, que já leu os dados de lá antes).
    4. `participacoes/migrations/0003_add_perfil_fk.py` — adiciona `perfil` (nulo) ao lado
       do `projeto` antigo.
    5. `participacoes/migrations/0004_migrar_projeto_para_perfil.py` — RunPython copia
       `projeto_id` → `perfil_id` (via o "Perfil único" de cada projeto).
    6. `participacoes/migrations/0005_finalizar_perfil_fk.py` — remove `projeto`, `perfil`
       vira obrigatório, troca a constraint `uniq_participante_projeto` por
       `uniq_participante_perfil` (fields `participante`+`perfil` em vez de
       `participante`+`projeto`) — **decisão**: a unicidade passou a ser por perfil, não
       mais por projeto inteiro, então agora o mesmo participante pode estar em mais de um
       perfil do mesmo projeto (não tinha motivo pra continuar bloqueando isso).
    `makemigrations --check --dry-run` limpo depois de escrever as 6 migrações à mão — igual
    da última vez, confirma que bateram exatamente com o `models.py` final. Rodei `migrate`
    contra o banco de verdade: os 3 projetos de teste ganharam seu "Perfil único" (2 deles já
    herdaram o "Formulário de Teste" que tinham via `ProjetoFormulario`) e as 3 participações
    existentes foram todas realocadas certinho pro perfil certo (conferido linha a linha).
  - **Associação manual** (`participacoes:nova`): `ParticipacaoForm.projeto` virou `.perfil`
    (mostra "Projeto — Perfil" no dropdown via `Perfil.__str__`, sem precisar de select em
    cascata por JS). View aceita `?perfil=<id>` pra pré-selecionar, usado pelo botão
    "Associar pessoa" na tela do perfil. `pessoas/forms.py::EscolherProjetoWizardForm` (o
    "associar os novos participantes a" do wizard de importação) seguiu o mesmo caminho.
  - **Link de captação + cadastro público, 1 por perfil**: `pessoas/links.py::
    gerar_token_captacao` trocou a chave `projeto_id` por `perfil_id` no payload assinado.
    `pessoas/views.py::cadastro_publico` carrega o `Perfil` (não mais o `Projeto` direto) e
    renderiza **no máximo um** formulário dinâmico (`_form_dinamico_do_perfil`, que substitui
    `_forms_dinamicos_do_projeto` — antes um projeto podia ter vários formulários, agora um
    perfil tem no máximo um; a função continua devolvendo uma lista de 0 ou 1 item só pra não
    precisar mexer no `{% for %}` do template). `projetos:gerar_link` (nível projeto) saiu;
    entrou `projetos:perfil_link` (nível perfil) — o botão "Link de cadastro" que ficava no
    cabeçalho do projeto agora fica em cada linha do painel "Perfis".
  - **Associação em lote via Excel** (feature nova): `projetos/perfil_lote.py` —
    `ler_cpfs()` (lê `.xlsx`/`.csv` com uma coluna "CPF", reaproveitando a mesma lógica de
    decodificação multi-encoding de `pessoas/wizard_csv.py`) e `associar_cpfs()` (casa cada
    CPF contra `Participante` — mesma técnica de `pessoas/views.py::_cpf_ja_cadastrado`,
    `annotate` removendo pontuação do CPF salvo — e faz `get_or_create` de `Participacao`
    pra cada um que bater). Sem fluxo de revisão em 2 passos (é gente que já existe, não tem
    campo pra validar) — processa direto e mostra um resumo (N associados agora, N já
    estavam, N CPFs não encontrados). Tela nova `projetos/perfis/<id>/associar-lote/`,
    reaproveitando `pessoas.forms.UploadCSVForm` pro upload (mesma validação de extensão já
    usada lá) em vez de duplicar a classe.
  - **Permissões**: nenhum código novo — CRUD de Perfil usa `projetos.gerenciar` (mesma do
    Projeto, perfil é sub-entidade dele); associar pessoa (individual ou em lote) usa
    `participacoes.mover_etapa` (mesma que já protegia `participacoes:nova`).
  - Telas/templates tocados por causa do `.projeto` → `.perfil.projeto` em Participacao:
    `templates/participacoes/lista.html` (+ coluna Perfil), `kanban.html`, `detalhe.html`,
    `templates/pessoas/detalhe.html` (+ coluna Perfil), `templates/formularios/
    responder_formulario.html`, `core/dashviz.py` (query de segmento no dashboard),
    `participacoes/exportacao.py` (+ coluna Perfil no PDF e XLSX).
  - Templates novos: `templates/projetos/perfil_form.html`, `perfil_detalhe.html`,
    `perfil_excluir.html`, `perfil_link.html` (substitui o antigo `link.html`, apagado),
    `perfil_associar_lote.html`. `templates/projetos/detalhe.html` trocou o painel
    "Formulários associados" por um painel "Perfis" (nome, formulário, participantes, e por
    linha: Link · Editar · Ver); `templates/projetos/form.html` perdeu o fieldset de
    formulários.
  - Testado com Playwright, ponta a ponta: (1) projeto existente mostrando o "Perfil único"
    migrado; (2) criado um 2º perfil ("Perfil B - Homens 25-40") com formulário associado;
    (3) gerado o link desse perfil, aberto numa aba anônima nova — carregou o formulário
    certo (inclusive os campos dinâmicos), cadastro concluído criou a `Participacao` presa
    ao perfil certo (confirmado no banco) e a `RespostaFormulario` foi salva; (4) associação
    manual de participante ao perfil via `?perfil=` pré-selecionado; (5) associação em lote:
    subi 3 CPFs válidos + 1 inexistente, resumo bateu (3 associados, depois reenviando: 0
    novos/3 já estavam/1 não encontrado — confirma idempotência); (6) dashboards (Visão
    participantes e Visão por segmento) continuam carregando; (7) exportação de
    Participações confirmada com a coluna Perfil certa; (8) tentativa de excluir o
    formulário em uso por perfis continua bloqueada (`ProtectedError`, formulário não foi
    apagado). Zero erros de console em todo o percurso.
  - **Segue sem commitar.** `git status` agora também inclui `projetos/models.py`,
    `projetos/forms.py`, `projetos/views.py`, `projetos/urls.py`, `projetos/admin.py`,
    `projetos/perfil_lote.py` (novo), `projetos/migrations/0004_perfil.py`,
    `0005_seed_perfis.py` (novos), `participacoes/models.py`, `participacoes/forms.py`,
    `participacoes/views.py`, `participacoes/admin.py`, `participacoes/exportacao.py`,
    `participacoes/migrations/0003_add_perfil_fk.py`, `0004_migrar_projeto_para_perfil.py`,
    `0005_finalizar_perfil_fk.py` (novos), `formularios/models.py`, `formularios/forms.py`,
    `formularios/views.py`, `formularios/urls.py`,
    `formularios/migrations/0005_remove_projetoformulario.py` (novo), `pessoas/links.py`,
    `pessoas/views.py`, `pessoas/forms.py`, `core/dashviz.py`, e os templates listados acima
    (modificados/novos/apagados).
- **2026-08-13 (wizard "Novos participantes (lote)" ganha as perguntas do formulário do
  perfil)** — Usuário reportou que não estava mais "sendo possível associar em lote como
  antes". Investigando com uma pergunta de esclarecimento, não era a feature nova de
  associação em lote (essa já existia e funciona, testada na rodada anterior) — era o wizard
  de importação de participantes novos (`Banco de Pessoas` → `Novos participantes (lote)`):
  o modelo de planilha baixado ali só trazia os campos fixos do participante (nome, CPF,
  etc.), nunca trouxe as perguntas do formulário — só que antes da mudança de Perfil isso não
  chamava tanto a atenção porque o formulário do projeto não era o foco principal do wizard;
  agora que cada perfil tem seu próprio formulário e o wizard já pergunta "associar a qual
  perfil" logo no passo 1, ficou claro que faltava trazer as perguntas desse formulário pro
  modelo/planilha também — pedido do usuário pra completar isso.
  - `pessoas/wizard_csv.py`: `variaveis_do_formulario()` (mesma consulta ordenada que
    `formularios/respostas.py::construir_form_resposta` já usa), `_exemplo_variavel()`
    (valor de exemplo por tipo — opção cadastrada pra select/radio, "Sim" pra booleano, data
    fixa, etc.), `_normalizar_valor_dinamico()` (só booleano e select/radio/múltipla escolha
    precisam de normalização — texto/número/data passam direto, o próprio campo do
    formulário dinâmico valida), `_mapa_variaveis()` (nome da variável → `Variavel`, pra
    casar cabeçalho da planilha) e `_normalizar_cabecalho()`. `ler_csv()`/`ler_xlsx()`/
    `ler_planilha()` ganharam um parâmetro `formulario=None` opcional — quando presente,
    colunas que não são nenhum campo fixo conhecido são testadas contra o nome das variáveis
    do formulário.
  - **Bug pego no meio do caminho**: o cabeçalho do modelo marca pergunta obrigatória com um
    `" *"` no final (ex.: "Nome Completo *"), mas a primeira versão do casamento de coluna
    comparava esse texto (com asterisco) direto contra o nome puro da variável — nunca
    batia, então nenhuma resposta dinâmica era lida de volta mesmo com a coluna certinha
    preenchida. Corrigido com `_normalizar_cabecalho()`, que tira o `" *"` antes de comparar.
    Só percebi isso testando de ponta a ponta (baixei o modelo, preenchi, subi de novo) —
    sem esse teste real o bug passaria despercebido.
  - **Limitação percebida durante o teste** (não é bug, é dado de teste ambíguo): o
    "Formulário de Teste" já cadastrado no sistema tem variáveis literalmente chamadas
    "Nome Completo" e "Data de Nascimento" (criadas em uma rodada bem anterior desta sessão,
    de propósito, pra testar que o formulário público mostra os campos fixos E os dinâmicos
    lado a lado mesmo com nome parecido). Como esses nomes colidem com os sinônimos que o
    wizard já reconhece pros campos fixos (`"nome completo"` → `nome`, `"data de
    nascimento"` → `data_nascimento`), essas duas colunas específicas continuam sendo lidas
    como os campos fixos, não como a pergunta do formulário — o campo fixo tem prioridade de
    propósito (é mais crítico não perder CPF/nome do que resolver uma colisão de nome rara).
    Confirmei que o mecanismo em si funciona certinho testando com um formulário à parte,
    com nomes de pergunta que não colidem ("Aceita viajar", "Anos de experiência") — a
    planilha baixada trouxe as duas colunas extras, e reenviando preenchida, criou o
    participante, a participação no perfil certo e a `RespostaFormulario` com os valores
    certos (`{'aceita_viajar': True, 'anos_de_experiencia': '5'}`).
  - `pessoas/views.py`: `_perfil_e_formulario_do_wizard(estado)` (novo helper, resolve
    `Perfil`/`Formulario` a partir da sessão do wizard, reaproveitado por 3 views);
    `_validar_linha_csv()` ganhou um parâmetro `formulario` opcional — quando presente,
    também valida as respostas dinâmicas via `construir_form_resposta()` e mistura os erros
    (usando o nome da pergunta, não a chave interna, pra ficar legível na tela de revisão).
    `wizard_modelo_csv()` acrescenta as colunas do formulário do perfil (se tiver) no
    cabeçalho/linha de exemplo da planilha baixada. `wizard_revisao()` (POST de
    confirmação): só aplica a validação/gravação de respostas dinâmicas pra linhas vindas da
    planilha (`estado["modo"] == "CSV"`) — o formset de cadastro manual não tem campo
    nenhum pra essas perguntas, então não faz sentido (nem seria possível) exigi-las por
    ali; ao criar a `Participacao`, também grava a `RespostaFormulario` correspondente,
    igual ao que `cadastro_publico` já faz pro cadastro externo.
  - `templates/pessoas/wizard_dados_csv.html`: aviso novo (só aparece quando o perfil
    escolhido tem formulário) avisando que o modelo já vem com as perguntas dele.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/wizard_csv.py`,
    `pessoas/views.py`, `templates/pessoas/wizard_dados_csv.html` (modificados).
- **2026-08-13 (revisão do wizard vira editável + upsert por CPF/e-mail/telefone em todo
  fluxo de cadastro)** — Dois pedidos do usuário nascidos da mesma captura de tela (a tela
  de revisão do wizard cheia de "Erro"): (1) dar um jeito de corrigir os dados errados **na
  própria tela** de revisão, em vez de só rejeitar a linha; (2) em **qualquer** fluxo de
  cadastro de pessoa (form interno, cadastro público, wizard em lote), se o CPF, e-mail ou
  telefone já bater com alguém cadastrado, **atualizar** esse registro em vez de duplicar ou
  travar com "já existe". Por mexer com integridade de dado (sobrescrever PII de gente já
  cadastrada é arriscado se a régua de casamento for ruim), perguntei antes de codar:
  - **Prioridade em caso de conflito** (CPF aponta pra uma pessoa, telefone aponta pra
    outra): confirmado — **CPF manda** (é o único campo com unicidade garantida no banco
    hoje); e-mail/telefone só entram como reforço quando o CPF não veio ou não bateu com
    ninguém. Evita fundir duas pessoas que só dividem um telefone de família.
  - **Como atualizar**: confirmado — **só preenche o que veio preenchido**. Campo vazio na
    submissão nova não apaga o que já estava salvo.
  - **`pessoas/matching.py`** (novo módulo) — `encontrar_participante_existente(cpf, email,
    telefone)` (CPF primeiro via o mesmo `Replace()`-encadeado já usado antes pra CPF;
    telefone usa a mesma técnica removendo `(`, `)`, espaço e `-`), `CAMPOS_ATUALIZAVEIS`
    (lista dos campos "de perfil" que um upsert pode tocar — **não** inclui `codigo`
    (gerado), `situacao` (uma nova submissão não pode desfazer uma triagem já feita),
    `consentimento_*`/`origem_recrutador` (efeito legal/de atribuição — cada fluxo decide
    isso por conta própria) nem campos de auditoria), `capturar_valores_atuais()` +
    `restaurar_campos_vazios()` (tira uma "foto" do participante antes de aplicar o form
    novo em cima, e depois devolve pro valor antigo qualquer campo que veio vazio —
    implementa a regra "só preenche o que veio preenchido" sem depender do `ModelForm.save()`
    puro, que sobrescreveria tudo incondicionalmente).
  - **`pessoas/views.py::novo()`**: antes de validar o form, tenta achar um participante
    existente com o CPF/e-mail/telefone enviado; se achar, o `ParticipanteForm` é ligado a
    essa instância (`instance=existente`) em vez de criar uma nova — isso também resolve de
    graça a validação de unicidade de CPF (o Django já sabe excluir a própria instância da
    checagem). Mensagem de sucesso muda pra "já estava cadastrado(a) — dados atualizados"
    nesse caso.
  - **`pessoas/views.py::cadastro_publico()`**: mesmo mecanismo, com dois cuidados a mais
    específicos do cadastro público (decisão própria, não perguntada ao usuário mas
    conservadora de propósito): reenviar o formulário público não reseta a `situacao` de
    alguém que já foi triado (só cadastro novo entra como "Pendente") e não troca o
    `origem_recrutador` original (preserva quem indicou a pessoa da primeira vez).
  - **Wizard em lote** (`_validar_linha_csv`, `wizard_dados_manual`, `wizard_revisao`): toda
    linha (venha de planilha ou do formset manual) passa a carregar `existente_pk`/
    `existente_codigo` — a tela de revisão mostra um selo "Atualiza P-2026-00XX" (azul) ou
    "Novo" (violeta) por linha. `wizard_revisao()` (POST de confirmação) foi reescrito por
    completo: em vez de simplesmente contar "criados"/"pulados" e descartar quem falhou,
    agora processa linha a linha e **separa** o que deu certo (cria ou atualiza, conforme o
    caso) do que ainda precisa de ajuste — essas ficam guardadas de volta na sessão (com os
    dados e erros atualizados) e a página **re-renderiza no mesmo lugar**, em vez de jogar
    tudo fora; só limpa a sessão e volta pra lista quando não sobra nenhuma linha problemática.
  - **Correção inline** (o pedido nº1): linha com erro ganha um mini-formulário logo abaixo,
    usando o próprio `ParticipanteWizardForm` (mesmo do cadastro manual — reaproveita todos
    os widgets, inclusive o dropdown de Profissão com o toggle de Especialidade) com
    `initial=` pré-preenchido e um `prefix=f"dados_{indice}"` — cada campo vira um `<input
    name="dados_0-cpf">` etc., isolado por linha. No POST, `wizard_revisao()` procura essas
    chaves (`dados_<indice>-<campo>`) antes de revalidar; se existirem, sobrescrevem o valor
    que a planilha original tinha trazido pra aquela linha. Escopo: só os campos fixos do
    participante — as perguntas do formulário dinâmico do perfil (do round anterior) ainda
    aparecem como erro em texto, não editáveis nesta rodada (a planilha continua sendo o
    jeito de corrigi-las).
  - **Limitação conhecida, não corrigida agora**: o formset do "Cadastro manual" (uma das
    duas formas de chegar no wizard) valida CPF duplicado **antes** de chegar em
    `wizard_revisao` (é campo `unique=True` no model, e o formset não liga cada linha a uma
    instância existente) — então, só pra esse caminho específico, um CPF já cadastrado ainda
    trava na própria tela de "Cadastro manual" em vez de virar atualização. O caminho por
    planilha (o mais comum pra lote) e os fluxos de formulário único (`novo`,
    `cadastro_publico`) já cobrem os três campos (CPF/e-mail/telefone) sem essa limitação.
  - Testado com Playwright: (1) `novo()` — reenviei o CPF da Maria Teste da Silva com nome
    novo, e-mail em branco e bairro preenchido: atualizou o registro dela (mesmo pk),
    manteve o e-mail antigo intocado, preencheu o bairro, sem duplicata; (2)
    `cadastro_publico()` — reenviei o CPF do Bruno Wizard Teste (que eu tinha marcado como
    "Aprovado" antes do teste) pelo link público: nome e telefone atualizados, `situacao`
    continuou "Aprovado" (não voltou pra "Pendente"), e-mail antigo preservado; (3) wizard
    por planilha — subi uma linha sem data de nascimento (erro) e uma com CPF já cadastrado
    (vira "Atualiza"): a linha com erro apareceu com o mini-formulário editável, preenchi a
    data que faltava ali mesmo e cliquei "Concluir importação" de novo — as duas linhas
    processaram na segunda tentativa (uma criação, uma atualização; confirmado no banco);
    (4) reconfirmei que uma planilha só com gente nova, sem nenhum casamento, continua
    criando normalmente, sem regressão no caminho mais comum. Zero erros de console.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/matching.py` (novo),
    `pessoas/views.py`, `templates/pessoas/wizard_revisao.html` (modificados).
- **2026-08-13 (wizard em lote ganha recrutador escolhível + modo "lote legado" tolerante) —
  e um bug de fundo do round anterior corrigido de brinde)** — Pedido do usuário: (1) na
  primeira tela do wizard em lote, poder escolher qual usuário cadastrado vira o recrutador
  responsável pelo lote, assumindo quem está subindo o arquivo como padrão se deixar em
  branco; (2) um botão "lote legado" pra planilhas de projetos já concluídos, enviadas só
  pra preencher o Banco de Pessoas — esses lotes aceitam os dados como vierem (sem exigir
  campo obrigatório completo nem travar por formato), só continuando a checar duplicidade de
  pessoa (CPF/e-mail/telefone, do round anterior) pra não criar gente repetida.
  - **Pergunta feita antes de codar**: vários campos do `Participante` são obrigatórios no
    banco (`data_nascimento`, `telefone`, `uf`, `cidade`) — não dá pra simplesmente deixar em
    branco num lote legado sem violar a constraint. Confirmado com o usuário: preencher com
    um valor de preenchimento ("Não informado"/data-marcador), e marcar esses registros com
    uma flag pra pedir a atualização de volta pra pessoa no futuro.
  - **`pessoas/models.py`**: `cpf` passa a `null=True` (mantendo `unique=True`) — decisão
    técnica não pedida explicitamente, mas necessária: cogitei usar `""` como valor de
    preenchimento pro CPF ausente (mesmo padrão do telefone/UF/cidade), mas o Postgres trata
    duas strings vazias como iguais sob `UNIQUE`, então o segundo lote legado sem CPF
    quebraria a importação; `NULL` não colide com `NULL` sob `UNIQUE`, resolve sem gambiarra.
    `cpf_mascarado` blindado contra `None` (`"—"` em vez de erro). Campo novo
    `cadastro_incompleto` (booleano, `default=False`) — marca quem tem algum dado de
    preenchimento em vez do dado real. Migração `0007_lote_legado.py` (auto-gerada, já
    aplicada).
  - **`pessoas/matching.py`** ganha a lógica de leniência: `preparar_linha_legado(dados)`
    (valida só o mínimo — nome não pode faltar, e precisa de pelo menos um entre CPF/e-mail/
    telefone pra dar pra conferir duplicidade; qualquer outro campo obrigatório ausente vira
    um valor de preenchimento e entra no conjunto `campos_incompletos`, devolvido separado)
    e `aplicar_dados_legado(participante, dados, campos_incompletos, existente,
    valores_originais)` (grava direto no objeto, sem passar pelo `ParticipanteWizardForm` —
    não faz sentido validar contra regras que o próprio modo legado existe pra ignorar).
    **Cuidado de design pego antes de implementar**: se um lote legado atualizasse (upsert)
    uma pessoa que já tinha, por exemplo, data de nascimento real cadastrada, o valor de
    preenchimento (1900-01-01) não podia se passar por "dado novo preenchido" e sobrescrever
    o dado real — por isso `aplicar_dados_legado` força os campos de `campos_incompletos`
    a parecerem vazios antes de chamar `restaurar_campos_vazios()` (do round anterior),
    garantindo que placeholder nunca vence dado real já salvo. `cadastro_incompleto` é
    recalculado (`bool(campos_incompletos)`) toda vez — se uma atualização futura vier com o
    dado que faltava, a flag se limpa sozinha.
  - **`pessoas/forms.py::EscolherProjetoWizardForm`**: campo novo `recrutador`
    (`ModelChoiceField` sobre `Usuario` ativos, `empty_label="Eu mesmo(a) — quem está
    enviando este lote"`) e `legado` (`BooleanField`, `required=False`). A exclusão de
    projetos concluídos do dropdown de perfil foi removida — lote legado existe justamente
    pra apontar pra perfis de projetos já concluídos.
  - **`pessoas/views.py`**: `wizard_projeto()` grava `recrutador_id`/`legado` na sessão;
    `_validar_linha_csv(dados, formulario=None, legado=False)` desvia pro caminho de
    `preparar_linha_legado()` quando `legado=True`; `wizard_revisao()` ganhou um branch
    completo — modo legado chama `preparar_linha_legado`/`aplicar_dados_legado` direto (sem
    `ParticipanteWizardForm`), modo normal continua no caminho estrito do round anterior; em
    ambos, ao criar (não atualizar) participante, `origem_recrutador` vira o recrutador
    escolhido na tela 1 (ou `request.user`, se deixado em branco). `_participantes_filtrados()`
    ganhou o filtro `?incompleto=1`.
  - **Bug crítico achado durante o teste, não introduzido nesta rodada** (afeta também a
    correção inline do round anterior): testando o botão "Concluir importação" com uma linha
    ainda em erro, o clique **não fazia nada** — sem mensagem, sem navegação, zero erro no
    console. Isolei em duas etapas: (1) simulei o mesmo POST direto via `test.Client()` do
    Django (sem navegador) e funcionou perfeitamente — o problema não era a view; (2) coloquei
    listener de `request`/`response` no Playwright e confirmei que **nenhuma requisição saía
    do navegador** ao clicar. Causa: a tela de revisão desenha um mini-formulário de correção
    por linha inválida, com atributos `required` nativos do HTML5 (nome, CPF, data de
    nascimento, telefone, UF, cidade); ao tentar submeter o formulário inteiro deixando OUTRA
    linha (que o usuário não estava mexendo) com esses campos vazios, o **próprio navegador**
    bloqueia o submit da página inteira silenciosamente, antes de qualquer request sair —
    sem erro de console, sem rede. Corrigido com `novalidate` no `<form>` de
    `wizard_revisao.html`, já que a validação do lado do servidor (Django) sempre foi a
    autoridade de fato. Esse bug já existia desde a correção inline do round anterior — só
    não tinha sido pego porque os testes de lá sempre corrigiam a única linha problemática da
    página antes de submeter.
  - `templates/pessoas/wizard_projeto.html`: campos `recrutador` e `legado` (com
    `help_text`) somados ao `perfil`. `templates/pessoas/wizard_dados_csv.html`: aviso
    exibido só quando `legado` está marcado, explicando a leniência. `wizard_revisao.html`:
    banner "Lote legado" no topo quando aplicável, badge "Dado incompleto" (âmbar) por linha
    válida com `cadastro_incompleto=True`, coluna "Situação" com selo "Atualiza <código>"
    (azul) ou "Novo" (violeta) por linha (do round anterior, mantido). `lista.html`: filtro
    "Só cadastro incompleto" e badge "Incompleto" ao lado do nome na tabela.
    `detalhe.html`: aviso explicando o que fazer quando `cadastro_incompleto=True`.
    `pessoas/exportacao.py`: coluna "Cadastro" (Completo/Incompleto) no PDF e no XLSX.
  - Testado com Playwright: (1) upload de lote legado com linhas sem telefone/UF/cidade/data
    de nascimento — nenhuma virou "Erro", todas processaram na primeira tentativa, e as que
    ficaram com valor de preenchimento apareceram com o badge "Dado incompleto" na revisão e
    "Incompleto" na lista; (2) reenviei o CPF de uma pessoa já cadastrada dentro do mesmo
    lote legado — virou atualização ("Atualiza <código>"), não duplicata; (3) deixei o campo
    recrutador em branco — `origem_recrutador` do participante criado ficou sendo o próprio
    usuário logado que subiu o arquivo; escolhi um recrutador explícito num segundo teste —
    ficou registrado esse outro usuário; (4) filtro `?incompleto=1` na lista trouxe só os
    registros esperados; (5) **regressão do bug do `novalidate`**: refiz o teste do round
    anterior (planilha não-legada com uma linha faltando data de nascimento, corrigida pelo
    mini-formulário inline) do zero — "1 participante(s) importado(s) com sucesso.", zero
    erro de console, confirmando que o `novalidate` não abriu brecha nenhuma pra dado
    inválido passar despercebido (a validação do servidor continua barrando tudo que não é
    modo legado). Participantes e planilhas de teste removidos/restaurados ao final.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/models.py`,
    `pessoas/migrations/0007_lote_legado.py` (novo), `pessoas/matching.py`,
    `pessoas/forms.py`, `pessoas/views.py`, `pessoas/exportacao.py`,
    `templates/pessoas/wizard_projeto.html`, `templates/pessoas/wizard_dados_csv.html`,
    `templates/pessoas/wizard_revisao.html`, `templates/pessoas/lista.html`,
    `templates/pessoas/detalhe.html`.
- **2026-08-13 (paginação em Pessoas/Participações + flash card de erro em qualquer
  cadastro)** — Dois pedidos do usuário: (1) paginar as listagens de Pessoas e
  Participações (10 por página) e fazer os downloads PDF/XLSX "considerarem a
  paginação"; (2) trocar o jeito como erro de campo aparece nos formulários de cadastro
  (hoje só um texto vermelho pequeno embaixo do campo, fácil de não notar num formulário
  longo) por um "flash card" — um aviso que sobe na tela deixando claro o que deu errado.
  - **Pergunta feita antes de codar**: com a lista paginada, o download deveria trazer só
    a página atual (os mesmos 10 registros da tela) ou todos os resultados filtrados,
    ignorando a página? Confirmado: **todos os filtrados, ignorando a página** — a
    paginação vale só pra navegação na tela; o relatório continua completo, igual já
    funciona hoje (e, pro Banco de Pessoas, ainda limitado a 50 por download, regra que já
    existia). "Considerar a paginação" então virou: não deixar o parâmetro `page` da URL
    contaminar o link de exportação por engano.
  - **Paginação**: `pessoas/views.py::lista()` e `participacoes/views.py::lista()` passam
    a paginar o queryset já filtrado com `django.core.paginator.Paginator` (constante
    `ITENS_POR_PAGINA = 10` em cada app), usando `paginator.get_page(request.GET.get
    ("page"))` — devolve a página pedida sem quebrar se `page` vier inválido ou fora do
    intervalo (`get_page` já trata isso, ao contrário de `.page()`). As views de
    exportação (`exportar()`) continuam usando a queryset completa (sem paginar) — só a
    tela de listagem foi paginada, o relatório baixado nunca foi tocado.
  - `core/templatetags/query_utils.py` (novo) — filtro `sem_pagina`, que reencoda
    `request.GET` tirando a chave `page`; usado tanto nos links "‹ Anterior/Próxima›" da
    paginação (pra montar `?...&page=N` sem duplicar) quanto nos links de PDF/XLSX (pra
    não herdar `page=3` de quem clicou exportando estando na 3ª página — resposta da
    pergunta acima).
  - `templates/core/_paginacao.html` (novo, `{% include %}` nas duas listagens) —
    Primeira/Anterior/Próxima/Última + "Página X de Y", sem numeração de página
    individual (decisão de simplicidade: o `{% if %}` do Django não suporta bem misturar
    `and`/`or` com precedência pra montar uma faixa de páginas com reticências tipo "1 … 4
    5 6 … 20"; como a base de dados aqui não tem volume que justifique esse refinamento,
    ficou só com o essencial).
  - `templates/pessoas/lista.html` e `templates/participacoes/lista.html`: contador do
    cabeçalho passa a usar `page_obj.paginator.count` (total real, não só o que está na
    página); `{% include "core/_paginacao.html" %}` logo abaixo da tabela; links de PDF/
    XLSX trocam `request.GET.urlencode` por `request.GET|sem_pagina`.
  - **Flash card de erro**: em vez de mexer formulário por formulário, aproveitei que
    **todo** template do sistema já renderiza erro de campo com o mesmo padrão
    `<p class="erro">{{ erro }}</p>` (18 arquivos, confirmado por busca — Participante,
    cadastro público, Usuário, Termo, Variável, Avaliação, formulário dinâmico, etc.) —
    então a solução é um único mecanismo genérico, sem tocar em nenhum desses templates:
    `static/js/flash_erros.js` roda em toda página (incluída em `base.html`, que cobre
    todo o sistema autenticado + a tela pública de cadastro que não herda de `base.html`
    e ganhou a inclusão à parte em `templates/publico/cadastro.html`); no `DOMContentLoaded`,
    procura todo `p.erro` já renderizado pelo Django, sobe **um** card fixo no canto
    superior direito juntando todos os erros da página (achando o rótulo do campo pelo
    `<label>` mais próximo, quando existe), com botão de fechar (×). Não substitui o texto
    vermelho abaixo do campo — os dois convivem, o card só chama atenção pra quem passaria
    batido. Deliberadamente **não** entra na tela de revisão do wizard em lote
    (`wizard_revisao.html`): lá os erros já aparecem numa tabela clara, linha por linha,
    com badge e mini-formulário de correção — um card flutuante juntando erro de N linhas
    ali seria barulho, não ajuda (e tecnicamente nem dispara, porque aquela tela usa
    `<li>` dentro de `<ul class="wiz-erro-lista">`, não `<p class="erro">`).
  - `static/css/base.css`: classes `.paginacao`/`.pg-nav`/`.pg-info`/`.pg-total` (mesma
    linguagem visual dos botões `.btn-ghost` já existentes) e `#flash-erros`/`.flash-card`/
    `.flash-close` (cartão branco com borda vermelha à esquerda, sombra, animação leve de
    entrada deslizando da direita — mesma paleta `--red`/`--red-soft` já usada em
    `.messages .error`).
  - **Bug de teste pego no meio do caminho, não é bug do sistema**: montando o teste de
    Playwright pro flash card, o clique em "Salvar participante" primeiro caiu direto na
    tela de login — o seletor genérico `button[type="submit"]` bateu no botão "Sair"
    (logout) da sidebar, que aparece antes no DOM. Depois, tentando desligar a validação
    nativa do navegador pra simular envio com campo faltando, `document.querySelector
    ("form")` pegou o formulário de logout (também antes no DOM) em vez do formulário do
    cadastro — então o `novalidate` foi parar no form errado e o clique continuava sem
    disparar nenhuma requisição. Corrigido escolhendo os elementos certos no teste (botão
    pelo texto "Salvar participante"; sem precisar de `novalidate` nenhum, preenchendo os
    campos obrigatórios de verdade). Nada disso é código do sistema — só uma armadilha do
    próprio script de teste, registrada aqui porque o padrão ("primeiro elemento do tipo X
    no DOM pode ser da sidebar, não do conteúdo") já se repetiu nesta sessão e vale
    lembrar da próxima vez que for escrever um teste.
  - Testado com Playwright: (1) `/participantes/` com 11 cadastros mostra 10 na página 1 e
    1 na página 2, "Página 1 de 2"/"Página 2 de 2" corretos, `?page=2` na URL; (2) mesmo
    teste em `/participacoes/`; (3) link de PDF/XLSX na página 2 de ambas as telas não
    carrega `page=` na querystring; (4) submeti o formulário de novo participante com CPF
    inválido (`111.111.111-11`) e cidade em branco: subiu 1 flash card no canto superior
    direito com "CPF: CPF inválido." e "Cidade: Este campo é obrigatório." (mesmo texto
    que já aparecia embaixo dos campos); clicar no × removeu o card; (5) confirmei que
    nenhuma página carregada sem erro (listagens, tela de novo cadastro em branco) mostra
    o card à toa — só sobe quando existe pelo menos um `p.erro` real na página. Zero
    participantes de teste sobraram no banco (as tentativas com CPF inválido nunca chegam
    a salvar) e zero erros de console em todo o percurso.
  - **Segue sem commitar.** `git status` agora também inclui `core/templatetags/
    query_utils.py` (novo), `templates/core/_paginacao.html` (novo), `static/js/
    flash_erros.js` (novo), `static/css/base.css`, `templates/base.html`,
    `templates/publico/cadastro.html`, `pessoas/views.py`, `participacoes/views.py`,
    `templates/pessoas/lista.html`, `templates/participacoes/lista.html`.
- **2026-08-13 ("Última participação" some sendo atualizada + cores por status + status
  editável direto na lista de Participações)** — Três pedidos do usuário: (1) a coluna
  "Última participação" na lista de Pessoas nunca mudava; (2) os "flags" (badges) de
  status em Participações deveriam ter cor de acordo com o status; (3) um botão suspenso
  (dropdown) pra editar o status direto na lista, sem precisar passar pelo kanban.
  - **Causa da nº1**: `Participante.data_ultima_participacao` é um campo desde o modelo
    inicial (migração `0001_initial`), mas nunca existia nenhum código que o preenchesse —
    zero atribuições no projeto inteiro além da própria declaração do campo. Sempre ficou
    `None`, daí "não atualizar" (na real, nunca chegou a atualizar nenhuma vez). Decisão de
    design (não perguntada, mas direta o bastante pra não travar nisso): "participação",
    aqui, significa participação de verdade — a pessoa fez a pesquisa e foi paga —, não só
    estar dentro do funil. `Etapa.PAGO` já é a última etapa do funil (`ETAPAS_ORDEM`) e
    representa exatamente isso, então virou o gatilho certo: `Participacao.save()` ganhou
    uma checagem — sempre que uma participação é salva com `etapa == PAGO`, o participante
    correspondente tem `data_ultima_participacao` posto pra hoje (`timezone.localdate()`).
    Fica no `save()` do model (não só dentro de `avancar_etapa()`) de propósito: cobre
    tanto quem avança pelo botão "Avançar" do kanban quanto qualquer outro jeito futuro de
    setar `etapa=PAGO` diretamente, sem duplicar a lógica.
  - **Backfill**: rodei um ajuste pontual nos dados de teste já existentes — a única
    participação já em "Pago" no banco (`Wizard Dinamico Teste`) tinha `data_
    ultima_participacao=None` porque chegou lá antes dessa lógica existir; resalvá-la
    (mesmo código, `participacao.save()`) preencheu corretamente. Não foi feita migração
    de dado — é só reprocessar os poucos registros que já estavam em Pago, mesma lógica
    que qualquer save novo vai aplicar dali pra frente.
  - **Cores por status** (pedido nº2): `Participacao.CORES_STATUS` (novo dict no model) +
    `Participacao.status_badge` (property) mapeiam cada valor de `Status` pra uma classe
    `.b-*` já existente no CSS — agrupado por "sentimento" do resultado, não 1 cor por
    valor: Aprovação (verde, positivo), Backup (azul, neutro/reserva), Desistência e Não
    aprovado (vermelho — os dois tiram a pessoa do funil por um motivo forte), Não
    compareceu (âmbar — mais leve, dá pra reagendar), Fora do perfil (cinza — nem chegou a
    ser avaliado, não é rejeição de qualidade). Aplicado tanto na lista quanto no KPI de
    Status da tela de detalhe da participação.
  - **Status editável na lista** (pedido nº3): hoje não existia NENHUM jeito de editar o
    campo `status` pela interface — nem o kanban mexe nele (kanban só avança `etapa`; quem
    quisesse mudar `status` só conseguia pelo Django admin). `participacoes/views.py::
    mudar_status(request, pk)` (novo, `POST`, permissão `participacoes.mover_etapa` — a
    mesma que já protege "Avançar" no kanban) grava o novo status e redireciona de volta
    pro `next` recebido (a própria URL da lista, com filtro e página preservados — mesmo
    padrão do botão "Avançar" do kanban, que já usa um `proximo` do mesmo jeito). Rota
    nova `participacoes/<int:pk>/status/` (`mudar_status`).
    `templates/participacoes/lista.html`: a coluna Status virou um `<form>` por linha com
    um `<select name="status">` (opção "Sem status" + as 6 opções de `Status.choices`),
    `onchange="this.form.submit()"` — funciona como um dropdown que salva sozinho ao
    escolher, sem precisar de botão "Salvar" separado. Só aparece pra quem tem
    `participacoes.mover_etapa`; sem essa permissão, cai de volta pro badge somente
    leitura (mesmo badge colorido, sem o dropdown).
  - `static/css/base.css`: classe `.status-select` estiliza o `<select>` nativo como um
    badge colorido (sem borda, cantos arredondados, seta customizada via SVG embutido em
    `data:` URI) — a cor de fundo/texto vem de continuar recebendo a mesma classe `.b-*`
    do badge (`class="status-select b-green"` etc.); funciona porque `.status-select` só
    mexe em propriedades de layout/seta (não redeclara `background-color`), então a cor
    de cada `.b-*` (que já existia) continua valendo por cima.
  - Testado: (1) via shell, forcei uma participação existente a passar por todas as
    etapas até "Pago" (mesmo método `avancar_etapa()` que o botão real usa) e confirmei
    que `data_ultima_participacao` do participante mudou pra hoje; desfiz a mudança depois
    (voltou pra "Análise de Perfil" e `data_ultima_participacao=None`, estado original);
    (2) Playwright: lista de Pessoas mostra "13 de Agosto de 2026" na linha da Wizard
    Dinamico Teste (que já estava em Pago desde antes); (3) lista de Participações mostra
    10 dropdowns de status coloridos (cinza pra quem não tem status); mudei o status de
    uma participação pra "Aprovação" pelo dropdown, confirmei mensagem de sucesso, redirect
    de volta pra mesma URL da lista, badge/select virou verde e o valor ficou selecionado
    corretamente; desfiz a mudança depois (status voltou a vazio). Zero erros de console em
    todo o percurso.
  - **Segue sem commitar.** `git status` agora também inclui `participacoes/models.py`,
    `participacoes/views.py`, `participacoes/urls.py`, `static/css/base.css`,
    `templates/participacoes/lista.html`, `templates/participacoes/detalhe.html`.
- **2026-08-13 (coluna "Pago" some do Kanban)** — Pedido do usuário: quem já foi pago não
  precisa mais aparecer no quadro do pipeline. `participacoes/views.py::kanban()` passa a
  pular `Etapa.PAGO` no loop que monta as colunas — a etapa continua existindo
  normalmente no modelo (`avancar_etapa()` intocado: de "Entrevista" ainda dá pra avançar
  pra "Pago" clicando "Avançar", só que agora, ao chegar lá, o card some do quadro em vez
  de ganhar uma 5ª coluna). `static/css/base.css`: `.board` tinha `grid-template-columns:
  repeat(5,...)` fixo (base e no breakpoint mobile) — ajustado pra `repeat(4,...)` nos dois
  lugares, senão sobraria um espaço vazio no lugar da coluna removida.
  - Testado com Playwright: kanban mostra só 4 colunas (Análise de Perfil, Preenchimento
    de Dados, Captação de Material, Entrevista — "Pago" não aparece); um participante já
    em "Pago" desde uma rodada anterior não aparece em nenhuma coluna do quadro; avancei um
    participante de teste de "Entrevista" até "Pago" pelo botão real da UI e confirmei que
    ele desaparece do quadro (mensagem de sucesso "avançou para Pago" continua aparecendo,
    só não sobra card visível depois) — desfiz a mudança depois pra devolver o estado
    original dos dados de teste.
  - **Nota de limpeza**: nesse teste percebi que um script de Playwright de uma rodada
    anterior desta sessão (já apagado) tinha travado achando um card errado pelo nome
    "Exemplo" e avançado por engano 2 participações reais (do participante-seed
    "Exemplo") até "Captação de Material" antes de dar timeout — passou despercebido no
    fechamento daquela rodada porque só validei os registros que eu *pretendia* ter
    mexido, sem reconferir a contagem geral. Achei comparando a distribuição de etapas
    antes/depois e restaurei as duas pra "Análise de Perfil", voltando o banco de teste ao
    estado original (10 em Análise de Perfil, 1 em Pago, igual estava antes de qualquer
    teste automatizado desta sessão).
  - **Segue sem commitar.** `git status` agora também inclui `participacoes/views.py` e
    `static/css/base.css`.
- **2026-08-13 (correção: "cores por status" era pra ser "cores por etapa" + reordenação
  do funil)** — O usuário apontou que a rodada anterior (cores + dropdown) mirou o campo
  errado: o pedido original usava a palavra "status" num sentido coloquial pra se referir
  à **etapa** do funil (que já existia como badge sempre azul, sem variação de cor, e sem
  jeito de editar direto na lista) — não ao campo `status` (Aprovação/Backup/etc., que era
  literalmente inédito na interface). Também pediu pra reordenar as etapas: **Preenchimento
  de Dados** (assim que a pessoa preenche os dados pelo link) → Análise de Perfil →
  Captação de Material → Entrevista → Pago — hoje Análise de Perfil vinha primeiro.
  - **Decisão**: mantive o dropdown/cores de `status` da rodada anterior (não foi pedido
    remover, e agora que existe é a única forma de editar esse campo no sistema todo — sem
    ele, voltaria a ficar só no Django admin) e *adicionei* o mesmo tratamento pra `etapa`
    ao lado. Se o usuário preferir tirar o de `status`, é reverter só essa coluna.
  - **Reordenação do funil**: `Participacao.Etapa` (TextChoices) reordenado pra
    `PREENCHIMENTO_DADOS, ANALISE_PERFIL, CAPTACAO_MATERIAL, ENTREVISTA, PAGO` — a ordem de
    declaração é o que decide tanto a ordem das colunas do Kanban (`Etapa.choices` iterado
    direto em `kanban()`) quanto a ordem das opções no dropdown novo, então só reordenar a
    classe já resolveu os dois lugares de uma vez. `ETAPAS_ORDEM` (lista separada, usada só
    por `avancar_etapa()` pra saber qual é a "próxima" etapa) seguiu a mesma nova ordem.
    Gerei `participacoes/migrations/0006_alter_participacao_etapa.py` (`AlterField`,
    puramente sobre a lista de `choices` — não muda nenhum dado nem tipo de coluna, os
    valores salvos no banco continuam as mesmas strings de sempre).
  - **Efeito colateral que precisou de ajuste** (achado revisando quem cria `Participacao`
    com etapa inicial fixa): como "Preenchimento de Dados" virou a etapa que representa
    literalmente "a pessoa acabou de preencher os dados pelo link", `pessoas/views.py::
    cadastro_publico()` (a view do link público) passou a criar a participação já em
    `PREENCHIMENTO_DADOS` em vez de `ANALISE_PERFIL` — é a etapa que descreve exatamente o
    que acabou de acontecer ali. Os outros 2 pontos que criam `Participacao` com etapa fixa
    (`wizard_revisao`, importação em lote — e `perfil_lote.py`, associação de gente já
    cadastrada por CPF) continuam criando em `ANALISE_PERFIL` de propósito: são fluxos
    onde a equipe já está de posse dos dados (veio de planilha ou já estava no Banco de
    Pessoas), não "a pessoa preenchendo o formulário agora" — decisão não pedida
    explicitamente, mas a leitura mais direta do parênteses do próprio pedido ("assim que a
    pessoa preenche os dados **pelo link**").
  - **Bug pego de graça por causa da reordenação**: `pessoas/views.py::descartar()` (botão
    de descartar um participante na triagem) limpava participações órfãs filtrando só por
    `etapa=ANALISE_PERFIL` — com o cadastro público agora criando em
    `PREENCHIMENTO_DADOS`, descartar um participante recém-cadastrado pelo link deixaria
    a participação dele **para trás**, órfã, sem limpar (o filtro antigo nunca ia bater
    nela). Corrigido pra `etapa__in=[PREENCHIMENTO_DADOS, ANALISE_PERFIL]` — as duas etapas
    que contam como "ainda não passou de revisão inicial".
  - **Cores por etapa**: `Participacao.CORES_ETAPA` (novo dict) + `etapa_badge` (property),
    mesmo padrão de `CORES_STATUS`/`status_badge` da rodada anterior — usando exatamente as
    mesmas cores já definidas em `core/dashviz.py::COR_ETAPA` (o gráfico "Situação dos
    participantes" dos dashboards), só que como classe de badge (`.b-*`) em vez de CSS var
    direta: Preenchimento de Dados → violeta, Análise de Perfil → azul, Captação de
    Material → âmbar, Entrevista → rosa, Pago → verde. Precisei criar a classe `.b-pink`
    (não existia — as outras 5 cores de badge já tinham classe, rosa não), usando as
    variáveis `--pink`/`--pink-soft` que já estavam definidas no CSS mas sem nenhum badge
    associado.
  - **Dropdown de etapa**: `participacoes/views.py::mudar_etapa(request, pk)` (novo, POST,
    mesma permissão `participacoes.mover_etapa`, mesmo padrão de `mudar_status` —
    inclusive já atualiza `etapa_atualizada_em` junto, igual `avancar_etapa()` faz, pra não
    zerar o "Na etapa desde" da tela de detalhe). Rota `participacoes/<int:pk>/etapa/`.
    `templates/participacoes/lista.html`: a coluna Etapa virou um `<select>` colorido igual
    ao de Status (mesma classe `.status-select`, cor via `part.etapa_badge`), só que sem
    opção "Sem etapa" (etapa nunca é vazia). Como muda a etapa passando por
    `Participacao.save()` normalmente, chegar em "Pago" pelo dropdown da lista também já
    atualiza `data_ultima_participacao` do participante — mesmo gatilho de sempre, não
    precisou de código novo pra isso. Badge do `detalhe.html` também ganhou cor (era sempre
    azul fixo antes).
  - Testado: (1) Playwright — ordem das colunas do Kanban confirmada (Preenchimento de
    Dados, Análise de Perfil, Captação de Material, Entrevista — Pago continua oculto,
    rodada anterior); dropdown de etapa na lista com as 5 opções na ordem certa e cor
    correspondente (`b-blue` pra quem estava em Análise de Perfil); mudei a etapa de uma
    linha pelo dropdown, mensagem de confirmação apareceu e desfiz a mudança depois; (2)
    cadastro público de ponta a ponta pelo formulário real (mockei a API do IBGE do
    seletor de cidade, que depende de rede externa e não respondia neste ambiente de
    teste) — confirmei no banco que a participação nasceu em `PREENCHIMENTO_DADOS`; (3)
    descartei esse mesmo participante e confirmei que a participação órfã foi removida
    (bug do item acima corrigido); removi o participante de teste depois. Zero erros de
    console em todo o percurso. Banco de teste conferido no fim — voltou exatamente pro
    baseline (10 participações em Análise de Perfil, 1 em Pago, nenhum status).
  - **Segue sem commitar.** `git status` agora também inclui `participacoes/models.py`,
    `participacoes/views.py`, `participacoes/migrations/0006_alter_participacao_etapa.py`
    (novo), `pessoas/views.py`, `static/css/base.css`,
    `templates/participacoes/lista.html`, `templates/participacoes/detalhe.html`.
- **2026-08-14 (Perfil volta a aceitar múltiplos formulários, ordenáveis)** — Antes da
  refatoração de Perfis (rodada bem anterior desta sessão), quem carregava formulário era
  o Projeto, e podia ter vários — um multi-select com campo de ordem. A refatoração
  reduziu isso pra 1 formulário por Perfil (FK simples). Usuário pediu de volta a mesma
  capacidade de antes, agora no nível do Perfil: 0 a N formulários, numa lista com
  checkbox pra marcar e campo numérico pra ordenar — **mesmo padrão** que `Formulario` já
  usa pra escolher suas `Variavel`s (`formularios/forms.py::VariavelSelecaoForm`/
  `montar_formset_variaveis`), não um widget novo.
  - **Modelo**: `Perfil.formulario` (FK) → `Perfil.formularios` (M2M) via `PerfilFormulario`
    (novo, em `projetos/models.py`, ao lado de `Perfil` pelo mesmo motivo de
    string-reference já documentado ali) — campos `perfil`, `formulario`, `ordem`,
    `UniqueConstraint(perfil, formulario)`, `Meta.ordering = ["ordem"]`. `on_delete=PROTECT`
    no FK do through preserva o comportamento de hoje: excluir um formulário em uso por
    algum perfil continua bloqueado com `ProtectedError` (`formularios/views.py::
    formulario_excluir` não precisou mudar).
  - **Pegadinha de M2M-through evitada**: `perfil.formularios.all()` **não** respeita a
    ordem do through (`PerfilFormulario.ordem`) — o manager do M2M ordena pelo
    `Meta.ordering` do `Formulario` (nome), não do through, porque o M2M manager não sabe
    nada sobre o through table's ordering. Resolvido com uma property nova,
    `Perfil.formularios_ordenados`, que consulta `self.perfil_formularios.select_related
    ("formulario").all()` (aí sim respeitando `Meta.ordering=["ordem"]`) — usada em toda
    view e template que precisa da lista de formulários do perfil, em vez de
    `.formularios.all()` direto.
  - **Migração** (mesmo padrão schema+dado+remove-campo-antigo já usado nesta sessão pra
    trocar `Projeto`→`Perfil`, dividida manualmente em 3 porque o Django propôs tudo numa
    migração só, removendo o campo antigo *antes* de eu poder copiar o dado):
    `0006_perfilformulario.py` (cria `PerfilFormulario` + `AddField Perfil.formularios`,
    mantendo `Perfil.formulario` intocado), `0007_backfill_perfil_formularios.py`
    (`RunPython`: cada perfil com `formulario_id` preenchido vira 1
    `PerfilFormulario(ordem=0)`), `0008_remove_perfil_formulario.py` (`RemoveField`).
    Confirmado no shell: os 4 perfis que tinham formulário associado ficaram cada um com
    exatamente 1 `PerfilFormulario` apontando pro mesmo formulário de antes.
  - `projetos/forms.py`: `FormularioSelecaoForm`/`FormularioSelecaoFormSet`/
    `montar_formset_formularios_perfil()` — cópia estrutural de
    `VariavelSelecaoForm`/`montar_formset_variaveis` (perfil↔formulário em vez de
    formulário↔variável). `PerfilForm` perde o campo `formulario` (fica só `nome`).
  - `projetos/views.py`: `_salvar_perfil_com_formularios()` (nova, espelha
    `formularios/views.py::_salvar_formulario_com_variaveis`) sincroniza os
    `PerfilFormulario` numa transação — apaga os desmarcados, `update_or_create` nos
    marcados (grava a ordem). `perfil_novo`/`perfil_editar` passam a montar e salvar esse
    formset junto do `PerfilForm`. Toda query que antes tinha `select_related("formulario")`
    virou `prefetch_related("perfil_formularios__formulario")` (`detalhe` do projeto,
    `perfil_detalhe`).
  - **Pontos de consumo que assumiam "1 formulário por perfil" — viraram loop**:
    `pessoas/wizard_csv.py` ganhou `variaveis_dos_formularios()` (mescla as variáveis de
    todos os formulários do perfil, dedup por `chave` — que já é globalmente única, então
    um formulário repetir uma variável de outro não duplica coluna); `ler_csv`/`ler_xlsx`/
    `ler_planilha`/`_mapa_variaveis` trocaram o parâmetro `formulario=None` por
    `formularios=None` (iterável). `pessoas/views.py::_perfil_e_formulario_do_wizard`
    virou `_perfil_e_formularios_do_wizard` (devolve a lista, via
    `perfil.formularios_ordenados`); `_validar_linha_csv`, `wizard_modelo_csv` e
    `wizard_revisao` passam a rodar `construir_form_resposta()` uma vez por formulário da
    planilha, juntando erros de todos e gravando uma `RespostaFormulario` por formulário
    ao confirmar (antes só uma). `_form_dinamico_do_perfil` (cadastro público) **já
    devolvia uma lista** desde a rodada anterior (decisão de design pensando exatamente
    nisso — só trocou o filtro de "no máximo 1" pra "todos os ativos do perfil, em ordem");
    `templates/publico/cadastro.html` não precisou mudar, já iterava num `{% for %}`.
    `participacoes/views.py::detalhe` (`formularios_do_projeto`) e
    `formularios/views.py::responder_formulario` (checagem de permissão) também passaram a
    considerar todos os formulários do perfil, não só um.
  - Templates: `perfil_form.html` ganhou a tabela checkbox+ordem (cópia visual de
    `formulario_form.html`); `detalhe.html` (projeto) e `perfil_detalhe.html` passam a
    listar os nomes dos formulários (o KPI do perfil virou uma contagem — "N formulários"
    — pra não estourar o layout de um card pequeno; o subtítulo da página é quem lista os
    nomes); `perfil_link.html` e `wizard_dados_csv.html` ajustados pro plural.
  - Testado com Playwright + Django test Client (misturado, pra cobrir tanto a UI quanto
    os fluxos que dependem de API externa/upload que são mais confiáveis via Client):
    (1) editei o perfil "Campanha Tenis Playwright · Perfil único" (que já tinha 1
    formulário do backfill), marquei um segundo, defini a ordem, salvei — subtítulo e KPI
    do perfil passaram a mostrar os dois, na ordem certa; (2) cadastro público desse
    perfil: os campos dos dois formulários apareceram na página (mockei a API do IBGE do
    seletor de cidade, que não responde neste ambiente), enviei preenchido e confirmei 2
    `RespostaFormulario` distintas gravadas, uma por formulário, com os dados certos; (3)
    modelo de planilha baixado do wizard trouxe as colunas dos dois formulários
    concatenadas, na ordem certa; (4) validação de uma linha da planilha com erro em só um
    dos dois formulários reportou exatamente esse erro (o outro formulário, com dados
    válidos, não apareceu nos erros — confirma que os dois são avaliados independentemente
    dentro do merge); (5) um upload limpo (formulário sem colisão de nome, evitando a
    limitação de colisão fixo×dinâmico já documentada numa rodada anterior) importou com
    sucesso e gravou a `RespostaFormulario` certa via `wizard_revisao`; (6) tentativa de
    excluir um formulário em uso por um perfil continua bloqueada (`ProtectedError`,
    redirecionado com mensagem, formulário não apagado); (7) tela de "Novo perfil" também
    renderiza a mesma tabela de seleção, sem nada marcado. `makemigrations --check
    --dry-run` limpo. Zero erros de console em todo o percurso.
  - **Efeito colateral do teste, corrigido**: pra testar o merge de 2 formulários no
    cadastro público, usei um CPF que já batia com um participante de teste pré-existente
    de uma rodada bem anterior desta sessão ("Teste Dinamico") — o upsert (mecanismo já
    existente, comportamento correto) sobrescreveu nome/e-mail/telefone/nascimento/cidade
    dele com os dados do meu teste. Restaurei o nome de volta pra "Teste Dinamico" (bem
    evidenciado por uma resposta de formulário já salva antes do teste); os outros campos
    (e-mail/telefone/nascimento/cidade) não tinham um snapshot conhecido pra restaurar com
    segurança e ficaram com o valor que o teste deixou — registrando aqui caso essa pessoa
    de teste específica seja usada como referência em algo futuro.
  - **Segue sem commitar.** `git status` agora também inclui `projetos/models.py`,
    `projetos/forms.py`, `projetos/views.py`, `projetos/admin.py`,
    `projetos/migrations/0006_perfilformulario.py`,
    `0007_backfill_perfil_formularios.py`, `0008_remove_perfil_formulario.py` (novos),
    `pessoas/views.py`, `pessoas/wizard_csv.py`, `participacoes/views.py`,
    `formularios/views.py`, `templates/projetos/perfil_form.html`,
    `templates/projetos/detalhe.html`, `templates/projetos/perfil_detalhe.html`,
    `templates/projetos/perfil_link.html`, `templates/pessoas/wizard_dados_csv.html`.
- **2026-08-14 (BP.xlsx: campos obrigatórios do participante + 9 formulários de
  perfilamento com 60 variáveis)** — Usuário trouxe `BP.xlsx` (raiz do projeto) com uma
  aba "Modelo" (190 linhas × 85 colunas) e uma aba de opções por coluna (nome da aba =
  letra da coluna). Pedido em duas etapas: primeiro só ler e confirmar entendimento (sem
  mexer em nada), depois — já com todas as dúvidas respondidas — implementar de verdade.
  - **Mapeamento confirmado com o usuário**: colunas H–Y (18 perguntas, 17 sem contar
    "Idade" que já é calculada) viram **campos obrigatórios do `Participante`** (não um
    formulário dinâmico — pedido explícito: "essas perguntas façam parte do
    participante"). Colunas Z–AE + CG viram o formulário **Perguntas Básicas de Saúde**;
    AF–AK **Lifestyle**; AL–AQ **Banco**; AR–AW **Beleza**; AX–BD **Esporte**; BE–BK
    **Entretenimento**; BL–BR **Tecnologia**; BS–BY **Bebidas**; **BZ**–CF
    **Alimentação** (o usuário tinha dito "BA a CF" — corrigido pra BZ, já que BA já
    pertence ao bloco de Esporte nos cabeçalhos reais da planilha).
  - **Fonte da verdade das opções**: confirmado com o usuário — a aba de cada coluna
    manda, não os dados que já existiam no sistema (tratado como "princípio de teste").
    Isso trocou as opções de `genero` (4 → 7, códigos novos) e `escolaridade` (4 tiers
    genéricos → 7 tiers específicos, sem "Fundamental") pelas da planilha, e criou do
    zero: `raca`, `estado_civil`, `ocupacao`, `regiao`. `faixa_renda` (3 faixas
    agregadas) foi **substituído** por dois campos novos — `renda_individual` e
    `renda_familiar` — porque a planilha trata como duas perguntas distintas (colunas P e
    Q), cada uma com 5 classes (A-E) e rótulo de valor próprio (a classe B, por exemplo,
    tem faixa de R$ diferente conforme é individual ou familiar).
  - **Tipo de resposta**: a planilha não tem nenhuma coluna dizendo o tipo (dropdown,
    radio, checkbox) — só a lista de opções. Regra combinada com o usuário: pergunta cujo
    texto contém "quais" (plural) → `multipla_escolha` (checkbox); senão, é escolha
    única — 2 opções → `radio`, 3+ → `select` (dropdown). Aplicada mecanicamente nas 60
    perguntas via script (não à mão, pra não errar por cansaço) — nenhuma das 60 caiu no
    caso de exatamente 2 opções nesta planilha, mas a regra está implementada pros dois
    casos.
  - **`pessoas/models.py`**: `Genero`/`Escolaridade` (choices reescritas), `Raca`,
    `EstadoCivil`, `Ocupacao`, `Regiao`, `FaixaRendaIndividual`, `FaixaRendaFamiliar`
    (`TextChoices` novas). Campos novos com `null=True` (mesmo padrão já usado pro CPF —
    obrigatório em formulário via `blank=False`, mas tolera `None` em quem já estava
    cadastrado antes dessa mudança, sem precisar de migração de dado inventando valor).
    `email`/`bairro` passaram de `blank=True` pra obrigatórios (já eram `NOT NULL` no
    banco, só a validação de formulário mudou). `profissao` (FK) virou `blank=False`
    mantendo `null=True`.
  - **Migração** `pessoas/migrations/0008_campos_perfilamento_bp.py` — só `AddField`/
    `AlterField`/um `RemoveField` (`faixa_renda`), sem passo de backfill: como os campos
    novos são `null=True`, cadastros existentes ficam com o campo vazio até serem
    editados (não crashou nem pediu default na hora do `makemigrations`, rodou limpo e
    não-interativo).
  - **`pessoas/forms.py`**: `ParticipanteForm.Meta.fields` ganhou os 6 campos novos;
    como `ParticipanteWizardForm`/`CadastroPublicoForm` herdam de `ParticipanteForm` sem
    redeclarar a lista de campos, ganharam tudo de graça. `templates/publico/cadastro.html`
    também não precisou de nenhuma mudança — já itera `{% for field in form %}`
    genericamente.
  - **`pessoas/matching.py`**: `CAMPOS_ATUALIZAVEIS` (upsert) e `PLACEHOLDERS_LEGADO`
    (lote legado) ganharam os campos novos — sem isso, um lote legado que não trouxesse
    "Gênero" (por exemplo) não ficaria marcado `cadastro_incompleto`, quebrando o
    propósito da flag (ela existe pra sinalizar exatamente isso).
  - **`pessoas/wizard_csv.py`**: `CAMPOS_CSV` ganhou sinônimos de coluna pros campos
    novos (incluindo "Bairro", que **não tinha sinônimo nenhum antes** — bug latente
    achado no caminho: até aqui, mesmo sendo campo do model há muito tempo, o wizard
    nunca soube ler uma coluna "Bairro" de planilha). Mapas de normalização novos
    (`RACA_MAP`, `ESTADO_CIVIL_MAP`, `OCUPACAO_MAP`, `REGIAO_MAP`, `RENDA_MAP` — este
    último compartilhado entre individual/familiar, já que o código de classe A-E é
    igual) e `GENERO_MAP`/`ESCOLARIDADE_MAP` reescritos pros códigos novos.
    `CABECALHO_MODELO`/`LINHA_EXEMPLO` (modelo de planilha baixável) ganharam as 6
    colunas novas + Bairro.
  - **9 formulários + 60 variáveis + 636 opções**: `formularios/migrations/
    0006_seed_perguntas_basicas_bp.py` (nova, ~51K caracteres — gerada por script a
    partir dos dados extraídos do `BP.xlsx`, não lida do arquivo em tempo de migração,
    pra ser reproduzível em qualquer ambiente/deploy sem depender do `.xlsx` estar
    presente). `RunPython` cria os 9 `Formulario` (`inclui_campos_fixos=False` — os
    campos fixos agora são sempre obrigatórios no cadastro base, não faz sentido esses
    formulários "extra" reafirmarem isso) e, pra cada um, suas `Variavel`/
    `VariavelOpcao`/`FormularioVariavel` na ordem da planilha. `obrigatoria=False` em
    todas as 60 — decisão não pedida explicitamente, mas a leitura mais direta do pedido
    original (só H–Y foi chamado de "obrigatório"; os 9 blocos temáticos foram descritos
    só como "perguntas" a organizar em formulário, sem menção a obrigatoriedade). Reversão
    da migração implementada (apaga por nome, na ordem certa pra não esbarrar no
    `on_delete=PROTECT` entre `FormularioVariavel` e `Variavel`), mesmo não sendo um
    caminho que planejo usar.
  - **`chave` da Variavel**: gerada na migração replicando a lógica de
    `Variavel._gerar_chave()` (`slugify` + sufixo numérico em colisão) em vez de chamar o
    método de verdade — migração usa `apps.get_model()` (model "congelado" no tempo da
    migração), que não carrega métodos customizados do model real, só os campos.
  - Templates: `pessoas/form.html` (raça, estado civil, região, ocupação, renda
    individual/familiar nos fieldsets certos), `pessoas/detalhe.html` (linhas novas na
    tabela de dados cadastrais), `pessoas/lista.html` (filtro renomeado
    `faixa_renda`→`renda_individual`, mesmas opções).
  - Testado: (1) tela "Novo participante" mostra os 6 campos novos com as opções certas
    (gênero com 7, escolaridade com 7, renda individual com 5 rótulos em R$); (2) cadastro
    completo salvo com sucesso, conferido no banco que todos os 10 campos (incluindo os 6
    novos) persistiram com os valores certos; (3) associei "Perguntas Básicas de Saúde" a
    um perfil de teste — modelo de planilha do wizard trouxe as 19 colunas fixas + as
    perguntas dos formulários associados (incluindo "Filhos", que fica dentro do
    formulário de Saúde); desassociei depois, voltando o perfil ao estado original; (4)
    lista de Pessoas, filtro de renda individual, exportação XLSX e os dois dashboards
    (Visão participantes / Visão por segmento) carregando sem erro 500 nem exceção —
    confirma que o rename de `faixa_renda` não quebrou nenhum consumidor esquecido.
    `makemigrations --check --dry-run` limpo. Zero erros de console em todo o percurso.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/models.py`,
    `pessoas/forms.py`, `pessoas/views.py`, `pessoas/matching.py`, `pessoas/wizard_csv.py`,
    `pessoas/exportacao.py`, `pessoas/migrations/0008_campos_perfilamento_bp.py` (novo),
    `formularios/migrations/0006_seed_perguntas_basicas_bp.py` (novo), `core/dashviz.py`,
    `templates/pessoas/form.html`, `templates/pessoas/detalhe.html`,
    `templates/pessoas/lista.html`, e `BP.xlsx` (novo, arquivo fonte na raiz do projeto).
- **2026-08-14 (pergunta de múltipla escolha vira dropdown, não parede de checkbox)** —
  Direto da rodada anterior: perguntas de `multipla_escolha` com muitas opções (ex.:
  "Quais marcas de beleza você utiliza atualmente?", 74 marcas) renderizavam como uma
  lista vertical de checkbox sempre visível — com dezenas de opções isso empurra o resto
  do formulário pra baixo e fica visualmente pesado. Pedido: virar um dropdown de
  múltipla seleção.
  - **`formularios/widgets.py`** (novo) — `DropdownCheckboxSelectMultiple`, subclasse de
    `forms.CheckboxSelectMultiple` que só troca o `template_name`. Continua mandando um
    `<input type="checkbox" name="...">` por opção (o POST no servidor não muda em nada,
    zero mudança em `formularios/respostas.py::construir_form_resposta` além de trocar
    qual widget usar) — a diferença é inteiramente visual/client-side.
  - **`formularios/templates/formularios/widgets/dropdown_checkbox_select.html`** (novo)
    — template custom do widget: botão-gatilho (mostra "Selecione…", o nome da opção se só
    1 estiver marcada, ou "N selecionadas"), painel que abre por baixo com campo de busca
    e a lista de checkboxes dentro (scroll interno, não estica a página).
    **Pegadinha descoberta no caminho**: o *form renderer* do Django (que desenha widgets)
    usa uma engine de template **separada** da engine principal do projeto — ela só
    enxerga templates dentro da pasta `templates/` de cada *app* (`app_directories`), não
    a pasta `templates/` na raiz do projeto onde todo o resto do sistema guarda seus
    templates. Coloquei o arquivo lá primeiro (padrão do resto do projeto) e caiu em
    `TemplateDoesNotExist` — corrigido movendo pra dentro de
    `formularios/templates/formularios/widgets/`, a única pasta que essa engine
    específica enxerga.
  - **`static/js/dropdown_multiselect.js`** (novo, incluído globalmente em `base.html` e
    em `publico/cadastro.html`, mesmo padrão do `flash_erros.js`) — abre/fecha o painel,
    fecha ao clicar fora ou `Esc`, filtra as opções pelo texto digitado na busca (ignora
    acento/caixa), atualiza o rótulo do botão ao marcar/desmarcar (inclusive já no
    carregamento da página, pra respeitar opções pré-marcadas na prévia/edição). Só entra
    em ação se existir pelo menos um `.dropdown-multiselect` na página — no-op em todo o
    resto do sistema.
  - **`static/css/base.css`**: estilo do gatilho (igual a um `<select>` comum, mesma
    paleta/raio de borda do resto dos campos) e do painel (sombra `--shadow`, borda
    `--line`, opções com hover em `--violet-soft`).
  - Testado: (1) associei "Perguntas Básicas de Beleza" (3 perguntas de múltipla escolha,
    uma com 74 opções) a um perfil de teste e abri o link de cadastro público — os 5
    dropdowns de múltipla escolha da página (de 2 formulários combinados) renderizam
    fechados por padrão; abri o de 74 opções, busquei "ro" e filtrou corretamente pra
    "Ruby Rose"/"Boca Rosa"/"Neutrogena"; marquei 2 opções e o rótulo do botão virou
    "2 selecionadas"; cliquei fora e o painel fechou; (2) prévia de formulário
    (`formulario_visualizar`, somente leitura) — os 3 dropdowns aparecem com os 91
    checkboxes (74+8+9) todos desabilitados, confirmando que o modo somente-leitura
    (`campo.disabled = True`) continua propagando corretamente pro widget novo; (3)
    desfiz a associação de formulário de teste depois. Zero erros de console.
  - **Segue sem commitar.** `git status` agora também inclui `formularios/widgets.py`
    (novo), `formularios/templates/formularios/widgets/dropdown_checkbox_select.html`
    (novo), `formularios/respostas.py`, `static/js/dropdown_multiselect.js` (novo),
    `static/css/base.css`, `templates/base.html`, `templates/publico/cadastro.html`.
- **2026-08-14 (cadastro público: CEP reposicionado + Região preenchida sozinha + seções
  por formulário + CEP obrigatório)** — Usuário mandou um print do cadastro público real
  (perfil "Campanha Tênis Playwright", já com formulários próprios associados por ele
  mesmo pela tela que criei há duas rodadas) pedindo três coisas nessa tela: (1) CEP
  reposicionado pra ficar logo antes de Região, com o ViaCEP preenchendo o resto sozinho;
  (2) separação visual em seções — "Perguntas Básicas" primeiro, depois uma seção por
  formulário associado ao perfil (título = nome do formulário), com uma linha fina entre
  elas, não caixas pesadas; (3) todas as perguntas do formulário base obrigatórias.
  - **CEP já tinha ViaCEP** (`static/js/endereco_cep.js`, de uma rodada bem anterior) —
    preenchia bairro/UF e disparava a busca de cidades do IBGE, mas **não existia** ainda
    quando esse script foi escrito, então nunca preenchia Região. Adicionado
    `REGIAO_POR_UF` (mapa fixo — é geografia oficial, os 5 grupos de estado não mudam) e
    `definirRegiao(uf)`, chamada tanto na resposta do ViaCEP quanto na troca manual de UF
    — cobre os dois jeitos de a UF ficar sabida.
  - **CEP era o único campo do H–Y que tinha ficado de fora da obrigatoriedade** na rodada
    anterior (não estava nas 18 colunas H-Y da planilha original) — agora que ele entra
    de vez no fluxo (é o gatilho do autopreenchimento), virou obrigatório também, fechando
    a lacuna: `pessoas/models.py::Participante.cep` perde o `blank=True` (migração
    `0009_cep_obrigatorio.py`, só `AlterField`, sem precisar de default pra dado
    existente — a coluna já era `NOT NULL`, só a validação de formulário mudou).
  - **Reordenação**: `pessoas/forms.py::ParticipanteForm.Meta.fields` — CEP sai de antes
    de UF e vai pra logo antes de Região (depois de UF/Cidade/Bairro). Como
    `publico/cadastro.html` itera os campos do form na ordem do `Meta.fields`, isso já
    resolve a posição na tela sem precisar tocar no template pra essa parte. O formulário
    interno (`pessoas/form.html`) já tinha CEP antes de Região na mesma linha (ordem
    manual, campo a campo) — não precisou de ajuste.
  - **Seções**: `publico/cadastro.html` reestruturado — a lista solta de campos virou um
    bloco "Perguntas Básicas" (os campos fixos do `ParticipanteForm`) seguido de um bloco
    por item de `forms_dinamicos` (cada um já é 1 formulário do perfil, na ordem
    escolhida na tela de perfil), cada um com `<h3>{{ formulario.nome }}</h3>`. Classe CSS
    nova `.cadastro-secao` (linha fina `border-top` + respiro, sem borda na primeira seção
    pra não duplicar a linha que já existe abaixo do subtítulo do cabeçalho) — decisão de
    propósito de não usar painel/caixa (`.panel` já existente no sistema é mais pesado
    visualmente, o pedido foi por algo sutil).
  - Testado com Playwright (mockei ViaCEP e IBGE, que não respondem neste ambiente de
    teste sem internet — mesma técnica já usada nas rodadas anteriores): (1) 4 seções
    renderizadas na página de um perfil com 3 formulários associados (o próprio usuário já
    tinha montado esse cenário testando a tela de perfil) — "Perguntas Básicas",
    "Perguntas Básicas de Alimentação", "...de Banco", "...de Bebidas"; (2) ordem dos
    campos confirmada — CEP aparece logo antes de Região; (3) preenchi o CEP
    "01310-100" e conferi que Bairro, UF, Cidade **e Região** foram todos preenchidos
    sozinhos (antes desta rodada, Região nunca preenchia); (4) confirmado que submeter o
    formulário sem CEP agora dá erro "Este campo é obrigatório." Zero erros de console.
    Não mexi nos formulários associados ao perfil de teste usado (Alimentação/Banco/
    Bebidas) — são associações reais que o próprio usuário já tinha montado explorando a
    tela de perfil, não fixture minha, então não desfiz nada ao terminar.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/models.py`,
    `pessoas/forms.py`, `pessoas/migrations/0009_cep_obrigatorio.py` (novo),
    `static/js/endereco_cep.js`, `static/css/base.css`, `templates/publico/cadastro.html`.
- **2026-08-14 (CEP primeiro, Região continuava sem preencher — bug real: cache do
  navegador no JS)** — Usuário mandou um segundo print da mesma tela pedindo ordem
  diferente (CEP primeiro, depois Região, Estado, Cidade, Bairro) e reclamando de novo que
  o ViaCEP não preenche Região — mas eu já tinha implementado isso na rodada anterior.
  - **Causa raiz**: `static/js/endereco_cep.js` é incluído nos templates como
    `{% static 'js/endereco_cep.js' %}` — **sem** cache-busting. O projeto já tem exatamente
    a ferramenta certa pra isso, `core/templatetags/static_v.py::static_v` (gruda
    `?v=<data de modificação do arquivo>` na URL), só que até agora só era usada pra CSS. O
    print do usuário mostrava UF e Cidade certos (prova que o ViaCEP rodou) mas Região
    errada ("Norte" pra um CEP do Rio de Janeiro) — exatamente a assinatura de rodar uma
    cópia do JS em cache no navegador, de antes da Região existir no script: o valor
    "Norte" ali era sobra de uma seleção manual anterior, não um cálculo novo errado (o
    código em si já estava certo, só não chegava a rodar naquele navegador). A própria
    docstring do `static_v` já registra que isso **já tinha acontecido antes com CSS**
    ("foi exatamente o que confundiu o usuário com o CSS do modal de avaliação") — mesma
    causa, dessa vez em JS.
  - **Correção estrutural** (não só o caso do CEP): troquei **todo** `<script src="{%
    static 'js/...' %}">` do projeto (17 tags em 10 templates) por `{% static_v %}`,
    adicionando `static_v` no `{% load %}` de quem ainda não tinha. Não é sobre esse bug
    específico — é fechar a lacuna de vez, já que o mecanismo existe desde uma rodada bem
    anterior mas só cobria CSS.
  - **Reordenação**: `pessoas/forms.py::ParticipanteForm.Meta.fields` — CEP volta a ficar
    logo depois de E-mail (era a posição original, antes da rodada passada), seguido de
    Região, UF, Cidade, Bairro. `templates/pessoas/form.html` (formulário interno)
    ajustado pra mesma ordem na fieldset "Contato e endereço".
  - Testado com Playwright (ViaCEP/IBGE mockados, mesma técnica de sempre): (1) confirmei
    que o `<script>` servido agora carrega com `?v=<timestamp>` na URL — a causa raiz de
    fato sumiu; (2) ordem dos campos na seção "Perguntas Básicas" confirmada: E-mail, CEP,
    Região, UF, Cidade, Bairro, Escolaridade...; (3) preenchi o CEP de Niterói/RJ
    (24110-415) e confirmei bairro="Barreto", UF="Rio de Janeiro", Região="Sudeste" — a
    região certa dessa vez, e batendo com a UF (antes o print mostrava "Norte" pra um
    endereço do Rio). Zero erros de console. Não toquei nos formulários associados ao
    perfil de teste (permanecem os mesmos 3 que o usuário já tinha montado).
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/forms.py`,
    `templates/pessoas/form.html`, e os 8 templates que ganharam `static_v` nos scripts:
    `templates/base.html`, `templates/publico/cadastro.html`,
    `templates/core/home.html`, `templates/core/dashboard_segmento.html`,
    `templates/participacoes/lista.html`, `templates/participacoes/detalhe.html`,
    `templates/pessoas/wizard_revisao.html`, `templates/pessoas/wizard_dados_manual.html`,
    `templates/formularios/variavel_form.html`.
- **2026-08-14 (tela "Link de cadastro" removida — vira botão de copiar direto)** — Desde
  que o link público parou de expirar por tempo (rodada bem anterior — só perde validade
  se o projeto sair de "Recrutando"), a tela dedicada (`projetos:perfil_link`, com campo
  de link + botão "Gerar novo link") não tinha mais razão de existir: como o token é só
  assinado na hora (sem estado salvo no banco), dá pra montar o link direto onde ele é
  mostrado, sem precisar navegar pra outro lugar.
  - `projetos/views.py::_link_captacao(request, perfil)` (novo, privado) — mesma geração
    de token de sempre (`gerar_token_captacao(perfil.id, request.user.id)`), só que
    chamada direto de `detalhe()` (tela do projeto, um link por perfil na tabela) e
    `perfil_detalhe()` (tela do perfil), anexando `perfil.link_cadastro` em cada objeto.
    Como o `recrutador_id` do token é sempre "quem está vendo a página agora", o link
    mostrado já reflete corretamente quem vai levar o crédito pela indicação se for essa
    pessoa quem copiar e compartilhar — sem precisar de um botão "Gerar novo link"
    separado pra isso (é recalculado a cada carregamento da página).
  - View `perfil_link`, rota `projetos/perfis/<int:pk>/link/` e o template
    `projetos/perfil_link.html` foram **removidos** (não mantidos como código morto).
  - `templates/projetos/detalhe.html` e `templates/projetos/perfil_detalhe.html`: o `<a
    href="...">Link</a>` que navegava pra tela dedicada virou `<button type="button"
    data-copiar="{{ perfil.link_cadastro }}">` — clique copia pro clipboard
    (`navigator.clipboard.writeText`, com fallback via `document.execCommand("copy")` pra
    contexto sem Clipboard API) e sobe um balãozinho "Link copiado!" ancorado no próprio
    botão (aparece por cima, seta apontando pra baixo, some sozinho depois de ~1.6s).
  - `static/js/copiar_link.js` (novo, incluído globalmente em `base.html` via
    `static_v` — funciona em qualquer botão com `data-copiar="<texto>"` em qualquer tela
    futura, não é específico de link de cadastro) + `.balao-copiado` em
    `static/css/base.css` (mesma linguagem visual do `.flash-card`, mas pequeno e
    ancorado no elemento em vez de canto da tela).
  - Testado com Playwright (contexto com permissão de clipboard concedida): (1) a rota
    antiga (`/projetos/perfis/1/link/`) agora dá 404, confirmando que não sobrou nada
    acessível; (2) botão "Copiar link" na tabela de perfis do projeto — cliquei, balão
    "Link copiado!" apareceu, conteúdo do clipboard bateu exatamente com o
    `data-copiar` do botão, balão sumiu sozinho depois de ~2s; (3) decodifiquei o token
    copiado e confirmei `perfil_id`/`recrutador_id` corretos (o usuário logado no teste);
    (4) mesmo teste no botão "Copiar link de cadastro" da tela do perfil — funciona igual.
    Zero erros de console (fora o 404 esperado da checagem da rota removida).
  - **Segue sem commitar.** `git status` agora também inclui `projetos/views.py`,
    `projetos/urls.py`, `static/js/copiar_link.js` (novo), `static/css/base.css`,
    `templates/base.html`, `templates/projetos/detalhe.html`,
    `templates/projetos/perfil_detalhe.html`; `templates/projetos/perfil_link.html`
    removido.
- **2026-08-17 (Perfil ganha "tipo" Captação/Respostas + Formulário ganha Categoria — CRUD
  novo em "Configurações de Formulários")** — Duas peças de organização pedidas juntas,
  preparando terreno pra uma ideia futura do usuário: só pedir **algumas** categorias de
  formulário na hora de responder um perfil, não todas de uma vez (ver nota no fim).
  - **`Perfil.tipo`** (`projetos/models.py`) — `TextChoices` nova (`CAPTACAO`/`RESPOSTAS`,
    default `CAPTACAO` — mantém o comportamento de todo perfil já existente igual a antes
    dessa migração). Migração `0009_perfil_tipo.py` (só `AddField`, sem passo de dado).
    `PerfilForm` ganhou o campo; `perfil_form.html` mostra o dropdown ao lado do nome;
    badge colorido (azul "Captação" / violeta "Respostas") na tabela de perfis do projeto
    (`detalhe.html`) e no título da tela do perfil (`perfil_detalhe.html`). Só o campo em
    si foi adicionado — nenhum comportamento downstream (link público, wizard, etc.) lê
    esse campo ainda; é puramente informativo por enquanto.
  - **`CategoriaFormulario`** (novo model em `formularios/models.py`) — `nome` (único),
    `observacao`, `id` (UUID, mesmo padrão de `Formulario`/`Variavel`/`TipoResposta`).
    `Formulario` ganhou `categoria` (FK, `null=True, blank=True, on_delete=SET_NULL` —
    de propósito **não** é `PROTECT`: apagar uma categoria não trava nem apaga os
    formulários que estavam nela, só solta a associação, porque categoria aqui é
    organização/rótulo, não uma dependência estrutural como Variável→Formulário é).
    Migração `0007_categoria_formulario.py`.
  - **CRUD de Categoria** — `formularios/views.py::categorias_lista/categoria_novo/
    categoria_editar/categoria_excluir`, `formularios/forms.py::CategoriaFormularioForm`,
    rotas em `formularios/urls.py` (`/formularios/categorias/...`), templates
    `categorias_lista.html`/`categoria_form.html`/`categoria_excluir.html` — cópia
    estrutural do CRUD de Variável (o mais simples que já existia: sem sub-formset,
    excluir sem `ProtectedError` porque a FK é `SET_NULL`). Entra em "Configurações de
    Formulários" no menu lateral, terceiro item depois de Variáveis e Formulários.
    `formulario_form.html` ganhou o dropdown de categoria (`empty_label="Sem categoria"`);
    `formularios_lista.html` ganhou a coluna com badge da categoria.
  - **Permissões novas** — `categorias_formulario.ver/gerenciar/excluir`, mesmo padrão
    (trio ver/gerenciar/excluir) que Variável e Formulário já têm cada um o seu, em vez de
    reaproveitar os códigos de `formularios.*` — mantém a granularidade que o resto do
    catálogo já usa. Adicionadas ao catálogo de referência
    (`accounts/permissions.py::CATALOGO_PERMISSOES`) e semeadas de verdade via
    `accounts/migrations/0011_seed_categorias_formulario_permissoes.py` (mesmo formato de
    `0007_seed_variaveis_permissoes.py`: Administrador e Operador ganham os 3, Visualizador
    só "ver").
  - **Nota importante — o que NÃO foi implementado ainda**: a frase final do pedido ("minha
    ideia é fazer com que ao responder um perfil, o usuário responda no final, apenas
    algumas categorias, e não todas") descreve a motivação/objetivo final, não uma
    especificação de como isso deve funcionar — não ficou claro, por exemplo, se a escolha
    de quais categorias entram é manual (quem monta o perfil escolhe quais categorias
    quer), automática/aleatória (sorteia N categorias por resposta), ou fixa por perfil.
    Essa rodada só constrói a base (categorizar formulários) — o mecanismo de **filtrar**
    quais categorias aparecem na hora de responder ainda não existe; fica pra confirmar
    com o usuário como deve funcionar antes de implementar.
  - Testado com Playwright: (1) criei uma categoria de teste, apareceu certinho na lista
    (nome, observação truncada, contagem de formulários); (2) associei essa categoria a um
    formulário existente pelo dropdown — badge apareceu na lista de formulários; (3)
    dropdown de tipo de perfil mostra as 2 opções certas, mudei um perfil de teste pra
    "Respostas" e confirmei o badge aparecendo tanto na tabela de perfis do projeto quanto
    no título da tela do próprio perfil; (4) desfiz todas as mudanças de teste depois —
    perfil voltou pra "Captação", formulário voltou "sem categoria", categoria de teste
    excluída — não sobrou nada no banco. `makemigrations --check --dry-run` limpo. Zero
    erros de console.
  - **Segue sem commitar.** `git status` agora também inclui `projetos/models.py`,
    `projetos/forms.py`, `projetos/migrations/0009_perfil_tipo.py` (novo),
    `formularios/models.py`, `formularios/forms.py`, `formularios/views.py`,
    `formularios/urls.py`, `formularios/migrations/0007_categoria_formulario.py` (novo),
    `accounts/permissions.py`, `accounts/migrations/
    0011_seed_categorias_formulario_permissoes.py` (novo), `templates/base.html`,
    `templates/projetos/perfil_form.html`, `templates/projetos/detalhe.html`,
    `templates/projetos/perfil_detalhe.html`, `templates/formularios/formulario_form.html`,
    `templates/formularios/formularios_lista.html`, e os 3 templates novos de Categoria.
- **2026-08-17 (Tabelas de listagem viram cards no mobile — sem grid de calendário no
  projeto)** — Pedido do usuário: aplicar aqui o mesmo padrão de responsividade mobile já
  validado em outro sistema dele, pra telas de listagem (tabelas) e grades de calendário.
  Busquei por grid de calendário no projeto e não existe nenhuma feature desse tipo aqui
  (só CSS interno do Django admin bateu com "calendar" na busca, irrelevante) — então essa
  rodada cobre só a parte de tabelas, que é 100% do escopo aplicável ao Qualy Vortice hoje.
  - **Padrão CSS** (`static/css/base.css`) — bloco novo dentro de `@media
    (max-width:700px)`: `.tbl-wrap thead{display:none}`, cada `<tr>` vira um cartão
    (`display:block`, borda, padding, `margin-bottom`), cada `<td>` vira
    `display:flex;justify-content:space-between` com `::before{content:attr(data-label)}`
    mostrando o rótulo da coluna à esquerda e o valor à direita — exatamente o mecanismo
    descrito pelo usuário. Coluna de ações (sem `data-label`) usa
    `justify-content:flex-start;flex-wrap:wrap` em vez de `space-between`, pra botões não
    ficarem espalhados com buracos grandes entre eles. Acima de 700px nada muda — é tudo
    dentro da media query, view desktop intacta.
  - **`.td-acoes`** (classe nova) — 6 templates tinham a célula de ações com
    `style="display:flex;gap:6px;justify-content:flex-end"` inline; como estilo inline
    sempre vence regra de stylesheet (mesmo dentro de media query), isso bloquearia
    silenciosamente a responsividade nessas células. Extraí pra uma classe compartilhada e
    troquei `<td style="...">` por `<td class="td-acoes">` em `accounts/usuarios_lista.html`,
    `formularios/categorias_lista.html`, `formularios/formularios_lista.html`,
    `formularios/variaveis_lista.html`, `participacoes/lista.html`, `projetos/detalhe.html`.
  - **`data-label` em todos os `<td>` de dado** (coluna de ações sempre excluída) nas 16
    telas com tabela do projeto: `pessoas/lista.html`, `pessoas/detalhe.html` (tabelas
    "Termos aceitos" e "Participações" — a tabela "Dados cadastrais"/"Pagamento" já é
    2-colunas simples fora de `.tbl-wrap`, não precisa do tratamento),
    `pessoas/wizard_revisao.html`, `participacoes/lista.html`, `participacoes/detalhe.html`,
    `projetos/detalhe.html`, `projetos/perfil_detalhe.html`, `projetos/perfil_form.html`,
    `formularios/formularios_lista.html`, `formularios/formulario_form.html`,
    `formularios/variaveis_lista.html`, `formularios/categorias_lista.html`,
    `accounts/usuarios_lista.html`, `accounts/painel_permissoes.html`, `termos/lista.html`,
    `auditoria/lista.html`.
  - **Caso especial: linha de correção do wizard** — em `pessoas/wizard_revisao.html`,
    linhas inválidas ganham uma segunda `<tr class="wiz-linha-correcao">` logo abaixo, com
    um único `<td colspan="6">` contendo um `.form-row` de campos de correção — não é um
    par rótulo→valor, então a regra genérica `.tbl-wrap td{display:flex}` a deixaria
    espremida. Adicionei um override específico (`.tbl-wrap tr.wiz-linha-correcao{...}` /
    `.tbl-wrap tr.wiz-linha-correcao td{display:block;...}`) que devolve essa linha pro
    fluxo de bloco normal, exibindo o formulário de correção por baixo do cartão da linha
    com erro, sem cortar nem espremer os campos.
  - **Caso especial: matriz de permissões** — `accounts/painel_permissoes.html` não é uma
    lista de entidades, é uma matriz Permissão × Nível com um checkbox por célula. Pra cada
    célula de nível mostrar qual nível ela representa no cartão mobile, adicionei `label`
    (o `get_nivel_display` de cada nível) em cada item de `linha.checks`
    (`accounts/views.py::painel_permissoes`) e usei `data-label="{{ c.label }}"` — no
    mobile, cada permissão vira um cartão com uma linha "ADMINISTRADOR ☑", "OPERADOR ☐"
    etc., em vez de uma tabela de 4+ colunas apertada.
  - Testado com Playwright em três larguras (375px, 700px e 1280px/desktop) nas 8 telas de
    listagem principais: **nenhuma teve `scrollWidth > clientWidth`** (zero rolagem
    horizontal) em nenhuma largura, e zero erros de console/página em qualquer navegação.
    Inspecionei visualmente os screenshots de `pessoas/lista.html`,
    `participacoes/lista.html`, `formularios/categorias_lista.html` (confirmando view
    desktop 100% inalterada) — cartões renderizam com rótulo à esquerda/valor à direita,
    botões de ação agrupados sem buracos. Testei também `pessoas/detalhe.html` (tabelas
    "Termos aceitos" e "Participações" viram cartões, "Dados cadastrais" permanece tabela
    simples inalterada), `projetos/detalhe.html` e `projetos/perfil_detalhe.html` (cartões
    corretos, botões de ação agrupados), e `accounts/painel_permissoes.html` (confirmei via
    screenshot recortado que cada permissão vira um cartão com os 4 níveis rotulados
    corretamente e o estado do checkbox preservado). O caso da linha de correção do wizard
    foi validado isoladamente com uma página HTML estática carregando o `base.css` real
    (evitando rodar o fluxo completo de upload/associação do wizard sobre dados reais) —
    confirmou que a linha de correção renderiza em bloco normal, sem ser espremida pela
    regra genérica de card. Nenhum dado do banco foi alterado durante os testes.
  - **Segue sem commitar.** `git status` agora também inclui `static/css/base.css`,
    `accounts/views.py`, e os 16 templates listados acima com `data-label`/`td-acoes`
    (`pessoas/lista.html`, `pessoas/detalhe.html`, `pessoas/wizard_revisao.html`,
    `participacoes/lista.html`, `participacoes/detalhe.html`, `projetos/detalhe.html`,
    `projetos/perfil_detalhe.html`, `projetos/perfil_form.html`,
    `formularios/formularios_lista.html`, `formularios/formulario_form.html`,
    `formularios/variaveis_lista.html`, `formularios/categorias_lista.html`,
    `accounts/usuarios_lista.html`, `accounts/painel_permissoes.html`, `termos/lista.html`,
    `auditoria/lista.html`).
- **2026-08-17 (Logo virou imagem de verdade — antes era um círculo preto em CSS)** — O
  elemento de marca no cabeçalho (`.brand-mark`) nunca teve a logo de fato: era um
  `<span>` com `background:#121216` formando só um círculo preto sólido ao lado do texto
  "Qualy Vortice". O usuário forneceu o arquivo original da logo (espiral colorida +
  wordmark "Qualy Vortice") e pediu pra usar essa imagem em todas as telas do site.
  - Arquivo salvo pelo usuário em `static/img/imglogo.png` (384×164px, RGB sem
    transparência, fundo #1A1A1A — bem próximo do `--side:#0B0B0D` da sidebar, então
    funde quase sem borda visível ali; nas telas de fundo branco o badge escuro
    arredondado é intencional, mesma linguagem visual do resto da UI).
  - Como a imagem já traz o wordmark "Qualy Vortice" desenhado, troquei
    `<span class="brand-mark"></span><h1>Qualy Vortice</h1>` por uma única
    `<img src="{% static_v 'img/imglogo.png' %}" alt="Qualy Vortice" class="brand-logo">`
    — o `<h1>` separado foi removido pra não duplicar o nome (uma vez na imagem, outra em
    texto). Trocado nos 5 lugares que mostravam a marca: `templates/base.html` (sidebar,
    autenticado), `templates/accounts/login.html`, e as 3 telas públicas
    (`templates/publico/cadastro.html`, `cadastro_ok.html`, `link_invalido.html`).
    `accounts/login.html` precisou ganhar `{% load static_v %}` próprio (os outros 4 já
    carregavam a tag).
  - `static/css/base.css`: `.brand-mark` (círculo) virou `.brand-logo`
    (`height:40px;width:auto;border-radius:10px`, mesma sombra rosada que já existia).
    Removidas as regras mortas `.brand h1` e `.sidebar .brand h1` (não sobrou `<h1>` dentro
    de `.brand` em lugar nenhum).
  - Testado com Playwright: confirmei via `naturalWidth`/`complete` no DOM que a imagem
    carrega de fato (não é um link quebrado) na tela de login, na sidebar autenticada e na
    tela pública `link_invalido` (mesma estrutura de `cadastro.html`/`cadastro_ok.html`).
    Inspecionei os 3 screenshots visualmente: logo aparece nítida e proporcional nos três
    contextos (fundo escuro da sidebar, card branco do login, card branco centralizado da
    tela pública), cantos arredondados sem distorcer a imagem. Zero erro de rede/console.
  - **Segue sem commitar.** `git status` agora também inclui `static/css/base.css`,
    `templates/base.html`, `templates/accounts/login.html`,
    `templates/publico/cadastro.html`, `templates/publico/cadastro_ok.html`,
    `templates/publico/link_invalido.html`, e `static/img/imglogo.png` (novo, arquivo
    binário fornecido pelo usuário).
- **2026-08-17 (Ajustes finos da logo — sombra removida e fundo preto virou
  transparência)** — Dois retornos do usuário sobre a rodada anterior:
  1. **Sombra feia** — `.brand-logo` tinha herdado o `box-shadow:0 8px 20px
     rgba(242,41,91,.5)` do antigo `.brand-mark` (pensado pra um círculo pequeno de
     40px); aplicado na imagem retangular nova, virava um halo rosa borrado sem
     propósito, já que a própria arte já tem cor e brilho. Removido o `box-shadow`
     inteiro e reduzida a altura de 40px pra 36px (proporção mais discreta ao lado do
     texto de navegação da sidebar).
  2. **Fundo preto sólido** — `static/img/imglogo.png`, como fornecida, era RGB opaco com
     fundo #1A1A1A preenchendo o retângulo inteiro (sem canal alfa). Contra o card branco
     do login/cadastro público, isso aparecia como uma caixa preta em volta do desenho.
     Removido via script Python (Pillow, sem dependência nova — só usa a mesma lib já
     instalada no projeto): (a) `ImageChops.difference` contra uma imagem sólida da cor de
     fundo pra gerar uma máscara de alfa (pixel igual ao fundo → alfa 0; pixel do
     desenho/texto → alfa 255, com transição suave nas bordas anti-aliased); (b) correção
     de "des-mistura" nos pixels de borda parcialmente transparentes (`cor_real = (cor_obs
     - (1-alfa)·cor_fundo) / alfa`), pra tirar o resíduo escuro que sobra nas bordas quando
     a imagem original foi anti-aliased contra o preto — sem essa etapa a logo ficava com
     uma auréola cinza-escura sutil ao redor do espiral e das letras em fundos claros.
     `static/img/imglogo.png` foi sobrescrita com a versão RGBA (384×164, fundo
     transparente); nenhum outro arquivo mudou nessa etapa. `.brand-logo` perdeu também o
     `border-radius` (não fazia mais sentido recortar cantos de uma imagem sem caixa
     visível).
  - Testado: recompus a logo sobre 3 fundos de teste (branco, azul, e a cor da sidebar)
    pra confirmar que não sobrou nenhuma auréola/franja escura perceptível — ok nos três.
    Depois recarreguei a tela de login e a sidebar autenticada de verdade no navegador
    (Playwright): confirmado visualmente que o fundo preto sumiu por completo no card
    branco (só aparece o espiral colorido + "Qualy Vortice") e que na sidebar escura a
    logo continua se misturando bem ao fundo, sem sombra.
  - **Segue sem commitar.** Mesma lista de arquivos da rodada anterior — só o conteúdo de
    `static/img/imglogo.png` e mais uma pequena alteração em `static/css/base.css` (sombra
    e border-radius removidos, altura ajustada).
- **2026-08-17 (Logo centralizada e maior)** — Pedido rápido de ajuste: centralizar a logo
  e aumentar o tamanho. `.brand` (`static/css/base.css`) ganhou `justify-content:center`
  (antes só tinha `align-items:center`, então a imagem ficava grudada na esquerda do
  card/sidebar); `.brand-logo` subiu de 36px pra 56px de altura. Como centralizar virou
  comportamento padrão da classe, removi o `style="justify-content:center"` inline que
  `templates/publico/link_invalido.html` e `templates/publico/cadastro_ok.html` já tinham
  (redundante agora).
  - Testado com Playwright nos 3 layouts que usam `.brand`: tela de login (card estreito),
    sidebar autenticada (coluna de 250px) e tela pública centralizada
    (`link_invalido.html`) — logo aparece centralizada e proporcionalmente maior nos três,
    sem cortar nem estourar o container.
  - **Segue sem commitar.** Só `static/css/base.css`, `templates/publico/link_invalido.html`
    e `templates/publico/cadastro_ok.html` (remoção do style inline redundante) mudaram
    nessa rodada.
- **2026-08-17 (Cadastro público: perfil de Captação com mais de 3 categorias pede escolha
  de 3 antes de abrir os formulários)** — Implementa o mecanismo que tinha ficado pendente
  na rodada de `CategoriaFormulario` (documentado ali como "ainda não implementado, falta
  confirmar como deve funcionar"). O usuário definiu a regra: perfil de Captação cujos
  formulários cobrem mais de 3 categorias distintas pede pra pessoa escolher 3 antes de
  ver qualquer pergunta, e só os formulários dessas 3 categorias abrem pra responder.
  - **`pessoas/views.py`** — `NUM_CATEGORIAS_A_ESCOLHER = 3` (constante, caso vire
    configurável no futuro). `_categorias_disponiveis_para_escolha(perfil)` devolve as
    categorias distintas entre os formulários ativos do perfil, ordenadas por nome.
    `_form_dinamico_do_perfil` ganhou o parâmetro `categorias_ids=None` — quando não é
    `None`, filtra pra só os formulários cuja categoria está no conjunto (formulário
    **sem** categoria sempre aparece, categorizar é opcional e nunca deveria esconder uma
    pergunta). `cadastro_publico` calcula `exige_escolha_categorias` (`perfil.tipo ==
    CAPTACAO and` mais de 3 categorias disponíveis) logo no início; se `True`, tanto o GET
    quanto o POST exigem exatamente 3 ids válidos em `?categorias=` (GET) ou no campo
    `categorias` do POST — sem isso (link recém-aberto, ids inválidos/adulterados, POST
    forjado sem os 3), renderiza `publico/escolha_categorias.html` em vez do formulário.
    Perfil de Respostas, ou de Captação com 3 categorias ou menos, nunca vê essa tela —
    comportamento idêntico ao de antes desta rodada (testado explicitamente, ver abaixo).
  - **`templates/publico/escolha_categorias.html`** (novo) — reaproveita o layout de
    `login-card wide` das outras telas públicas. Texto exato pedido pelo usuário: "Escolha
    3 categorias que tem mais domínio para responder perguntas e participar de pesquisas:"
    (o "3" vem de `num_categorias` no contexto, não craveado no template). Checkboxes com
    `name="categorias"`; formulário `method="get"` — ao enviar, os ids escolhidos viram
    query string na mesma URL, e `cadastro_publico` já entende isso na próxima requisição.
  - **`static/js/escolha_categorias.js`** (novo) — só UX no cliente (a validação de
    verdade é sempre no servidor): contador "N de 3 selecionadas", desabilita as caixas
    não marcadas assim que 3 são escolhidas (evita marcar uma 4ª), botão "Continuar" só
    habilita com exatamente 3 marcadas.
  - **`templates/publico/cadastro.html`** — as categorias escolhidas viajam como campos
    ocultos (`<input type="hidden" name="categorias">`) dentro do próprio POST de envio do
    cadastro, pra sobreviver a um reenvio com erro de validação sem perder a escolha. Link
    "‹ Trocar categorias escolhidas" no topo (usa `{{ request.path }}`, sem querystring)
    volta pra tela de escolha.
  - **`projetos/models.py::Perfil.formularios_ordenados`** — ganhou
    `select_related("formulario__categoria")` (era só `select_related("formulario")`) pra
    não gerar uma query por formulário toda vez que algo lê `formulario.categoria` agora
    que isso passou a acontecer em todo carregamento da página pública.
  - `formularios/models.py::CategoriaFormulario` — docstring atualizada (não fala mais em
    "ainda não implementado").
  - Testado com Playwright contra o perfil real "Perfil Único Geral" (projeto "Captação de
    Pessoas Instagram", 9 categorias — Alimentação, Banco, Bebidas, Beleza, Entretenimento,
    Esporte, LifeStyle, Saúde, Tecnologia): (1) abrir o link mostra a tela de escolha com o
    texto pedido, contador "0 de 3", botão desabilitado; marcar 2 mantém desabilitado,
    marcar a 3ª habilita e desabilita as demais caixas; (2) "Continuar" leva ao formulário
    mostrando só as 3 seções escolhidas (Alimentação/Banco/Bebidas) mais "Perguntas
    Básicas" (fixo, não é afetado pela escolha); (3) `?categorias=` com ids inválidos/
    adulterados devolve a tela de escolha em vez do formulário; (4) link "Trocar
    categorias" volta pra tela de escolha; (5) preenchi um cadastro de teste completo
    escolhendo LifeStyle/Saúde/Tecnologia e enviei de verdade — no banco, só 3
    `RespostaFormulario` foram criadas (Tecnologia, Saúde, LifeStyle), nenhuma pras outras
    6 categorias não escolhidas; apaguei esse participante de teste (e sua participação e
    aceite de termo) depois de conferir, não sobrou nada; (6) perfil de Captação com 3
    categorias ou menos (projeto "Campanha Tenis Playwright") continua indo direto pro
    formulário completo, sem tela de escolha — confirma que não há regressão pra perfis
    que não se enquadram na regra. Zero erro de página/console em qualquer etapa.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/views.py`,
    `projetos/models.py`, `formularios/models.py`, `templates/publico/cadastro.html`,
    `templates/publico/escolha_categorias.html` (novo), `static/js/escolha_categorias.js`
    (novo).
- **2026-08-18 (Escolha de categorias vira configurável por perfil — quantidade, pergunta
  e texto de boas-vindas)** — Na rodada anterior a pergunta, a quantidade (3) e o texto
  ficaram fixos no código. O usuário pediu pra virarem editáveis por perfil, na própria
  tela de edição do perfil.
  - **`projetos/models.py::Perfil`** — 3 campos novos: `qtd_categorias_escolha`
    (`PositiveSmallIntegerField`, default `3`, `MinValueValidator(1)` — substitui a
    constante `NUM_CATEGORIAS_A_ESCOLHER` que existia em `pessoas/views.py`),
    `texto_escolha_categorias` (`CharField`, pode ficar em branco) e
    `texto_boas_vindas_categorias` (`TextField`, opcional, novo — texto que aparece acima
    da pergunta, só mostrado quando preenchido). Constante de módulo
    `TEXTO_ESCOLHA_CATEGORIAS_PADRAO` guarda o texto padrão (mesmo da rodada anterior) —
    usada tanto como `default=` do campo quanto na property nova
    `Perfil.texto_escolha_categorias_efetivo` (fallback pro padrão se o campo for salvo em
    branco, pra nunca sumir a pergunta da tela). Migração
    `projetos/migrations/0010_perfil_qtd_categorias_escolha_and_more.py` — só `AddField`
    (os 3 defaults cobrem os perfis já existentes, sem precisar de passo de dado).
  - **`projetos/forms.py::PerfilForm`** — ganhou os 3 campos, com `Textarea` pros dois de
    texto (`rows=2`) e labels/help_text explicando quando cada um tem efeito.
  - **`templates/projetos/perfil_form.html`** — novo fieldset "Escolha de categorias no
    cadastro público", entre o nome/tipo do perfil e a tabela de formulários, com uma nota
    deixando claro que só faz efeito em perfil de Captação com mais categorias que a
    quantidade escolhida.
  - **`pessoas/views.py::cadastro_publico`** — a constante `NUM_CATEGORIAS_A_ESCOLHER`
    saiu; toda a lógica de gatilho/validação usa `perfil.qtd_categorias_escolha` agora
    (efeito colateral útil: setar uma quantidade igual ou maior que o total de categorias
    do perfil desliga a exigência de escolha pra aquele perfil específico, sem precisar de
    um campo liga/desliga separado). `_contexto_escolha_categorias()` (novo, local à view)
    centraliza o contexto passado pra `escolha_categorias.html`, incluindo
    `texto_pergunta` (`perfil.texto_escolha_categorias_efetivo`) e `texto_boas_vindas`.
  - **`templates/publico/escolha_categorias.html`** — título da pergunta e (quando
    preenchido) o texto de boas-vindas acima dela agora vêm do contexto em vez de
    hardcoded no template.
  - Testado com Playwright contra o perfil real "Perfil Único Geral": (1) tela de edição
    mostra os 3 campos novos pré-preenchidos com os valores atuais (quantidade 3, pergunta
    padrão, boas-vindas em branco); (2) mudei quantidade pra 2, preenchi um texto de
    boas-vindas e uma pergunta customizada, salvei — confirmado no banco que persistiu;
    (3) reabri o link público do perfil: texto de boas-vindas aparece acima da pergunta
    customizada, contador mostra "0 de 2 selecionadas", botão habilita com exatamente 2
    marcadas (não mais 3) e desabilita a 3ª caixa ao atingir o limite — tudo reagindo à
    nova quantidade configurada; (4) formulário final mostrou só as 2 categorias
    escolhidas. Restaurei o perfil pros valores padrão originais (quantidade 3, texto
    padrão, boas-vindas vazio) depois de confirmar — não sobrou alteração de teste.
    `makemigrations --check --dry-run` limpo antes e depois de aplicar a migração.
  - **Segue sem commitar.** `git status` agora também inclui `projetos/forms.py`,
    `projetos/migrations/0010_perfil_qtd_categorias_escolha_and_more.py` (novo),
    `templates/projetos/perfil_form.html`, além dos arquivos já modificados de
    `projetos/models.py`, `pessoas/views.py` e `templates/publico/escolha_categorias.html`
    (que já apareciam no `git status` da rodada anterior).
- **2026-08-18 (Detalhe da participação: botão "Ver respostas" abre modal com o
  formulário respondido completo)** — Até aqui, a única forma de ver as respostas de um
  formulário na tela da participação era clicar em "Editar respostas" e navegar pra uma
  página separada. Pedido do usuário: um botão que abra um modal ali mesmo, mostrando
  todas as respostas daquele formulário sem sair da tela.
  - **`participacoes/views.py::detalhe`** — pra cada item de `formularios_do_projeto` que
    já tem `RespostaFormulario`, monta também `linhas_leitura` chamando
    `formularios.respostas.construir_form_resposta(formulario,
    dados_iniciais=resposta.respostas_variaveis, somente_leitura=True)` — o mesmo
    renderizador dinâmico usado em `formulario_visualizar` (a prévia de formulário), só que
    agora com os valores reais da resposta como `initial` em vez de vazio. Item sem
    resposta (`Pendente`) fica com `linhas_leitura=None` (não monta form dinâmico à toa).
  - **`templates/participacoes/detalhe.html`** — botão "Ver respostas" (`btn-ghost btn-sm`,
    só aparece quando `item.resposta` existe) ao lado de "Editar respostas"/"Responder" na
    coluna de ações; abre `QVModal.abrir('mVer<N>')`. Um modal por formulário respondido é
    renderizado logo abaixo da tabela (`.modal.wide`, novo — 760px em vez dos 640px
    padrão, mais confortável pro `.form-row` de perguntas), reaproveitando o mesmo layout
    label+campo de `formulario_visualizar.html`. Como o modal já carrega os campos
    desabilitados com o valor real (via Django `disabled=True` + `initial=`), inclusive o
    widget de múltipla escolha (`DropdownCheckboxSelectMultiple`) mostra corretamente
    quantas opções foram marcadas e quais são, só sem poder alterar — sem precisar de
    nenhum JS novo, `dropdown_multiselect.js` já é carregado globalmente em `base.html`.
    `{% block scripts %}` simplificado pra sempre carregar `modal.js` (antes só carregava
    se `pode_avaliar`; agora o modal de "Ver respostas" também depende dele,
    independentemente da permissão de avaliação).
  - **`static/css/base.css`** — `.modal.wide{max-width:760px}` (novo, ao lado do já
    existente `.modal.slim`).
  - Testado com Playwright contra a participação real de Lucas Couto (`/participacoes/78/`,
    9 formulários todos respondidos, do BP.xlsx): (1) os 9 botões "Ver respostas"
    aparecem, um por formulário; (2) abri o modal de "Perguntas Básicas de Alimentação" —
    título certo, todos os campos aparecem com o valor realmente salvo (ex.: "Sou
    apaixonado(a) por gastronomia", "Todos os dias"); (3) os 3 campos de múltipla escolha
    desse formulário mostram o rótulo certo ("4 selecionadas", "6 selecionadas", "5
    selecionadas") e, abrindo o dropdown, exatamente as opções marcadas batem com o que
    foi respondido (ex.: Gastronomia/Restaurantes/Receitas/Tendências gastronômicas),
    todas as caixas desabilitadas (nenhuma clicável); (4) botão "Fechar" e o X fecham o
    modal normalmente; (5) confirmei que o modal de "Avaliar" (que já existia antes)
    continua abrindo normalmente depois da simplificação do `{% block scripts %}`. Zero
    erro de página/console em qualquer etapa.
  - **Segue sem commitar.** `git status` agora também inclui `participacoes/views.py`,
    `templates/participacoes/detalhe.html`, `static/css/base.css`.
- **2026-08-18 (Dashboards: "Classe social" voltou a contar de verdade, e "Segmento" virou
  "Categoria" — lista as categorias cadastradas de verdade)** — Dois problemas relatados
  pelo usuário nos dois dashboards ("Visão participantes" e "Visão por segmento"):
  1. **Classe social sempre em zero** — `core/dashviz.py::dados_participantes_dashboard`
     mandava `p.get_renda_individual_display()` (ex.: `"A — a partir de R$ 9.738"`) no
     campo `cls`, mas `static/js/dashboard.js`/`dashboard_segmento.js` só reconhecem 3
     rótulos fixos (`CLS_ORDEM = ["Classes A/B", "Classe C", "Classes D/E"]`). Isso ficou
     dessincronizado desde a rodada do BP.xlsx, quando `renda_individual` passou a usar
     códigos A-E com rótulo próprio (["Faixa de renda individual/familiar vira 2 perguntas
     separadas"], SDD de rodada anterior) — o cliente nunca mais bateu o rótulo esperado
     com o que o servidor mandava, e todo gráfico de classe social ficava zerado
     independente de quantos participantes tivessem `renda_individual` preenchida. Corrigido
     com `BUCKETS_CLASSE_SOCIAL` (novo, em `core/dashviz.py`): mapeia os códigos A/B → 
     `"Classes A/B"`, C → `"Classe C"`, D/E → `"Classes D/E"` a partir do código
     (`p.renda_individual`), não do rótulo por extenso — bate exatamente com o que o JS
     espera.
  2. **"Segmento" → "Categoria do Perfil"** — o agrupamento dos dois dashboards vinha de
     `Projeto.Segmento` (`Saúde/Cosméticos/Alimentação/Banco/Tecnologia`, lista fixa de 5
     no código, atributo do Projeto). Como pedido, isso virou a Categoria de Formulário
     (`CategoriaFormulario`, cadastrada em "Configurações de Formulários › Categorias") —
     um participante agora "pertence" a uma categoria por ter de fato **respondido** um
     formulário categorizado naquela categoria (`RespostaFormulario.formulario.categoria`),
     não por ter sido recrutado num projeto com aquela tag comercial. `categorias_disponiveis()`
     (nova, em `core/dashviz.py`) lista todas as `CategoriaFormulario` cadastradas (ordem
     alfabética) — essa é a lista de abas/pills dos dois dashboards agora, então cresce ou
     encolhe junto com o cadastro de categorias, sem precisar mexer em código pra isso.
     `dados_participantes_dashboard` trocou o campo `segs` (nome antigo, ligado a segmento)
     por `cats`, computado via `RespostaFormulario.objects.filter(participacao__participante__in=...)
     .values_list("participacao__participante_id", "formulario__categoria__nome")`.
     `core/views.py` (`home` e `dashboard_segmento`) passam `categorias_json` (de
     `categorias_disponiveis()`) pro contexto, embutido via `json_script` em
     `id="categorias-disponiveis"` (mesmo padrão do `dados-participantes`).
     `static/js/dashboard.js` e `dashboard_segmento.js`: `SEGMENTOS` deixou de ser array
     fixo e passou a ler esse JSON; `SEG_COR` (mapa de cor por nome fixo) virou `corSeg()`
     — cor por posição numa paleta que se repete (mesmo padrão de `PROF_PALETA`), já que os
     nomes das categorias não são mais conhecidos em tempo de escrita do código. Todo texto
     visível de "segmento" nas duas telas virou "categoria" (título, breadcrumb, subtítulo,
     cabeçalhos de painel, rodapés de KPI, item do menu lateral "Visão por segmento" →
     "Visão por categoria") — só os identificadores internos (nome da URL/rota, nome do
     arquivo JS, classe CSS `.seg-tab`, IDs como `segTabs`/`sgComp`) ficaram como estavam,
     por não serem visíveis e trocar deles não mudar nada pro usuário. **Não mexi** no campo
     `Projeto.segmento` em si nem nos lugares que ainda o mostram fora do dashboard (lista/
     detalhe/formulário de projeto) — o pedido foi especificamente sobre os dois dashboards.
  - Testado com Playwright, autenticado: (1) "Visão participantes" — "Classe social (faixa
    de renda)" agora mostra contagem real (1 em "Classes A/B", antes 0/0/0 nas três barras);
    "Sobreposição entre categorias" lista as 9 categorias cadastradas de verdade
    (Alimentação, Banco, Bebidas, Beleza, Entretenimento, Esporte, LifeStyle, Saúde,
    Tecnologia) em vez dos 5 segmentos fixos antigos, com Venn mostrando corretamente 1
    participante nas 3 categorias pré-selecionadas ao mesmo tempo; (2) "Visão por
    categoria" — as 9 abas aparecem com contagem real, cliquei em "Banco": KPIs, "Classe
    predominante" (agora "Classes A/B" em vez de "—"), "Comparativo entre categorias" (9
    barras coloridas por paleta) e "Classe social" (barra real em vez de zero) todos batendo
    com os dados de verdade; confirmei que os números de cada categoria refletem
    exatamente quem respondeu formulário daquela categoria (verifiquei no shell que a
    diferença em relação ao antigo "Segmento: Banco" — que somava 7 participantes de um
    projeto de teste antigo com um formulário nunca categorizado — é esperada e correta,
    não uma regressão). Zero erro de página/console em qualquer tela.
  - **Segue sem commitar.** `git status` agora também inclui `core/dashviz.py`,
    `core/views.py`, `templates/core/home.html`, `templates/core/dashboard_segmento.html`,
    `templates/base.html`, `static/js/dashboard.js`, `static/js/dashboard_segmento.js`.
- **2026-08-18 (Classe social: 5 barras de verdade, uma por faixa do formulário — não mais
  3 buckets fixos)** — A correção anterior consertou a contagem zerada, mas ainda juntava
  os 5 códigos de `renda_individual` (A-E) em 3 buckets hardcoded ("Classes A/B", "Classe
  C", "Classes D/E") herdados do protótipo original. O usuário pediu pra usar a quantidade
  de faixas de verdade e casar com o que o formulário de participante realmente pergunta —
  5 faixas (A a E), não 3.
  - `core/dashviz.py::faixas_renda_disponiveis()` (nova, mesmo padrão de
    `categorias_disponiveis()`) devolve `Participante.FaixaRendaIndividual.choices` direto
    — `[("A", "A — a partir de R$ 9.738"), ("B", ...), ...]`, na ordem do cadastro. Removido
    `BUCKETS_CLASSE_SOCIAL` (o mapeamento pra 3 buckets); `dados_participantes_dashboard`
    agora manda `"cls": p.renda_individual` — o código bruto (A-E ou `None`), sem
    transformação nenhuma no servidor.
  - `core/views.py` (`home` e `dashboard_segmento`) passam `faixas_renda_json` pro
    contexto; `templates/core/home.html` e `dashboard_segmento.html` embutem via
    `{{ faixas_renda_json|json_script:"faixas-renda-disponiveis" }}` (mesmo padrão de
    `categorias-disponiveis`).
  - `static/js/dashboard.js` e `dashboard_segmento.js`: `CLS_ORDEM` deixou de ser o array
    fixo de 3 buckets e passou a ler essa lista de pares `[codigo, rótulo]` do JSON — o
    gráfico "Classe social" agora desenha uma barra por faixa cadastrada (5 hoje, mas
    acompanha sozinho se o formulário ganhar/perder faixas no futuro). Cada barra mostra só
    o código (A/B/C/D/E — cabe no espaço apertado do `.vbar`) com o rótulo completo
    (`"B — R$ 4.869 a R$ 9.737"`) como `title` (tooltip ao passar o mouse, mesmo padrão já
    usado nos tiles do mapa por estado). `CLS_LABEL` (novo, mapa código→rótulo) é usado pra
    mostrar o rótulo completo nos dois lugares com mais espaço: o chip de filtro ativo
    ("Visão participantes") e o KPI "Classe predominante" ("Visão por categoria") — só o
    rótulo curto (código) aparece embaixo de cada barrinha.
  - Corrigido no processo: a primeira versão do trecho de `dashboard_segmento.js` chamava
    `esc(rotulo)` pro `title` da barra, mas esse arquivo nunca teve essa função (só existe
    em `dashboard.js`) — teria quebrado com `ReferenceError` assim que a tela de categoria
    carregasse. Pego antes de subir pro usuário: como o resto do arquivo já insere texto
    sem escapar (rótulos vêm de `choices` do model, não de entrada de usuário), troquei
    pra usar `rotulo` direto, consistente com o padrão já usado ali (ex.: `title` das
    barras de gênero).
  - Testado com Playwright: (1) "Visão participantes" — "Classe social (faixa de renda)"
    agora mostra 5 barras (A, B, C, D, E) com o rótulo completo de cada uma no tooltip;
    cliquei na barra "B" (única com dado real) e o chip de filtro mostrou o rótulo completo
    "B — R$ 4.869 a R$ 9.737"; (2) "Visão por categoria" (aba Banco) — mesmas 5 barras,
    contagem batendo (1 em B), e o KPI "Classe predominante" mostrando o rótulo completo em
    vez do código sozinho. Zero erro de página/console nas duas telas.
  - **Segue sem commitar.** `git status` agora também inclui as mesmas mudanças da rodada
    anterior em `core/dashviz.py`, `core/views.py`, `templates/core/home.html`,
    `templates/core/dashboard_segmento.html`, `static/js/dashboard.js`,
    `static/js/dashboard_segmento.js`.
- **2026-08-18 (Gênero: mesmo bug da classe social, mais registros legado com código de
  gênero desatualizado)** — Dois pedidos do usuário: (1) o KPI de gênero também estava
  desatualizado; (2) tanto gênero quanto faixa salarial tinham "registros legado" que
  precisavam ser atualizados pra caber nas informações novas.
  1. **Mesmo bug do "Classe social" da rodada anterior, agora em "Gênero"** —
     `GEN_ORDEM`/`GEN_COR` em `static/js/dashboard.js`/`dashboard_segmento.js` estavam
     hardcoded com os 4 rótulos **antigos** (`Feminino/Masculino/Outro/Prefere não
     informar`) de antes da migração `pessoas/migrations/0008_campos_perfilamento_bp.py`,
     que realinhou `Participante.Genero` pras 7 opções do BP.xlsx (Mulher cisgênero, Homem
     cisgênero, Mulher transgênero, Homem transgênero, Pessoa não binária, Outra
     identidade de gênero, Prefiro não responder) — igual ao que tinha acontecido com
     "Classe social", ninguém tinha atualizado o dashboard nessa hora, então nenhum
     participante batia com as 4 opções esperadas e o gráfico ficava zerado. Corrigido com
     o mesmo padrão: `core/dashviz.py::generos_disponiveis()` (nova) devolve os rótulos de
     `Participante.Genero.choices` de verdade; `core/views.py` passa `generos_json`;
     `templates/core/home.html`/`dashboard_segmento.html` embutem via
     `json_script:"generos-disponiveis"`; os dois JS leem `GEN_ORDEM` desse JSON em vez do
     array fixo, com cor por posição numa paleta (`corGen()`, mesmo padrão de `corSeg()`)
     em vez do mapa fixo por nome.
  2. **Registros legado de gênero corrigidos de verdade (migração de dados)** — diferente
     do bug de exibição acima, aqui o **dado salvo no banco** estava desatualizado: a
     migração 0008 trocou as opções de `genero` via `AlterField` (que só muda a lista de
     opções válidas pro Django, não toca em dado já gravado) — participantes cadastrados
     antes dela ficaram com o código antigo (`FEMININO`/`MASCULINO`) gravado, que não bate
     com nenhuma das 7 opções atuais. Conferido no banco: 8 dos 9 participantes cadastrados
     tinham código antigo (`FEMININO`: 2, `MASCULINO`: 6) — só quem foi cadastrado depois
     da migração 0008 (1 participante) já tinha código novo. Nova migração de dados
     `pessoas/migrations/0010_corrige_genero_legado.py` (`RunPython`) atualiza esses
     registros pro código novo mais próximo: `FEMININO→MULHER_CIS`, `MASCULINO→HOMEM_CIS`
     (não havia pergunta sobre esse recorte no cadastro antigo — cisgênero é o padrão mais
     razoável pra "Feminino"/"Masculino" sem mais contexto), `OUTRO→OUTRA`,
     `NAO_INFORMA→NAO_RESPONDE`. Aplicada e conferida: os 9 participantes agora têm só
     códigos válidos (`HOMEM_CIS`: 7, `MULHER_CIS`: 2).
  3. **Faixa salarial legado — sem dado pra recuperar, diferente de gênero** — fui conferir
     o mesmo tipo de problema pra `renda_individual`/`renda_familiar` e é um caso
     diferente: a migração 0008 não só trocou as opções da faixa de renda, ela **removeu o
     campo antigo inteiro** (`faixa_renda`, `RemoveField`) e criou dois campos novos do
     zero (`AddField renda_individual`/`renda_familiar`) — sem nenhum passo de conversão
     entre eles. `RemoveField` derruba a coluna do banco de vez; o valor que cada
     participante tinha em `faixa_renda` **não existe mais em lugar nenhum do sistema**
     (não sobrou backup, snapshot ou log com esse dado). Diferente do gênero (onde o
     código antigo continuava salvo, só não batia mais com a lista de opções), aqui não há
     nada pra "atualizar pra caber" — a informação original foi perdida na migração 0008,
     antes desta sessão. Os 8 participantes com `renda_individual`/`renda_familiar` em
     branco são conferidos no banco como sendo participantes de teste desta mesma sessão
     (nomes como "Wizard Dinamico Teste", "Ana Wizard Teste" etc.), não dados reais — fica
     como está (em branco, o que já é tratado corretamente pelo dashboard desde a correção
     anterior) a menos que o usuário quiser preencher um valor de exemplo pra esses
     participantes de teste especificamente.
  - Testado com Playwright: "Visão participantes" — "Gênero" agora mostra as 7 opções
    reais com contagem certa (Mulher cisgênero 2 · 22%, Homem cisgênero 7 · 78%, as outras
    5 em 0%, batendo com os 9 participantes); "Visão por categoria" (aba Banco) — mesma
    lista de 7 opções, "Gênero predominante" mostrando "Homem cisgênero" em vez de vazio.
    Zero erro de página/console.
  - **Segue sem commitar.** `git status` agora também inclui `core/dashviz.py`,
    `core/views.py`, `templates/core/home.html`, `templates/core/dashboard_segmento.html`,
    `static/js/dashboard.js`, `static/js/dashboard_segmento.js`,
    `pessoas/migrations/0010_corrige_genero_legado.py` (novo — já aplicada no banco local).
- **2026-08-18 (Badge de consentimento LGPD passa a distinguir versão vigente de versão
  substituída)** — O usuário perguntou por que o consentimento aparecia verde com
  "v2026.2" já existindo uma "v2026.3". Investigando: `v2026.3` é de fato a versão vigente
  hoje (`v2026.2` está com status `SUBSTITUIDA` desde que a nova foi publicada) — os 9
  participantes da base aceitaram todos a `v2026.2`, então tecnicamente nenhum tem consentimento
  pra versão vigente atual. O badge, porém, sempre mostrava verde pra qualquer
  `consentimento_versao` preenchida, sem checar se aquela versão ainda é a vigente ou já
  foi substituída — não distinguia "em dia" de "desatualizado".
  - **Importante, decisão consciente**: não toquei em `consentimento_versao` de ninguém.
    Atualizar esse campo pra apontar pra `v2026.3` sem a pessoa ter de fato visto e aceito
    o novo texto seria fabricar consentimento — problema sério de LGPD, não uma correção de
    dado. `VersaoTermo` já guarda o histórico completo de aceite em `AceiteTermo` (log
    imutável), então isso não é um caso de "registro legado com dado errado" como o do
    gênero da rodada anterior — é a ausência real de consentimento pra versão atual, que só
    a própria pessoa (ou um operador em nome dela, através do fluxo de cadastro normal)
    pode resolver aceitando de novo.
  - **O que mudei**: só a exibição, pra ficar honesta sobre esse estado.
    `templates/pessoas/lista.html` e `templates/pessoas/detalhe.html` — o badge de
    consentimento agora checa `consentimento_versao.status`: `"VIGENTE"` continua verde
    (só o código da versão); qualquer outro status (`SUBSTITUIDA`/`EXPIRADA`) vira âmbar
    com "· desatualizado" e um `title` explicando. `pessoas/views.py` (`lista` e
    `detalhe`) ganharam `select_related("consentimento_versao")` nas duas queries — sem
    isso, cada linha da lista já disparava uma query separada só pra buscar a versão
    (N+1 pré-existente, aproveitei que já estava mexendo ali).
  - Testado com Playwright: os 9 participantes (todos com `v2026.2`, a versão substituída)
    agora mostram badge âmbar "v2026.2 · desatualizado" em vez de verde, tanto na listagem
    quanto no detalhe individual — confirmado visualmente num viewport largo o bastante
    pra não cortar o texto mais longo do badge. Zero erro de página.
  - **Segue sem commitar.** `git status` agora também inclui `templates/pessoas/lista.html`,
    `templates/pessoas/detalhe.html`, `pessoas/views.py`.
- **2026-08-18 (Link público pra renovar termo/contrato desatualizado)** — Consequência
  direta da rodada anterior: agora que o sistema sabe distinguir "aceitou a versão
  vigente" de "aceitou uma versão substituída", o usuário pediu uma forma de resolver
  isso — um link que a equipe manda pra pessoa, ela lê o texto novo e aceita, confirmando
  a identidade por CPF (sem travar no e-mail, já que a mesma pessoa pode ter mais de um
  ao longo do tempo).
  - **`pessoas/links.py`** — `gerar_token_renovacao_termo`/`ler_token_renovacao_termo`
    (mesmo padrão assinado de `gerar_token_captacao`, salt próprio). O token guarda
    `participante_id` + `termo_id`, não uma versão específica — assim o link não expira
    nem fica órfão se o documento for atualizado de novo depois de gerado: sempre mostra
    a versão vigente *no momento em que é aberto*, mesma filosofia do link de cadastro
    público.
  - **`pessoas/views.py`** — `_termos_pendentes_renovacao(request, participante,
    aceites_termos)` (nova): a partir da lista de `AceiteTermo` já carregada pra tabela
    "Termos aceitos" (sem consulta extra — o primeiro aceite de cada `termo_id` na lista já
    é o mais recente, dado que `AceiteTermo.Meta.ordering = ["-aceito_em"]`), separa os
    documentos onde a versão aceita não é mais a vigente. `_link_renovacao_termo` monta a
    URL completa (mesmo padrão de `_link_captacao` em `projetos/views.py`). `detalhe`
    passa `termos_pendentes` pro contexto. Nova view pública `renovar_termo(request,
    token)`: decodifica o token, resolve `termo.versao_vigente` na hora; se a pessoa já
    tiver um `AceiteTermo` pra essa versão específica (link reaberto depois de já ter
    aceitado), mostra direto a tela de "você já está em dia" em vez do formulário — sem
    duplicar aceite. No POST, valida CPF (`normalizar_cpf`, comparação exata com o
    cadastro — único campo que bloqueia) e, se bater, grava um `AceiteTermo`
    (`origem=PUBLICO`, mesma função `registrar_aceite` que o cadastro público já usa). Se o
    termo em questão for especificamente o de Consentimento LGPD (único tipo com um campo
    dedicado — `Participante.consentimento_versao`), esse campo também é atualizado; os
    demais tipos de termo/contrato ficam só no histórico de `AceiteTermo` (não têm um
    ponteiro "versão atual" próprio no model de Participante, então não têm o que
    atualizar além do log).
  - **`pessoas/forms.py::RenovarTermoForm`** — `cpf` (comparado no view, não aqui — o form
    só garante que não veio vazio), `email` (`EmailField`, só formato — nunca comparado
    com o cadastro, de propósito, exatamente o pedido do usuário) e `aceite`
    (`BooleanField` obrigatório).
  - **Templates novos**: `templates/publico/renovar_termo.html` (mostra o nome da pessoa,
    o texto completo da versão vigente, dica com CPF/e-mail mascarados pra ajudar a
    lembrar qual usar — mesma máscara já usada em `Participante.cpf_mascarado`/
    `email_mascarado` —, e o formulário CPF+e-mail+aceite) e
    `templates/publico/termo_renovado_ok.html` (duas variantes de texto: acabou de
    aceitar, ou já estava em dia).
  - **`templates/pessoas/detalhe.html`** — novo painel "Documentos pendentes de
    renovação" (só aparece quando `termos_pendentes` não é vazio), listando cada
    documento com a versão aceita, a versão vigente, e um botão "Copiar link de
    renovação" — reaproveita o `data-copiar`/`copiar_link.js` já usado pro link de
    cadastro público de perfil (carregado globalmente em `base.html`, nada novo pra
    incluir).
  - Testado com Playwright de ponta a ponta, usando o participante real Lucas Couto (que
    tinha `v2026.2 · desatualizado` desde a rodada anterior): (1) painel "Documentos
    pendentes de renovação" aparece no detalhe dele com o botão de copiar link; (2) abri o
    link gerado numa aba sem sessão de login — carrega a tela pública com nome, texto da
    versão vigente, e os campos; (3) tentei aceitar com CPF errado — erro "Esse CPF não
    confere com o cadastro", nada foi gravado; (4) aceitei de novo com o CPF certo e um
    e-mail **diferente** do cadastrado — aceite registrado normalmente (confirmando que o
    e-mail não trava, como pedido); (5) reabri o mesmo link depois de já ter aceitado —
    mostrou "Você já está em dia" em vez do formulário; (6) voltando pra tela do
    participante: painel de pendentes sumiu, badge de consentimento virou verde `v2026.3`,
    "Termos aceitos" ganhou uma linha nova com origem "Cadastro público". Desfiz essa
    mudança de teste depois de confirmar (apaguei o aceite criado e restaurei
    `consentimento_versao` pra `v2026.2`) — não sobrou alteração de teste no participante
    de demonstração. `makemigrations --check --dry-run` limpo (nenhuma mudança de model
    nessa rodada). Zero erro de página em qualquer etapa.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/links.py`,
    `pessoas/forms.py`, `pessoas/views.py`, `pessoas/urls.py`,
    `templates/pessoas/detalhe.html`, `templates/publico/renovar_termo.html` (novo),
    `templates/publico/termo_renovado_ok.html` (novo).
- **2026-08-18 ("Associar pessoa"/"Associar em lote" também na tela do projeto, não só
  dentro de cada perfil)** — O usuário perguntou onde estavam essas duas ações (association
  individual e em lote/Excel) — já existiam, mas só dentro da tela de cada Perfil
  (`projetos/perfil_detalhe.html`), obrigando a entrar em "Ver" antes de conseguir
  associar alguém. Pedido: deixar isso disponível direto na tela do Projeto.
  - **`projetos/views.py::detalhe`** — passou a calcular `pode_associar`
    (`participacoes.mover_etapa`, mesma permissão já usada em `perfil_detalhe`) e mandar
    pro contexto.
  - **`templates/projetos/detalhe.html`** — a tabela "Perfis" já tinha uma coluna de ações
    por linha (Copiar link/Editar/Ver); ganhou mais dois botões nessa mesma coluna, gated
    por `pode_associar`: "＋ Associar pessoa" (vai pra `participacoes:nova?perfil=<id>`,
    já chega com o perfil daquela linha pré-selecionado — mesma URL que o botão do perfil
    já usava) e "⬆ Em lote" (vai direto pra `projetos:perfil_associar_lote` daquele
    perfil). Não criei rota nem view nova — só expus os dois links que já existiam um
    nível mais acima, já que cada linha da tabela já sabe exatamente a qual perfil se
    refere (não tem ambiguidade de "qual perfil" pra resolver, diferente de tentar pôr
    esses botões soltos no topo da página, fora da tabela, quando o projeto tem mais de um
    perfil).
  - Testado com Playwright: os 5 botões aparecem na linha do perfil ("Associar pessoa",
    "Em lote", "Copiar link", "Editar", "Ver"); "Associar pessoa" leva pro formulário de
    associação com o campo de perfil já pré-selecionado certo; "Em lote" leva pra tela de
    upload de Excel do perfil certo. Testado também em viewport mobile (375px) — os 5
    botões quebram em duas linhas dentro do cartão sem sobrepor nem cortar nada, mesmo
    padrão de `flex-wrap` já usado nas outras telas. Zero erro de página.
  - **Segue sem commitar.** `git status` agora também inclui `projetos/views.py`,
    `templates/projetos/detalhe.html`.
- **2026-08-18 (Wizard de importação: revisar/editar qualquer linha antes de enviar +
  "marcar coluna toda" no consentimento)** — Na tela de Revisão (último passo do wizard de
  importação em lote), só linha com erro ganhava um mini-formulário editável; linha válida
  só mostrava um resumo fixo, sem chance de ajustar nada antes de concluir. Pedido do
  usuário: poder revisar/editar qualquer linha, e um jeito rápido de marcar consentimento
  pra todas de uma vez.
  - **Descoberta importante que simplificou a implementação**: o back-end
    (`pessoas/views.py::wizard_revisao`, POST) já lia `dados_<indice>-<campo>` do POST pra
    **qualquer** índice de linha, não só as com erro — o comentário no código já dizia
    isso ("uma linha já válida não manda nenhum `dados_<indice>_*` e mantém o que já
    tinha"). Ou seja, o mecanismo de edição já era genérico; só a tela (GET) que só
    montava o formulário (`ParticipanteWizardForm(initial=..., prefix=f"dados_{indice}")`)
    pra linha com erro. A mudança de back-end virou uma linha só: tirar o `if not
    linha["valido"]:` que gatava a montagem do form, passando a montar pra toda linha.
  - **`templates/pessoas/wizard_revisao.html`** — cada linha ganhou um botão
    "Editar"/"Fechar" (nova coluna de ações) que abre/fecha a mesma linha de correção que
    já existia pra erro — só que agora **toda** linha tem uma, começando fechada se for
    válida (evita a tela virar um formulário gigante por padrão) e já aberta se tiver erro
    (continua precisando de atenção imediata, sem exigir clique extra). Texto de
    instrução dentro da linha muda conforme o caso ("Confira ou ajuste..." pra válida,
    "Corrija os campos..." pra erro).
  - **`static/css/base.css`** — `.wiz-linha-correcao{display:none}` /
    `.wiz-linha-correcao.wiz-aberta{display:table-row}` (e a versão mobile equivalente
    dentro do `@media`, já que lá a linha vira bloco de cartão, não `table-row`) — antes a
    linha de correção só existia no HTML quando precisava aparecer; agora ela sempre
    existe, e uma classe controla se está visível.
  - **`static/js/wizard_revisao.js`** (novo) — dois comportamentos pequenos, sem
    framework: (1) o clique no botão "Editar"/"Fechar" alterna a classe `wiz-aberta` da
    linha correspondente (via `data-toggle-linha="correcao-N"`) e troca o próprio texto do
    botão; (2) o checkbox "Marcar consentimento LGPD de todas as linhas" marca/desmarca
    todas as caixas `consentimento_*` de uma vez — e se alguém desmarcar uma linha
    manualmente depois, o checkbox mestre se desmarca sozinho (não fica "mentindo" que
    tudo está marcado).
  - **Pegadinha resolvida durante o teste**: a primeira versão colocava o checkbox
    "marcar coluna toda" dentro do `<th>` da coluna Consentimento LGPD — funciona no
    desktop, mas o `<thead>` inteiro **some** no layout de cartão do mobile (regra já
    existente de tabela responsiva), deixando o controle inacessível em tela pequena.
    Corrigido movendo o checkbox pra uma barra própria acima da tabela, fora do
    `<thead>` — sempre visível, em qualquer largura.
  - Testado criando sessões de wizard sintéticas via shell (mais rápido que preencher
    ~15 campos × N linhas manualmente pela wizard inteira) e abrindo a tela de Revisão com
    o cookie de sessão direto no Playwright: (1) linhas válidas nascem fechadas com botão
    "Editar", linha com erro nasce aberta com botão "Fechar"; (2) clicar em "Editar" abre a
    linha e pré-preenche o formulário com os dados originais; (3) editei o telefone de uma
    linha válida, marquei o consentimento e concluí a importação — **conferido no banco
    que o telefone editado (não o original) foi o que ficou salvo**, provando que a edição
    de linha válida realmente é aplicada, não só visual; (4) "marcar coluna toda" marca
    todas as caixas, e desmarcar uma individualmente desmarca o checkbox mestre sozinho;
    (5) testado em viewport mobile (375px) — checkbox de marcar tudo visível e funcional,
    coluna de ações e formulário de edição empilham corretamente no cartão. Apaguei o
    participante e as sessões de teste depois de confirmar — não sobrou nada de teste no
    banco. `makemigrations --check --dry-run` limpo (nenhuma mudança de model). Zero erro
    de página em qualquer etapa.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/views.py`,
    `templates/pessoas/wizard_revisao.html`, `static/css/base.css`,
    `static/js/wizard_revisao.js` (novo).
- **2026-08-19 (3 bugs do lote legado corrigidos — a partir da análise do
  `teste_import.xlsx` do usuário)** — O usuário importou esse arquivo como lote legado
  no perfil "Consumidores de Cerveja Premium" (projeto Moments) e reportou 3 problemas.
  Analisei o arquivo real e o código do caminho legado (`pessoas/matching.py`,
  `pessoas/wizard_csv.py`, `pessoas/views.py::wizard_revisao`) pra achar a causa de cada
  um.
  1. **CPF vazio/inválido não pode ser usado pra casar nem substituir dado de
     participante** — `preparar_linha_legado()` já tratava CPF **vazio** corretamente
     (nunca usava pra achar/substituir ninguém, e o participante existente tinha o CPF
     dele preservado via `restaurar_campos_vazios()`). O que faltava era CPF **presente
     mas inválido** (dígito verificador errado, tipo "111.111.111-11") — esse passava
     direto sem checagem nenhuma, podia ser usado pra tentar casar com alguém e podia ser
     gravado como se fosse um CPF de verdade. Corrigido: `preparar_linha_legado()` agora
     valida CPF presente com `validar_cpf()` (mesmo validador de dígito verificador já
     usado no resto do sistema) — se falhar, trata exatamente como se tivesse vindo em
     branco (vira placeholder, marca `cadastro_incompleto`), nunca chega em
     `encontrar_participante_existente()` nem é gravado no cadastro.
  2. **Perguntas do formulário do perfil (ex.: "Perguntas Básicas de Bebidas") nunca
     entravam no lote legado** — achei a causa exata: em `wizard_revisao` (POST), o ramo
     `if legado:` sempre mandava `forms_dinamicos = []` **incondicionalmente**, mesmo que
     `ler_planilha()` já tivesse lido certinho as colunas de resposta (o cabeçalho da
     planilha bate exatamente com o nome das variáveis do formulário — conferido no
     banco). O laço que grava `RespostaFormulario` só rodava pro caminho não-legado, então
     essas respostas eram lidas, guardadas em `dados`, e simplesmente descartadas na hora
     de salvar. Nova função `_respostas_dinamicas_legado(dados, formularios)` (em
     `pessoas/views.py`) monta o mesmo formato de saída do caminho normal
     (`[(formulario, algo_com_.cleaned_data), ...]`), mas pega os valores direto de
     `dados` sem passar pela validação do formulário dinâmico — mesma filosofia do resto
     do lote legado (aceita o que veio, não trava a linha por uma resposta que não bateu
     com o tipo esperado).
  3. **Data de nascimento errada — todo mundo importado com 126 anos** — causa: célula de
     data do Excel formatada como **texto** (ex.: "4/23/1986") em vez de célula de data de
     verdade vira uma string comum na leitura, e nada no código tentava interpretar esse
     texto como data — só `date.fromisoformat()` (que exige "aaaa-mm-dd") era tentado, e
     "4/23/1986" não bate, então caía sempre no placeholder `DATA_NASCIMENTO_NAO_INFORMADA`
     (1900-01-01 — daí os "126 anos"). Confirmado no arquivo: linhas onde o Excel já tinha
     a célula formatada como data (`datetime` de verdade) importaram certo; linhas com data
     em texto solto, não. Nova função `pessoas/validators.py::normalizar_data_nascimento()`
     tenta uma lista de formatos — dia primeiro (`d/m/aa`, `dd/mm/aa`, `dd/mm/aaaa`, etc.,
     conforme pedido) antes de mês primeiro (US, ex.: "4/23/1986" — formato real encontrado
     no arquivo do usuário), pra desambiguar datas onde dia e mês caberiam nos dois jeitos
     (`"05/04/1990"` vira 5 de abril, não 4 de maio). Usada em dois pontos, não só um: na
     leitura da planilha (`wizard_csv.py::_normalizar_campo`, pra CSV e XLSX) **e** dentro
     de `preparar_linha_legado()` (que tinha sua própria chamada solta a
     `date.fromisoformat()`) — cobre tanto a leitura inicial quanto qualquer texto que
     chegue por outro caminho (ex.: edição manual de uma linha na tela de Revisão).
  - Testado com Playwright, contra um projeto/perfil **descartável** criado só pra esse
    teste (reaproveitando o formulário real "Perguntas Básicas de Bebidas", sem tocar no
    perfil real do projeto Moments nem nos 26 participantes que o usuário já tinha
    importado de verdade): (1) rodei o fluxo completo do wizard (perfil → lote legado →
    planilha → revisão → concluir) com um arquivo `.xlsx` sintético isolado (e-mails que
    não batem com ninguém real), reaproveitando o cabeçalho de verdade do arquivo do
    usuário — uma linha com data em formato US e CPF vazio, outra com data em formato BR e
    CPF inválido; (2) conferido no banco depois: as duas pessoas ficaram com
    `data_nascimento` certa (1988-03-15 e 1995-12-25 — não mais 1900-01-01/126 anos), CPF
    `None` nas duas (nunca gravou o CPF inválido da segunda linha), e **as 7 respostas do
    formulário de Bebidas foram gravadas certinho** pras duas, batendo exatamente com o
    que estava na planilha; (3) também validei `normalizar_data_nascimento()` e a
    validação de CPF de `preparar_linha_legado()` isoladamente via shell, com uma bateria
    maior de formatos de data (ISO, BR com `/`/`-`/`.`, ano de 2 e 4 dígitos, US) e os 3
    casos de CPF (vazio, inválido, válido). Apaguei os 2 participantes de teste, a
    participação, as respostas de formulário e o projeto/perfil descartável depois de
    confirmar — conferido que o perfil real do Moments continua com as 26 participações
    intactas. `makemigrations --check --dry-run` e `manage.py check` limpos (nenhuma
    mudança de model nessa rodada). Zero erro de página em qualquer etapa.
  - **Importante**: os 26 participantes que o usuário já importou de verdade continuam
    com a data de nascimento errada (126 anos) e sem as respostas de Bebidas — essas
    correções valem daqui pra frente, não reprocessam automaticamente o que já foi
    importado. Pra corrigir os que já existem, o caminho mais simples é reimportar o mesmo
    `teste_import.xlsx` no mesmo perfil (o CPF continua protegido, e-mail casa com quem já
    existe e atualiza os dados incompletos sem duplicar — mas preferi não fazer isso
    automaticamente numa rodada de teste, então fica a critério do usuário decidir quando
    rodar).
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/matching.py`,
    `pessoas/validators.py`, `pessoas/wizard_csv.py`, `pessoas/views.py`.
- **2026-08-19 (Mais 2 ajustes no lote legado: faixa de renda em texto livre, e etapa
  inicial "Pago")** — Continuação da rodada anterior, dois pedidos a mais depois de olhar
  de novo o `teste_import.xlsx`.
  1. **Faixa de renda familiar não era considerada** — causa: a coluna "Renda familiar" da
     planilha vem como texto livre em R$ (ex.: `"Acima de R$ 10788.56"`, `"Entre R$
     5721.73 e R$ 10788.56"`), não como letra (`"B"`) nem `"Classe B"` — o único formato
     que `RENDA_MAP` reconhecia. Sem bater com o mapa, o valor virava `""`, tratado como
     "não veio" (`cadastro_incompleto`), perdendo o dado mesmo ele estando presente na
     planilha. Nova função `_mapear_renda_por_valor()` (`pessoas/wizard_csv.py`) — quando
     o mapa de letra/"classe X" não bate, extrai o(s) número(s) do texto (`"Acima de R$
     X"`, `"Entre R$ X e R$ Y"`, etc.) e baleia contra os mesmos limiares de
     `Participante.FaixaRendaIndividual` (A ≥ 9738, B 4869-9737, C 1883-4868, D 974-1882,
     E < 974) — o valor numérico é o que decide a faixa certa, não o rótulo exato que o
     questionário original usava (R$ direto ou salários mínimos). Numa faixa "entre X e
     Y", usa o limite de baixo (X): é ele que separa essa faixa da faixa imediatamente
     acima. Mesmo fallback vale pra "Renda individual", caso venha descrita do mesmo jeito.
  2. **Lote legado agora entra direto na etapa "Pago"** — antes, toda participação nova
     (legado ou não) entrava em "Análise de Perfil", que faz sentido pra gente recém-
     captada mas não pra quem tá sendo importada de um histórico que já rodou por completo
     (o próprio objetivo do lote legado é regularizar cadastro de gente que já participou).
     `pessoas/views.py::wizard_revisao` agora escolhe a etapa inicial condicionalmente:
     `Participacao.Etapa.PAGO` se `legado`, senão continua `ANALISE_PERFIL` como sempre.
     Como é `get_or_create` com `defaults`, isso só vale pra participação **nova** —
     reimportar um CPF/e-mail que já tem participação em andamento não regride a etapa de
     quem já avançou mais no funil por outro caminho.
  - Testado com Playwright de novo contra um projeto/perfil descartável novo (mesmo
    cuidado da rodada anterior — nada tocou no perfil real do Moments nem nos 26
    participantes já importados de verdade): rodei o wizard completo com um `.xlsx`
    sintético isolado reaproveitando o cabeçalho real, uma linha com `"Acima de R$
    10788.56"` e outra com `"Entre R$ 3194.34 e R$ 5721.72"` na renda familiar — conferido
    no banco depois que as duas ficaram com o código certo (`A` e `C`, batendo com os
    limiares esperados) e as duas participações entraram direto em `PAGO`. Também testei
    `_mapear_renda_por_valor()` isoladamente via shell com os 3 valores reais do arquivo do
    usuário mais casos de borda (texto sem número, string vazia, formato letra/classe
    continua funcionando). Apaguei os participantes de teste, a participação e o
    projeto/perfil descartável depois — conferido que o perfil real do Moments continua
    com as 26 participações intactas. `makemigrations --check --dry-run` e `manage.py
    check` limpos. Zero erro de página.
  - **Mesmo aviso da rodada anterior**: essas correções valem daqui pra frente — os 26
    participantes já importados continuam com a faixa de renda familiar perdida e a etapa
    que já tinham antes (não regride nem re-completa automaticamente). Reimportar o mesmo
    arquivo no mesmo perfil resolveria os três problemas de uma vez (data, Bebidas, renda)
    pra quem já existe — mas essa decisão fica com o usuário, não fiz isso automaticamente.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/wizard_csv.py`
    (mudança nova nessa rodada) e `pessoas/views.py` (mudança nova nessa rodada).
- **2026-08-19 (Excluir os 26 participantes do lote com bug + botão novo de excluir
  participação)** — Pedido do usuário depois de confirmar os bugs do lote legado: apagar
  os 26 participantes importados com dado errado, e ter um botão de excluir participação
  (não só participante) — os dois com aviso "Quer mesmo excluir?".
  1. **Exclusão real dos 26 participantes/participações** — conferido antes de apagar
     (`Participacao.objects.filter(perfil_id=34)`, o perfil "Consumidores de Cerveja
     Premium" do projeto Moments): batiam exatamente os 26 códigos `P-2026-0013` a
     `P-2026-0038`, e nenhum deles tinha participação em nenhum outro perfil — existiam no
     sistema só por causa dessa importação. Apaguei cada `Participante` (não só a
     participação) — `Participacao`/`RespostaFormulario`/`AceiteTermo` já são
     `on_delete=CASCADE` a partir de `Participante`, então tudo relacionado a cada um saiu
     junto automaticamente, e registrei cada exclusão na Auditoria LGPD (mesma função
     `registrar()` que a tela de exclusão de participante já usa). Conferido depois: 0
     participantes com aqueles códigos, 0 participações restando no perfil do Moments, os
     9 participantes de demonstração que já existiam antes continuam intactos.
  2. **Botão de excluir participação (novo)** — não existia view nenhuma pra isso, só a
     permissão `participacoes.excluir` (já cadastrada e seedada no catálogo desde uma
     rodada bem anterior, mas nunca ligada a nada). Segue exatamente o mesmo formato já
     usado em "Excluir participante" (`pessoas/views.py::excluir` +
     `templates/pessoas/excluir.html`): tela de confirmação própria (não um `confirm()` de
     JS), texto "Quer mesmo excluir a participação de X no perfil Y?", aviso de que
     avaliação e respostas de formulário daquela participação saem junto (mas o cadastro
     do participante no Banco de Pessoas **não** é afetado — só a ligação dele com aquele
     perfil), e "Esta ação não pode ser desfeita". Nova view
     `participacoes/views.py::excluir` (rota `participacoes/<pk>/excluir/`, gated por
     `participacoes.excluir`), novo template `templates/participacoes/excluir.html`,
     botão "Excluir" adicionado tanto na tela de detalhe da participação quanto na coluna
     de ações da listagem (`templates/participacoes/lista.html`) — mesmo padrão de botão
     vermelho fraco (`border-color:#F7C9C0;color:#B03225`) já usado nos outros "Excluir"
     do sistema. Também registra na Auditoria LGPD.
  3. **Texto de confirmação padronizado nos dois** — `templates/pessoas/excluir.html`
     tinha "Tem certeza que deseja excluir..."; ajustado pra "Quer mesmo excluir...?", a
     mesma frase pedida, igual à do novo `participacoes/excluir.html`.
  - Testado com Playwright contra dados descartáveis (participante/perfil/projeto de
    teste criados só pra isso, com uma `Avaliacao` de verdade anexada): (1) botão
    "Excluir" aparece na tela de detalhe da participação; (2) tela de confirmação mostra o
    texto certo; (3) "Cancelar" volta pro detalhe sem apagar nada; (4) "Sim, excluir"
    apaga a participação e a avaliação junto (conferido no banco), sem tocar no cadastro
    do participante; (5) conferi também a tela de confirmação de excluir participante
    (sem clicar em excluir — só GET, sem risco) pra confirmar o texto "Quer mesmo excluir
    Lucas Couto...?". Apaguei os dados de teste depois de confirmar. `manage.py check` e
    `makemigrations --check --dry-run` limpos (nenhuma mudança de model). Zero erro de
    página.
  - **Segue sem commitar.** `git status` agora também inclui `participacoes/views.py`,
    `participacoes/urls.py`, `templates/participacoes/excluir.html` (novo),
    `templates/participacoes/detalhe.html`, `templates/participacoes/lista.html`,
    `templates/pessoas/excluir.html`. A exclusão dos 26 participantes já foi aplicada
    direto no banco (não é uma mudança de código pra commitar — é dado, já fora da base).
- **2026-08-19 (Mais um campo do lote legado sem mapa: Raça/cor com sufixo "(a)")** — Última
  pergunta do usuário sobre o `teste_import.xlsx`: por que Raça não entrou, e por que só 26
  de 31 linhas viraram participante novo (5 "atualizados").
  1. **Raça/cor** — mesma classe de bug das rodadas anteriores (Renda familiar, Gênero):
     `RACA_MAP` só tinha as formas femininas sem sufixo (`"branca"`, `"preta"`, `"parda"`),
     mas a planilha usa `"Branco(a)"`, `"Pardo(a)"`, `"Preto(a)"` (confirmado nos valores
     reais da coluna) — não bate com nenhuma chave do mapa, então a raça de todo mundo
     importado ficava vazia (`cadastro_incompleto`) mesmo com o dado presente. Adicionadas
     as variações `"branco"`/`"branco(a)"`, `"preto"`/`"preto(a)"`, `"pardo"`/`"pardo(a)"`,
     `"amarelo"`/`"amarelo(a)"` ao `RACA_MAP` (`pessoas/wizard_csv.py`) — o padrão de aceitar
     a forma com "(a)" já existia em `ESTADO_CIVIL_MAP` pra outros campos, só faltava
     estender pra esse.
  2. **26 criados + 5 atualizados, não é bug — é o arquivo tendo gente duplicada** —
     conferido nos dados reais: a planilha tem **31 linhas** (não 32 — a primeira linha é
     cabeçalho), e **5 pessoas aparecem duas vezes cada** (mesmo nome, mesmo e-mail, mesmo
     telefone — duplicata exata, não coincidência de nome): Felipe Rigio Monteiro (linhas 2
     e 29), Aline Santos de Carvalho (linhas 3 e 25), Tatiane Pereira da Silva (linhas 7 e
     17), Jonathan Valerio Lopes da Silva (linhas 8 e 21) e Claudio José Tonett (linhas 10 e
     14). 31 linhas − 5 nomes repetidos = 26 pessoas únicas → 26 "criados"; as 5 segundas
     ocorrências batem via e-mail com quem a própria importação acabou de criar poucas
     linhas antes (mesma lógica de `encontrar_participante_existente` que evita duplicar
     cadastro) → contam como "atualizados". 26 + 5 = 31, bate certinho com o total de
     linhas — não sobrou nem faltou ninguém.
  - Testado `_normalizar_campo("raca", ...)` isoladamente via shell com os 3 valores reais
    da planilha mais variação de maiúscula/minúscula e a forma sem sufixo — todos mapeando
    certo agora. A investigação da duplicidade foi só leitura de planilha (nenhuma consulta
    ou mudança no banco). `manage.py check` e `makemigrations --check --dry-run` limpos.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/wizard_csv.py`
    (mudança nova nessa rodada, além da de rodadas anteriores).
- **2026-08-19 (Renda familiar usava a escala errada de limiar; Origem confundia
  importação com cadastro público)** — Usuário reportou dois problemas olhando o cadastro
  de um participante importado de verdade: "Acima de R$10788.56" virou Classe A — 20
  salários mínimos (que hoje passa de R$30 mil, muito mais que R$10.788,56), e a tela de
  Origem dizia "Cadastro público" pra alguém que na verdade é participante legado —
  importação.
  1. **Renda familiar reusava os limiares de Renda individual** — causa raiz: a rodada
     anterior (`_mapear_renda_por_valor()`) usava a **mesma** tabela de limiares em R$ pros
     dois campos, mas `FaixaRendaIndividual` e `FaixaRendaFamiliar` são escalas diferentes
     pro mesmo código de classe (individual é R$ direto: A ≥ 9.738; familiar é múltiplo de
     salário mínimo: A = 20×). Como R$10.788,56 já passa de R$9.738, caía em "A" na escala
     errada — mas 20 salários mínimos é uma renda familiar muito maior que isso. Corrigido
     em `pessoas/wizard_csv.py`: a tabela antiga virou
     `_FAIXAS_RENDA_INDIVIDUAL_POR_VALOR` (limiares inalterados, só renomeada), e entrou
     `_FAIXAS_RENDA_FAMILIAR_POR_VALOR`, calculada a partir de uma constante nova
     `SALARIO_MINIMO = 1518` (valor real vigente, não lido de lugar nenhum do banco — ajustar
     ali quando o valor oficial mudar): A ≥ R$30.360 (20×), B ≥ R$15.180 (10×), C ≥ R$6.072
     (4×), D ≥ R$3.036 (2×), E abaixo disso. `_mapear_renda_por_valor()` agora recebe a
     tabela de limiares como parâmetro em vez de usar uma fixa, e `_normalizar_campo()`
     escolhe a tabela certa por campo. Com o limiar novo, "Acima de R$10788.56" agora cai em
     "C" (4-10 salários mínimos), não mais em "A".
  2. **Origem confundia "quem indicou" com "veio de cadastro público"** — causa raiz:
     `origem_recrutador` (FK) só registra quem leva o crédito pela indicação, mas era
     preenchido tanto no cadastro público de verdade (`cadastro_publico`) quanto em
     **qualquer** participante novo do wizard de importação (`wizard_revisao`, legado ou
     não) — e a tela de detalhe (`templates/pessoas/detalhe.html`) interpretava
     `origem_recrutador` preenchido como "sempre veio do cadastro público", o que é falso
     pra quem foi importado pela equipe. Corrigido com um campo novo,
     `Participante.origem_cadastro` (`CharField` com choices `PUBLICO`,
     `IMPORTACAO_LEGADO`, `IMPORTACAO`, `MANUAL_EQUIPE`, `null=True` — fica em branco em
     quem foi criado antes desta distinção existir, já que não dá pra reconstruir a origem
     de cadastros antigos com certeza) — migração
     `pessoas/migrations/0011_participante_origem_cadastro.py`. Gravado em três pontos:
     `cadastro_publico` marca `PUBLICO` toda vez que a pessoa responde o formulário público
     de verdade (cadastro novo **ou** reenvio de quem já existia — é literalmente "ela
     respondeu o formulário", exatamente o critério que o usuário pediu: "só atualize essa
     informação se ele responder o formulário"); `wizard_revisao` marca
     `IMPORTACAO_LEGADO`/`IMPORTACAO`/`MANUAL_EQUIPE` (conforme o modo do lote) só em
     participante **novo**, nunca sobrescrevendo quem já tinha uma origem registrada por
     outro caminho — mesma regra que já valia pra `origem_recrutador` não roubar crédito de
     indicação em atualização. `templates/pessoas/detalhe.html`: a linha "Origem" agora
     mostra `get_origem_cadastro_display()` (com "por Fulano" quando há recrutador) quando o
     campo novo está preenchido, e só cai no texto genérico antigo ("Cadastro público,
     indicado por X") pra quem não tem `origem_cadastro` (cadastro antigo, de antes desta
     mudança) — só 2 participantes no banco caem nesse caso hoje.
  3. **Correção retroativa dos 26 participantes reais do lote legado** — mesmo lote descrito
     nas rodadas anteriores (`P-2026-0013` a `P-2026-0038`, reimportado depois das correções
     de CPF/data/Bebidas/Raça já aplicadas), únicos participantes reais afetados pelos dois
     bugs. Reli `teste_import.xlsx`, recalculei a Renda familiar de cada um dos 26 com a
     tabela nova (batendo o e-mail de cada linha com o participante correspondente) e
     apliquei só quem realmente mudava de código — todos os 26 mudaram (13 de "A" pra "C",
     13 de "B"/"C" pra "D"), confirmado no banco depois. Também apliquei
     `origem_cadastro = IMPORTACAO_LEGADO` nos mesmos 26 (confirmado antes que os 26 tinham
     `origem_cadastro` vazio e etapa "Pago" em todas as participações — a mesma marca que o
     lote legado já usa — antes de mexer). Nenhum outro participante do banco foi tocado.
  - Testado: `_mapear_renda_por_valor()` com os 3 valores reais do arquivo contra a tabela
    familiar nova, batendo com o balde esperado (C/D/D pros três exemplos do arquivo, contra
    A/B/C que dava antes). Renderizei a linha "Origem" do template isoladamente (via
    `Engine.from_string`, sem precisar subir o servidor) pra dois dos 26 participantes reais
    corrigidos — confirma "Participante legado — importação, por Administradora Demo".
    Conferi que só 2 participantes no banco inteiro ainda caem no fallback antigo (cadastro
    de antes desta mudança, com `origem_recrutador` mas sem `origem_cadastro`). `manage.py
    check` e a migração (`makemigrations` + `migrate`) limpos. Não testei o fluxo completo
    de cadastro público/wizard de ponta a ponta via navegador nesta rodada — a lógica nova
    é a mesma estrutura condicional já testada em rodadas anteriores, só troquei qual valor
    é atribuído; validação foi direto nos pontos de escrita e no template.
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/models.py`,
    `pessoas/migrations/0011_participante_origem_cadastro.py`, `pessoas/views.py`,
    `pessoas/wizard_csv.py`, `templates/pessoas/detalhe.html`. A correção dos 26
    participantes reais (Renda familiar + Origem) já foi aplicada direto no banco (dado, não
    código — nada a commitar por ela).
- **2026-08-19 (Conferência dos "5 atualizados" do lote legado + log de auditoria pra
  atualização via wizard)** — Usuário olhou o projeto Moments em produção
  (`sistema-banco-pessoas-production.up.railway.app`, mesmo banco RDS que o shell local usa
  — confirmado, não é ambiente separado) e reportou que, dos 5 participantes "atualizados"
  na importação (em vez de criados), a participação no perfil não tinha sido criada nem as
  respostas do formulário de Bebidas.
  1. **Conferência direta no banco de produção** — antes de mexer em qualquer código, bati
     as 31 linhas do `teste_import.xlsx` (26 pessoas únicas) contra o estado atual: todas as
     31 linhas resolvem pra um `Participante` existente, e todos os 26 únicos têm
     `Participacao` no perfil "Consumidores de Cerveja Premium" (etapa "Pago") **e**
     `RespostaFormulario` do formulário de Bebidas — inclusive checado nome a nome os 5 que
     geraram "atualizado" (Felipe Rigio Monteiro, Aline Santos de Carvalho, Tatiane Pereira
     da Silva, Jonathan Valerio Lopes da Silva, Claudio José Tonett): todos com participação
     e resposta de formulário presentes. Ou seja, pro lote que já rodou, o dado real já está
     correto — o problema relatado não reproduz no banco de hoje (`pessoas/views.py::wizard_revisao`,
     no bloco `if perfil is not None:`, já roda `Participacao.objects.get_or_create(...)` e
     salva `RespostaFormulario` incondicionalmente pra toda linha, criada ou atualizada — não
     achei nenhum caminho que pule isso só pra quem é "atualizado").
  2. **Log de auditoria pra atualização via wizard (pedido novo, esse sim não existia)** —
     antes desta rodada, `wizard_revisao` nunca chamava `registrar()` quando uma linha
     atualizava um participante já existente (só exclusão/aprovação/descarte tinham log até
     aqui). Adicionado: toda vez que a linha bate com um participante existente (`atualizados
     += 1`), grava um `RegistroAcesso` (`Acao.ALTERACAO`, detalhe "Cadastro atualizado via
     importação em lote (participante já existia — CPF/e-mail/telefone bateu)") na Auditoria
     LGPD — mesmo padrão já usado pra exclusão/aprovação/descarte. Vale só daqui pra frente:
     as 5 atualizações do lote já processado aconteceriam sem log (a feature não existia
     ainda no momento em que rodaram) — não criei entrada retroativa porque o campo `quando`
     do `RegistroAcesso` é `auto_now_add` (sempre "agora"), e uma entrada "falsa" datada de
     hoje pra um evento que já aconteceu antes distorceria a trilha de auditoria em vez de
     documentá-la.
  - Testado: consulta direta no banco (mesma RDS de produção) cruzando as 31 linhas da
    planilha original contra `Participante`/`Participacao`/`RespostaFormulario` — nenhuma
    linha ficou sem `Participacao` ou sem resposta salva. `manage.py check` limpo (sem
    mudança de model nesta rodada, só a chamada nova de `registrar()`).
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/views.py` (mudança
    nova nessa rodada, além das anteriores). Nenhum dado foi alterado no banco nesta
    rodada — só leitura/conferência.
- **2026-08-19 ("Segmento" do cadastro/edição de Projeto vira Categoria cadastrada)** —
  Usuário mostrou a tela de editar o projeto Moments: o campo "Segmento" ainda era a lista
  fixa de 5 opções (`Saúde/Cosméticos/Alimentação/Banco/Tecnologia/Outro`) do código, mesmo
  depois de os dois dashboards já terem trocado esse conceito pra `CategoriaFormulario`
  (rodada anterior "Segmento → Categoria do Perfil") — pediu pra esse campo também usar as
  categorias cadastradas de verdade.
  1. **`Projeto.segmento` (CharField + choices fixas) virou `Projeto.categoria` (FK pra
     `CategoriaFormulario`)** — `projetos/models.py`: removida a classe `Segmento`
     (TextChoices), campo novo `categoria = ForeignKey("formularios.CategoriaFormulario",
     null=True, blank=True, on_delete=SET_NULL, related_name="projetos")`. Sem import
     circular (`projetos` já importa de `formularios` em `forms.py`; o inverso não existe).
     Renomeado (não só o tipo) porque manter o nome "segmento" apontando pra um valor que
     agora É uma `CategoriaFormulario` ficaria inconsistente com o resto do sistema, que já
     chama esse conceito de "categoria" desde a rodada anterior.
  2. **Migração com preservação de dado** (`projetos/migrations/0011_remove_projeto_segmento_projeto_categoria.py`) —
     como o tipo de coluna muda de verdade (varchar → FK), não dá pra fazer só um
     `AlterField`; escrevi manualmente `AddField categoria` → `RunPython` (associa cada
     projeto com `segmento` preenchido à `CategoriaFormulario` de mesmo nome, via um mapa
     `SAUDE→"Saúde"`, `ALIMENTACAO→"Alimentação"`, `BANCO→"Banco"`, `TECNOLOGIA→"Tecnologia"`
     — "COSMETICOS" e "OUTRO" não têm categoria cadastrada equivalente, ficam sem categoria
     em vez de eu adivinhar uma associação) → `RemoveField segmento`, nessa ordem (o dado
     velho só some depois de já ter sido lido e copiado). Conferido nos 4 projetos reais do
     banco: "Moments" (era `ALIMENTACAO`) → categoria "Alimentação"; "Teste Bancos Digitais"
     (era `BANCO`) → categoria "Banco"; "Captação de Pessoas Instagram" (era `OUTRO`) → sem
     categoria (não tinha match); "Campanha Tenis Playwright" (já estava em branco) → sem
     categoria. Nenhum projeto perdeu dado que tinha correspondência real.
  3. **Formulário e telas** — `ProjetoForm` (`projetos/forms.py`): `"segmento"` →
     `"categoria"` em `fields`/`labels`; `empty_label = "Sem categoria"` no `__init__`
     (mesmo texto que `Formulario.categoria` já usa em `formularios/forms.py` — o helper
     `personalizar_opcoes_vazias` pula `ModelChoiceField` de propósito, então precisa setar
     na mão). `templates/projetos/form.html`, `lista.html`, `detalhe.html`: trocado
     `form.segmento`/`get_segmento_display` por `form.categoria`/`categoria.nome`.
  - Testado: renderizei o `<select>` do campo `categoria` isoladamente (via
    `ProjetoForm(instance=...)`, sem precisar subir o servidor) pro projeto Moments —
    aparecem as 9 categorias cadastradas em ordem alfabética, "Alimentação" já vem marcada
    (`selected`) batendo com o valor migrado. `manage.py check` e `makemigrations --check
    --dry-run` limpos. Não testei a submissão do formulário via navegador nesta rodada — é
    um `ModelChoiceField` padrão do Django, mesmo mecanismo já usado em `Formulario.categoria`
    noutra tela.
  - **Segue sem commitar.** `git status` agora também inclui `projetos/models.py`,
    `projetos/forms.py`, `projetos/migrations/0011_remove_projeto_segmento_projeto_categoria.py`
    (novo), `templates/projetos/form.html`, `templates/projetos/lista.html`,
    `templates/projetos/detalhe.html`. A migração de dado dos 4 projetos reais (segmento →
    categoria) já foi aplicada junto com a migração de schema — é a mesma operação, não dá
    pra separar "código" de "dado" aqui como nas correções anteriores.
- **2026-08-19 (Profissão do lote: de→para automático pela mais parecida, cadastra nova se
  não achar nenhuma)** — Pedido do usuário: hoje `profissao` só casava texto **exatamente**
  igual (case-insensitive) a uma das 67 profissões cadastradas — qualquer variação
  ("Advogada" em vez de "Advogado(a)", "Medico" sem acento, uma profissão que não existe
  ainda no cadastro) virava `""` e a linha ficava incompleta, mesmo o dado estando presente.
  1. **Casamento pela mais parecida (`difflib`)** — `_profissao_por_nome_ou_criar()` (nova,
     `pessoas/wizard_csv.py`): tenta o nome exato primeiro (comportamento de antes); não
     achando, usa `difflib.get_close_matches()` contra os nomes das profissões já
     cadastradas e pega a mais parecida acima de 0.6 de similaridade (escala 0-1) — cobre
     variação de gênero gramatical ("Advogada"→"Advogado(a)", 0.84), acento faltando
     ("Medico"→"Médico(a)", 0.67), forma abreviada/composta ("Enfermeira"→"Enfermeiro(a)"
     0.87, "vendedora"→"Vendedor(a)" 0.9, "Desenvolvedor Full Stack"→"Desenvolvedor(a) de
     Software" 0.69). Corte de 0.6 escolhido testando essas variações reais — abaixo disso
     começa a casar coisas sem relação nenhuma só por compartilhar letras.
  2. **Profissão nova quando não acha nada parecido** — pedido explícito do usuário ("caso
     não ache um parecido, inserir a profissão na listagem"): abaixo do corte de 0.6,
     `Profissao.objects.get_or_create(nome__iexact=texto, defaults={"nome": texto})` cadastra
     o texto da planilha como profissão nova em vez de descartar o dado (testado com
     "Programador", "Dev", "Motorista de aplicativo" — nenhuma tinha profissão parecida o
     bastante cadastrada, as três viraram cadastro novo). O mapa nome→PK em memória
     (`mapa_profissoes`, já existia pra evitar 1 query por célula) é atualizado na hora que
     cria uma nova — outra linha do mesmo lote com o mesmo texto (ou variação que bate
     exato) reaproveita a profissão recém-criada em vez de tentar duplicar (`nome` é
     `unique` no model, `get_or_create` evita o `IntegrityError`).
  3. **Limitação conhecida, documentada e não escondida**: o casamento é por parecença de
     texto, não por significado — testei "Analista de TI" e o mais parecido que o `difflib`
     achou foi "Analista de Redes" (não "Analista de Sistemas / TI", que seria o certo
     semanticamente, mas ficou com nota de parecença um pouco menor). Acontece quando duas
     profissões cadastradas têm nomes parecidos entre si e o texto da planilha é ambíguo
     entre elas — não tem como resolver 100% sem revisão humana; a tela de revisão do
     wizard já deixa qualquer linha editável antes de confirmar, então dá pra corrigir ali
     se acontecer.
  - Testado dentro de uma transação com rollback forçado (`transaction.atomic()` +
    `transaction.set_rollback(True)`) — sem tocar as 67 profissões reais cadastradas: rodei
    13 variações de texto (nomes com gênero diferente, sem acento, abreviados, e 3 que não
    existem no cadastro) contra `_profissao_por_nome_ou_criar()`, conferi cada resultado
    (10 casaram com a profissão certa, 1 casou com a "vizinha" errada por ambiguidade
    semântica — o caso já documentado acima —, 3 viraram profissão nova) e, depois do
    rollback, confirmei que o banco real continua com exatamente 67 profissões (nenhuma das
    3 novas de teste ficou gravada). `manage.py check` limpo (sem mudança de model — só
    lógica nova em `wizard_csv.py`, `Profissao` já existia).
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/wizard_csv.py`
    (mudança nova nessa rodada, além das anteriores).
- **2026-08-20 (Nova coluna no lote: "Data e hora da aplicação" — aceita mês/ano solto e
  vários formatos)** — Pedido do usuário: planilha de importação passa a ter uma coluna pra
  registrar quando a pesquisa foi de fato aplicada com a pessoa (não quando o registro foi
  importado pro sistema) — na maioria das vezes só vem mês/ano (ex.: "jul-2026"), mas pode
  vir em formatos diferentes; em branco, mantém o comportamento de hoje (data/hora da
  importação); mês/ano sozinho completa dia e hora com valor coringa.
  1. **Campo novo em `Participacao`, separado de `criado_em`** — `participacoes/models.py`:
     `data_aplicacao = DateTimeField(default=timezone.now, blank=True)`. Deliberadamente
     **não** é o mesmo campo que `criado_em` (`auto_now_add`, sempre o instante real de
     inserção no banco — continua existindo, intacto, pra quem quiser saber quando o
     registro entrou no sistema de verdade): `criado_em` é "quando entrou no sistema",
     `data_aplicacao` é "quando a pesquisa aconteceu de fato" — pra lote legado, os dois
     podem ser bem diferentes (a pessoa participou há meses, o registro só está sendo
     regularizado agora). Migração
     `participacoes/migrations/0007_participacao_data_aplicacao.py`: `AddField` +
     `RunPython` que preenche `data_aplicacao` das participações já existentes com o próprio
     `criado_em` delas (melhor estimativa disponível pra quem já existia antes deste campo —
     confirmado no banco real: todas as participações existentes ficaram com
     `data_aplicacao == criado_em`, nenhuma virou "agora" pra todo mundo igual).
  2. **Parser novo pra texto livre de data/hora** (`normalizar_data_aplicacao()`, nova em
     `pessoas/validators.py`, ao lado de `normalizar_data_nascimento` que já existia) — tenta
     nessa ordem: data+hora completa → só data → só mês/ano numérico ("07/2026",
     "2026-07") → mês por nome/abreviação em português + ano ("jul-2026", "julho/2026",
     "jul de 2026", "Mar-26" — regex `_REGEX_MES_NOME_ANO` + mapa `_MESES_PT` com todos os
     meses abreviados e por extenso, aceitando com e sem acento). Só mês/ano (o formato mais
     comum avisado pelo usuário) completa **dia 1 e meia-noite** como valor coringa — não dá
     pra saber o dia/hora exatos só com mês/ano, então usa o primeiro instante do mês.
     Não bate com nada conhecido (incluindo texto vazio): devolve `""`, que quem chama trata
     como "não veio" — sem gerar erro nem travar a linha da planilha.
  3. **Coluna nova no wizard** — `pessoas/wizard_csv.py`: `CAMPOS_CSV` ganhou várias
     variações de cabeçalho ("data e hora da aplicação", "data da aplicação", "aplicação",
     etc., com e sem acento) mapeando pra `data_aplicacao`; `_normalizar_campo()` chama
     `normalizar_data_aplicacao()` pra esse campo; `CABECALHO_MODELO`/`LINHA_EXEMPLO` (a
     planilha de exemplo baixável) ganharam a coluna "Data e hora da aplicação" com o
     exemplo `"jul-2026"` (o formato mais comum, exatamente como o usuário descreveu);
     `pessoas/views.py::wizard_modelo_csv` adicionou essa coluna na lista que força
     formato de texto na célula (senão o Excel tentaria converter "jul-2026" pra uma data
     serial ao abrir o arquivo).
  4. **Consumo na hora de criar a participação** — `pessoas/views.py::wizard_revisao`: o
     bloco que já fazia `Participacao.objects.get_or_create(...)` (criação de participação a
     partir da linha da planilha) monta um `defaults_participacao` com `etapa`/`responsavel`
     de sempre, e só acrescenta `data_aplicacao` (convertido pra `datetime` ciente de fuso via
     `timezone.make_aware`) quando a coluna trouxe algo que bateu com o parser. Coluna vazia
     ou texto que não bateu com nenhum formato: a chave nem entra em `defaults`, então o
     próprio `default=timezone.now` do campo assume — exatamente "continua como está hoje",
     pedido explicitamente pelo usuário. Não mexe em nenhum outro caminho de criação de
     participação (`cadastro_publico`, `participacoes:nova` manual) — esses continuam com o
     mesmo `timezone.now()` de sempre, sem coluna de planilha nenhuma envolvida.
  - Testado: 15+ variações de texto (mês abreviado/por extenso com e sem acento, com "de",
    mês/ano numérico em várias ordens, data completa, data+hora, texto vazio, texto inválido,
    mês sem ano, mês inválido) contra `normalizar_data_aplicacao()` isoladamente — todas
    resolveram certo. Depois, ponta a ponta: montei um `.xlsx` sintético com a coluna nova (3
    linhas — mês/ano, data+hora completa, e vazia) e rodei `ler_xlsx()` de verdade, conferindo
    os 3 resultados. Por fim, um teste completo dentro de uma transação com rollback forçado
    (`transaction.atomic()` + `transaction.set_rollback(True)`) — criei projeto/perfil/
    participante descartáveis, rodei a planilha sintética pelo parser e criei a `Participacao`
    exatamente como `wizard_revisao` faz, conferindo que `data_aplicacao` ficou "01/07/2026
    00:00 (America/Sao_Paulo)" (a partir de "jul-2026") enquanto `criado_em` ficou no
    instante real do teste — os dois campos claramente diferentes, como esperado — e que nada
    disso persistiu depois do rollback. `manage.py check` e `makemigrations --check --dry-run`
    limpos.
  - **Segue sem commitar.** `git status` agora também inclui `participacoes/models.py`,
    `participacoes/migrations/0007_participacao_data_aplicacao.py` (novo), `pessoas/views.py`,
    `pessoas/wizard_csv.py`, `pessoas/validators.py`. A migração já rodou (schema + backfill
    de dado nas participações reais existentes — `data_aplicacao = criado_em`).
- **2026-08-20 (Botão "Voltar" nas telas de detalhe/visualização)** — Pedido do usuário:
  "Ver projeto", "Detalhes" da pessoa e outras telas de visualização ganham um botão
  "Voltar" ao lado de "Editar", que volta pra página anterior de verdade — inclusive com
  filtro aplicado, se a página anterior tinha um.
  1. **`history.back()` em vez de link fixo** — `<button type="button" class="btn
     btn-ghost" onclick="history.back()">‹ Voltar</button>`, adicionado antes do botão
     "Editar" (fora de qualquer `{% if pode_editar %}` — navegação não é uma ação
     permissionada) em `templates/pessoas/detalhe.html`, `templates/projetos/detalhe.html`,
     `templates/projetos/perfil_detalhe.html`, `templates/participacoes/detalhe.html`,
     `templates/termos/detalhe.html` (esse último não tinha um wrapper `<div style="flex">`
     pro grupo de botões — adicionei um). Usar o histórico do navegador em vez de montar um
     `href` fixo (ex.: sempre `pessoas:lista`) é o que resolve "voltar com filtro" de graça —
     é literalmente a página anterior inteira, query string incluída, sem precisar guardar
     nem repassar filtro nenhum entre view e template.
  2. **`templates/formularios/formulario_visualizar.html` já tinha um "‹ Voltar"** — mas era
     um link fixo pra `formularios:formularios_lista` (sem filtro, sempre a lista "limpa") e
     vinha depois de "Editar", não antes. Trocado pro mesmo padrão `history.back()` e
     reposicionado antes de "Editar", pra ficar consistente com as telas novas.
  - Testado com Playwright, autenticado: fui pra lista de pessoas com filtro de busca
    aplicado (`/participantes/?q=a`), cliquei em "Detalhes" de um participante, conferi o
    botão "Voltar" (screenshot: aparece à esquerda de "Editar"/"Excluir", igual pedido),
    cliquei nele e confirmei que a URL voltou a ser exatamente `/participantes/?q=a` (mesmo
    filtro, não a lista sem filtro) — comparação exata de URL, não só visual. Também
    screenshot da tela de detalhe de projeto confirmando o mesmo posicionamento. Todos os
    templates tocados carregam sem erro de sintaxe (`get_template()` de cada um).
  - **Segue sem commitar.** `git status` agora também inclui `templates/pessoas/detalhe.html`,
    `templates/projetos/detalhe.html`, `templates/projetos/perfil_detalhe.html`,
    `templates/participacoes/detalhe.html`, `templates/termos/detalhe.html`,
    `templates/formularios/formulario_visualizar.html`.
- **2026-08-21 (Auditoria dos filtros de lista: telefone sem normalização, busca não
  cobria telefone/e-mail, índices novos nas colunas pesquisadas)** — Pedido do usuário:
  conferir por que só o filtro por nome funcionava nas listas, garantir que telefone seja
  sempre salvo só com dígitos (busca por `LIKE`), colocar índice nas colunas pesquisadas, e
  testar todos os filtros de todas as páginas.
  1. **Levantamento de todas as páginas com filtro** — só 3 telas têm filtro de verdade:
     `pessoas/lista.html` (q, situação, classe social, UF, cadastro incompleto),
     `participacoes/lista.html` (nome, projeto, etapa, status, nota) e `auditoria/lista.html`
     (usuário, titular, ação, período). `projetos/lista.html` e as 3 listas de
     `formularios` (formulários, categorias, variáveis) e `usuarios_lista.html` não têm
     filtro nenhum hoje — nada quebrado ali, só não existe.
  2. **Bug real encontrado: busca de Pessoas (`q`) nunca cobriu telefone nem e-mail** —
     `pessoas/views.py::_participantes_filtrados` só buscava em `nome`/`cpf`/`codigo`
     (`Q(...) | Q(...) | Q(...)`), apesar do placeholder do campo já prometer "nome, CPF ou
     código" — nunca incluiu telefone/e-mail, então digitar um telefone ou e-mail na busca
     sempre voltava vazio (ou, pior, um telefone que por acaso batesse como substring de um
     CPF/código de outra pessoa). Corrigido: `Q(email__icontains=q)` entrou na busca; pra
     telefone, só entra `Q(telefone__icontains=q_digitos)` quando o texto digitado tiver
     pelo menos um dígito (`q_digitos = normalizar_telefone(q)`) — sem essa guarda, buscar só
     por nome (sem dígito nenhum) bateria com `telefone__icontains=""`, que casa com
     **qualquer** telefone e devolveria a base inteira (testado e confirmado esse risco antes
     de proteger). Placeholder do campo (`templates/pessoas/lista.html`) atualizado pra
     "nome, CPF, código, telefone ou e-mail".
  3. **Telefone não era normalizado na gravação — só na comparação de duplicidade** —
     `pessoas/matching.py` já tinha `normalizar_telefone()` (só dígitos), mas só usava pra
     achar duplicata na hora do upsert (`encontrar_participante_existente`) — o valor
     **gravado** no banco continuava com a pontuação que a pessoa/planilha trouxe
     (confirmado nos dados reais: 34 dos 38 telefones cadastrados tinham espaço/parênteses/
     hífen, só 4 já eram só dígitos). Corrigido: `normalizar_telefone()` mudou de
     `matching.py` pra `pessoas/validators.py` (módulo compartilhado, ao lado de
     `normalizar_cpf`/`normalizar_data_*`), `matching.py` agora importa de lá em vez de ter
     a própria cópia; `ParticipanteForm.clean_telefone()` (novo, `pessoas/forms.py`) aplica
     a normalização em todo cadastro que passa por formulário (cadastro manual, cadastro
     público, wizard manual); `pessoas/wizard_csv.py::_normalizar_campo` ganhou o campo
     `"telefone"` (aplica na leitura da planilha, cobre o lote legado que nunca passa por
     `ParticipanteForm`). Migração
     `pessoas/migrations/0012_alter_participante_cadastro_incompleto_and_more.py` inclui um
     `RunPython` que normaliza todo telefone já cadastrado — conferido no banco real depois:
     os 38 telefones existentes ficaram 100% só-dígitos (nenhum caractere de pontuação
     sobrando).
  4. **Índices novos nas colunas realmente pesquisadas** — `db_index=True` em:
     `Participante.nome`, `.telefone`, `.email`, `.uf`, `.renda_individual`, `.situacao`,
     `.cadastro_incompleto` (cpf/código já são `unique=True`, que no Postgres já cria índice
     sozinho — não precisavam); `Participacao.etapa`, `.status`; `RegistroAcesso.titular`,
     `.acao`, `.quando` (`usuario` já é FK, que Django indexa automaticamente). Mesma
     migração de pessoas (índice + normalização de telefone juntos) e duas migrações novas
     em `participacoes`/`auditoria` só com os índices.
  - **O que já funcionava e não precisou de conserto** (importante deixar claro — nem tudo
    que o usuário desconfiava estar quebrado estava): os dropdowns de situação/classe
    social/UF/cadastro incompleto em Pessoas, e todos os filtros de Participações (nome,
    projeto, etapa, status, nota/sem_avaliação) e Auditoria (usuário, titular, ação,
    período) já filtravam certo — conferido um por um contra dado real (ver testes abaixo).
    O filtro "nome" de Participações continua só por nome (não por telefone/e-mail) porque é
    isso que o campo já diz que faz (`placeholder="Buscar por nome…"`) — não é um filtro
    "genérico" quebrado como o `q` de Pessoas era; se o usuário quiser esse também cobrindo
    telefone/e-mail do participante, é só pedir.
  - Testado direto contra dado real (só leitura nos testes de filtro que já existiam — a
    única escrita real foi a migração de normalização, que já é o próprio conserto): (1)
    busca por telefone com pontuação diferente da salva (`(85) 99994-9633` batendo com
    `85999949633`) achou exatamente o participante certo, tanto chamando
    `_participantes_filtrados()` direto quanto pelo navegador via Playwright (autenticado,
    `/participantes/?q=...`, 1 resultado); busca por pedaço de e-mail achou certo; busca só
    por nome (sem dígito) continuou achando só quem bate o nome, **não** a base inteira
    (conferido explicitamente — é a guarda que existe pra evitar a armadilha do
    `telefone__icontains=""`); dropdowns de situação (`PENDENTE` → 37) e UF (`SP` → 9)
    testados no navegador de verdade, contadores batendo. (2) Participações: filtro por
    nome, por projeto, por etapa (`PAGO` → 38 de 39, `ANALISE_PERFIL` não achou o mesmo
    registro), por status, e "sem avaliação" — todos conferidos contra dado real, todos
    corretos (não tinha nenhuma `Avaliacao` no banco pra testar o limiar de nota mínima
    numérico, mas o código é uma comparação direta, risco baixo). (3) Auditoria: usuário,
    pedaço do titular, ação exata, e intervalo de data (uma data futura corretamente não
    achou nada) — todos corretos. `manage.py check` e `makemigrations --check --dry-run`
    limpos.
  - **Segue sem commitar.** `git status` agora também inclui `auditoria/models.py`,
    `participacoes/models.py`, `pessoas/forms.py`, `pessoas/matching.py`,
    `pessoas/models.py`, `pessoas/validators.py`, `pessoas/views.py`, `pessoas/wizard_csv.py`,
    `templates/pessoas/lista.html`,
    `auditoria/migrations/0003_alter_registroacesso_acao_and_more.py` (novo),
    `participacoes/migrations/0008_alter_participacao_etapa_alter_participacao_status.py`
    (novo), `pessoas/migrations/0012_alter_participante_cadastro_incompleto_and_more.py`
    (novo, inclui a normalização retroativa dos 38 telefones reais).
- **2026-08-21 (Opções de resposta de Variável: botão "Adicionar opção" em vez de 3 campos
  fixos; ordem alfabética com "Outro"/"Outra" sempre por último)** — Usuário mostrou a tela
  de editar uma variável de múltipla escolha com várias opções e pediu duas mudanças: (1)
  em vez do formset sempre terminar com 3 campos em branco pra opção nova, um botão
  "Adicionar opção" que abre um campo novo; (2) opções de tipo lista fechada sempre em
  ordem alfabética, com "Outro"/"Outra" sempre por último.
  1. **Formset deixou de nascer com 3 campos em branco** — `VariavelOpcaoFormSet`
     (`formularios/forms.py`) tinha `extra=3`; virou `extra=0`. Criar uma variável nova (ou
     editar uma sem adicionar opção) começa com a lista vazia, só o botão.
  2. **Botão "+ Adicionar opção" (novo)** — `templates/formularios/variavel_form.html`:
     lista de opções ganhou um container (`id="opcoes-lista"`) pra JS conseguir apontar onde
     inserir a linha nova, e um `<template id="opcao-form-template">` escondido com
     `formset.empty_form` (o form vazio do Django, com `__prefix__` no lugar do índice — é o
     mecanismo padrão do framework pra formset dinâmico, não tem equivalente pronto em JS).
     `static/js/variavel_opcoes.js` (novo): ao clicar, clona o template, troca `__prefix__`
     pelo índice atual (lido de `#id_opcoes-TOTAL_FORMS` — o prefixo do formset é `opcoes`,
     que vem do `related_name` do FK em `VariavelOpcao.variavel`, não o `"form"` padrão que
     eu tinha assumido de início e corrigi depois de testar), anexa a linha e incrementa
     `TOTAL_FORMS`. "Remover" continua sendo o mesmo checkbox `DELETE` de sempre, tanto pra
     linha já salva quanto pra linha recém-adicionada.
  3. **Ordem alfabética com "Outro"/"Outra" sempre por último** — `ordem`
     (`VariavelOpcao.ordem`) nunca foi editável por ninguém (não existe UI pra isso); só
     refletia a ordem de preenchimento/importação original — por isso a tela mostrava
     "Antarctica, Coca-Cola, Antarctica Pilsen, Pepsi, Brahma..." fora de ordem. Nova função
     `_reordenar_opcoes_alfabetico()` (`formularios/views.py`), chamada no fim de
     `_salvar_variavel_com_opcoes()` (toda criação/edição de variável): reordena
     `variavel.opcoes.all()` por `valor.strip().lower()`, com uma chave `(eh_outro,
     valor_normalizado)` que empurra qualquer opção cujo valor normalizado seja "outro" ou
     "outra" pro final, não importa a posição alfabética real — e regrava `ordem` só de quem
     mudou de posição. Como `variavel.opcoes.all()` já é usado tanto na tela de edição
     quanto em `formularios/respostas.py::_campo_para_variavel` (as opções que o
     participante vê de verdade num select/radio/checkbox), essa é a única mudança
     necessária pra alfabetizar nos dois lugares — nenhuma mudança em `respostas.py`.
  4. **Migração de dado pra quem já tinha opção cadastrada** —
     `formularios/migrations/0008_reordena_opcoes_alfabetico.py`: mesma lógica de
     reordenação, rodada uma vez em todas as `Variavel` existentes (a variável do
     screenshot do usuário incluída). Sem isso, o conserto só valeria pra quem editasse e
     salvasse a variável de novo.
  - Testado: (1) a variável real do screenshot ("Quais marcas de bebidas você costuma
    consumir atualmente?") — depois da migração, conferido no banco e na tela de edição via
    Playwright que a ordem ficou "3 Corações, Ambev, Antarctica, Antarctica, Antarctica
    Pilsen, Antarctica Pilsen, Brahma, Brahma, Coca-Cola, Corona, Heineken, Nespresso,
    Pepsi, Red Bull, Stella Artois, Outro" — alfabética, Outro por último (as duplicatas
    "Antarctica"/"Antarctica Pilsen"/"Brahma" já existiam nos dados antes desta mudança —
    não fazia parte do pedido remover duplicata, só ordenar). (2) Botão "Adicionar opção"
    testado ao vivo via Playwright, tanto na tela de criar variável nova (0 linhas → 2
    linhas depois de 2 cliques, `TOTAL_FORMS` batendo) quanto editando a variável real (16
    → 18 linhas); tela de "Nova variável" com tipo "Seleção múltipla" selecionado mostra só
    o botão, sem nenhum campo em branco (screenshot conferido). (3) Ciclo completo de
    salvar+reordenar testado numa variável descartável dentro de uma transação com rollback
    forçado (`transaction.atomic()` + `transaction.set_rollback(True)`, nunca tocou dado
    real): submeti opções fora de ordem e com variação de maiúscula (`"Zebra", "outro",
    "Abacaxi", "Manga", "ABACATE"`) através de `_salvar_variavel_com_opcoes()` de verdade —
    saiu `ABACATE, Abacaxi, Manga, Zebra, outro` (alfabética case-insensitive, "outro"
    minúsculo reconhecido e empurrado pro fim mesmo tendo sido submetido em segundo lugar);
    confirmado que nada da variável de teste sobrou no banco depois do rollback. `manage.py
    check` e `makemigrations --check --dry-run` limpos.
  - **Segue sem commitar.** `git status` agora também inclui `formularios/forms.py`,
    `formularios/views.py`, `templates/formularios/variavel_form.html`,
    `static/js/variavel_opcoes.js` (novo),
    `formularios/migrations/0008_reordena_opcoes_alfabetico.py` (novo, já rodou —
    reordenou toda `VariavelOpcao` já cadastrada no banco real).
- **2026-08-21 (Estado civil no lote: forma feminina sem sufixo não era reconhecida)** —
  Mesma classe de bug já corrigida pra Raça/cor nesta sessão, dessa vez em Estado civil:
  usuário reportou que "Solteira" não preenchia o campo na importação, só "Solteiro"
  reconhecia. `ESTADO_CIVIL_MAP` (`pessoas/wizard_csv.py`) tinha a forma masculina e a
  forma com sufixo "(a)" pra cada estado civil, mas não a forma feminina pura sem sufixo —
  adicionadas "solteira", "casada", "separada", "divorciada", "viuva"/"viúva" (união
  estável já não tem variação de gênero). Testado isoladamente via shell com todas as
  formas (feminino, masculino, com "(a)") — todas mapeando pro código certo agora.
  Conferido no banco real: 0 participantes atualmente com `estado_civil` vazio, então não
  havia ninguém real pra corrigir retroativamente desta vez — o conserto vale só pra
  próxima importação. `manage.py check` limpo (sem mudança de model).
  - **Segue sem commitar.** `git status` agora também inclui `pessoas/wizard_csv.py`
    (mudança nova nessa rodada, além das anteriores).
