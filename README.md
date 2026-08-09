# Sistema Banco de Pessoas (Qualy Vortice)

Sistema Django de gestão de captação de participantes de pesquisa, com login multiusuário
(4 níveis: Administrador, Operador, Visualizador, Freelancer) e painel de permissões.

Leia **[docs/SDD.md](docs/SDD.md)** antes de continuar o desenvolvimento — é o documento
condutor com decisões técnicas, modelo de dados, matriz de permissões e roadmap de fases.

## Rodando localmente

```bash
.venv/Scripts/python.exe manage.py runserver
```

Usuários de teste: `admin_demo`, `operador_demo`, `visualizador_demo`, `freelancer_demo`
(senha `QualyVortice#2026`) — detalhes em `docs/SDD.md`.
