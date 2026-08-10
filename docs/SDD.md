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
   O diagrama de Venn de sobreposição entre segmentos continua fora do escopo — Chart.js não
   tem isso nativamente e o valor é baixo para o esforço nesta fase; fica no backlog de Fase
   3 se o usuário quiser depois.

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
