# PredixAI BR — Regras Técnicas do Projeto

## Escopo da Fundação Técnica

- A Fase 1 cria apenas a base técnica da plataforma.
- A Fase 1 não implementa Vision, Auditor, Strategy, AI Provider, Dashboard, Broker Adapter ou Trader.
- O Core pode inicializar a aplicação, carregar configuração, configurar logs, registrar versão e registrar módulos.
- Nenhuma lógica financeira pode ser implementada na Fase 1.

## Arquitetura

- A arquitetura oficial da V1 está congelada.
- O Codex não altera arquitetura sem aprovação.
- Cada módulo deve manter responsabilidade clara e baixo acoplamento.
- O Core coordena inicialização, configuração, logs, eventos e registro de módulos.
- Módulos não devem acessar outros módulos de forma desorganizada.

## Segurança

- Segredos nunca devem ser commitados.
- `.env`, `license.local.json` e `secrets.local.json` devem permanecer ignorados pelo Git.
- API Keys devem ficar somente em arquivos locais ignorados pelo Git.
- Logs técnicos não devem registrar segredos.

## Desenvolvimento

- Usar Python 3.11+.
- Manter código limpo, pequeno e coeso.
- Não criar arquivos gigantes.
- Não criar exemplos ou funcionalidades fora da fase atual.
- Não adicionar dependências sem necessidade real.
- Atualizar `CHANGELOG.md`, `predixai_context.json` e checklist quando houver mudança relevante.

## V1

- A V1 opera em modo Observador.
- A V1 não executa cliques.
- A V1 não envia ordens.
- A V1 não usa conta real.
- A IA é analista, não operadora.
- O sinal exibido é sempre sinal sugerido.
