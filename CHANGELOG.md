# Changelog

## 2026-06-25 — PTP-007 Primeira Execução Local no Windows 10

- Criado guia `docs/setup/Windows10.md` para primeira execucao local.
- Criado `scripts/setup_windows.bat` para validar Python, ambiente virtual, dependencias, diretorios, compilacao e bootstrap.
- Criado `scripts/run_predixai.bat` para executar a PredixAI localmente com ou sem `--capture`.
- Validada execucao local de `python -m predixai.main` e `python -m predixai.main --capture` no Windows 10.
- Mantida a ausencia de OCR, IA, Strategy, Dashboard, Broker Adapter, Auditor, automacao ou interacao com corretora.

## 2026-06-25 — PTP-006 Manual Screen Snapshot Engine

- Implementada captura manual de uma tela inteira via `python -m predixai.main --capture`.
- Criados `capture_snapshot.py` e `snapshot_metadata.py` no Capture Engine.
- A captura manual usa a sessão do Capture Engine e salva PNG no diretório `captures/`.
- Adicionado bootstrap mínimo de pacote para permitir execução via `python -m predixai.main` a partir da raiz do repositório.
- Registrados em log o início da sessão, horário, resolução, caminho do arquivo e tamanho do arquivo.
- Mantida a ausência de captura automática, OCR, OpenCV, IA, estratégia, automação, leitura visual ou interação com corretora.

## 2026-06-25 — PTP-005 Screen Capture Engine Foundation

- Criada a fundação do Capture Engine em `src/predixai/capture`.
- Criados contratos técnicos para engine, sessão, storage e validação de captura.
- Adicionada configuração `capture` em `config/config.json`.
- Integrado bootstrap condicional do Capture Engine ao Core.
- Adicionados logs de inicialização, diretório, formato e compressão do Capture Engine.
- Atualizados `PROJECT_RULES.md`, `V1_CHECKLIST.md` e `predixai_context.json`.
- Mantida a restrição de não realizar captura automática, OCR, IA, estratégia, automação ou interação com corretora.

## 2026-06-25 — PTP-004 Perception Engine Foundation

- Criada a fundação do Perception Engine em `src/predixai/perception`.
- Implementada leitura do ambiente de tela: sistema operacional, resolução, escala, quantidade de monitores, monitor principal e área útil.
- Implementada listagem inicial de janelas com título, posição, largura, altura e janela ativa.
- Criado `config/screen_profiles/default_screen_profile.json` sem coordenadas.
- Criada a estrutura inicial do futuro Calibration Wizard sem interface gráfica.
- Atualizado `config/config.json` com `perception`, `window_detection` e `screen_profile`.
- Integrado log técnico de ambiente, monitores, janelas encontradas e janela ativa.
- Atualizados `V1_CHECKLIST.md` e `predixai_context.json`.

## 2026-06-25 — PTP-003 Fundação técnica

- Criada a estrutura técnica inicial do projeto.
- Criados os pacotes Python da plataforma em `src/predixai`.
- Criado o Core inicial com bootstrap, leitura de configuração, logger técnico e eventos de inicialização.
- Criado `config/config.json` com modo Observador, Fixed Time, Rebote Triplo, Olymp Trade e Gemini.
- Criado `PROJECT_RULES.md` com regras técnicas para futuras implementações.
- Criado `requirements.txt` sem dependências externas para a fundação.
- Criados diretórios base para testes, dados, logs, capturas e assets.
- Atualizados `MASTER_PLAN.md`, `V1_CHECKLIST.md` e `predixai_context.json`.

## 2026-06-25 — PTP-002 Correção documental

- Alinhada a sequência oficial de fases para Fase 0 a Fase 7.
- Atualizado o contexto do projeto para Fase 1 - Fundação Técnica.
- Marcados como concluídos os itens documentais já existentes no checklist da V1.
- Separados os módulos da V1 dos módulos futuros no Blueprint.
- Consolidado o critério único de sucesso da V1.
- Padronizados os arquivos sensíveis: .env, license.local.json e secrets.local.json.
- Padronizada a linguagem da V1 para modo observando, sinal sugerido e ausência de execução.

## 2026-06-25 — Fundação inicial

- Criado repositório privado predixai-platform.
- Definido Blueprint Oficial v1.0.
- Definida Constituição da PredixAI BR.
- Definida arquitetura oficial v1.0.
- Definido checklist completo da V1.
- Definido escopo congelado da V1.
