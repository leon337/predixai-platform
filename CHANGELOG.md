# Changelog

## 2026-06-25 — MILESTONE-005 OCR Real Foundation

- Concluídos os PTPs 024, 025, 026 e 027 da Milestone-005.
- Implementada execução real do Tesseract sobre a ROI `FULL_SCREEN` exportada.
- Atualizado `OCRResult` para registrar texto extraído, confiança, idioma utilizado, erros, warnings, SHA256 da imagem, cache hit/miss e benchmark.
- Implementada validação de OCR com idioma configurado, fallback de idioma, confiança mínima e tratamento de erros.
- Implementado cache OCR por SHA256 em `data/ocr_cache`, com artefatos locais ignorados pelo Git.
- Implementado benchmark técnico com tempo de processamento do provider, pico de memória, tamanho do texto e status.
- Mantida a restrição de não implementar IA, Gemini, EasyOCR, PaddleOCR, Strategy, Dashboard, Broker Adapter ou automação de operações.

## 2026-06-25 — PTP-023 Tesseract Provider Foundation

- Criada a fundação do Tesseract Provider em `src/predixai/ocr/providers/tesseract_provider.py`.
- Integrado o provider `tesseract` ao `OCREngine`, `ProviderRegistry` e `ProviderSelector`.
- Atualizada a configuração OCR para `provider=tesseract`, `language=por` e `text_extraction_enabled=false`.
- Registrados em log técnico `Tesseract Provider iniciado`, versão detectada, idioma configurado e provider pronto.
- Mantida a restrição de não executar OCR real, não extrair texto, não usar IA, Gemini, EasyOCR, PaddleOCR, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 — MILESTONE-004 Region Mapping Expansion

- Implementado o Screen Profile Binding com `profile_binding.py` e suporte a regiões no perfil padrão.
- Expandido o `RegionRegistry` com `version`, `enabled`, `profile_id`, `metadata` e serialização completa.
- Implementado o Region Validation Pipeline para coordenadas, largura, altura, limites da captura e IDs duplicados.
- Integrado o fluxo Capture → Vision → Frame → Region Mapping → ROI → ROICrop → ROI Export → OCR Pipeline.
- Registrados logs de Screen Profile, Region Binding, Region Registry, Region Validation, Region Mapping iniciado e Region Mapping finalizado.
- Mantida a restrição de não implementar OCR real, leitura de pixels, OpenCV, Pillow, EasyOCR, Tesseract, Gemini, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 — PTP-018 OCR Region Mapping Foundation

- Criada a fundação de Region Mapping em `src/predixai/vision/regions`.
- Criados `region.py`, `region_manager.py`, `region_registry.py`, `region_validator.py` e `__init__.py`.
- Integrado o `RegionManager` ao `VisionEngine` para registrar a região lógica `FULL_SCREEN` durante o fluxo `python -m predixai.main --capture`.
- Registrados em log técnico `Region Manager iniciado`, `Region Registry carregado`, `Região FULL_SCREEN registrada` e o total de regiões registradas.
- Mantida a restrição de não implementar OCR real, leitura de pixels, OpenCV, Pillow, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 — PTP-017C Forçar Execução Real do Pipeline OCR no --capture

- Tornado obrigatório o pipeline completo após `python -m predixai.main --capture`: Vision, ImageBuffer, ROI, ROICrop, ROI Export e OCR Mock não são mais ignorados silenciosamente quando exigidos pela captura manual.
- Ajustado o logger para escrever o console em `stdout` e manter o mesmo conteúdo em `logs/predixai.log`.
- Padronizadas mensagens literais de validação: `Vision Engine iniciado`, `ImageBuffer criado`, `ROI FULL_SCREEN registrada`, `ROICrop criado`, `ROI exportada`, `Pipeline OCR iniciado`, `Provider selecionado: mock`, `OCR executado (Mock)`, `OCRResult criado` e `Pipeline OCR finalizado`.
- Mantida a restrição de não implementar OCR real, extração de texto, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 — PTP-017B Hotfix de Validação do Pipeline OCR no Windows do Leo

- Confirmado que o fluxo `python -m predixai.main --capture` já conectava Capture, Vision, ROI Export, OCR Engine, Provider Selector, Mock Provider e OCRResult.
- Ajustado o logger para exibir no CMD as frases obrigatórias da validação do Windows do Leo: `OCR Provider Registry iniciado`, `Provider selecionado: mock`, `Resultado criado` e `Pipeline finalizado`.
- Mantidos os logs do PTP-017A para preservar a auditoria anterior do pipeline OCR completo.
- Mantida a restrição de não implementar OCR real, extração de texto, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 — PTP-017A Validar Pipeline OCR Completo

- Confirmado que o pipeline OCR completo já estava conectado após `python -m predixai.main --capture`.
- Padronizados os logs obrigatórios para registrar `Provider Registry iniciado`, `Provider mock selecionado`, `Imagem enviada ao Mock Provider`, `OCRResult criado` e `Pipeline OCR finalizado`.
- Mantida a restrição de não implementar OCR real, extração de texto, Tesseract, EasyOCR, PaddleOCR, OpenCV, Pillow, Gemini, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 — PTP-017 OCR Pipeline Validation Foundation

- Validado o fluxo completo Capture → Vision → Frame → ImageBuffer → ROI → ROICrop → ROI Export → OCR Engine → Provider Selector → Mock Provider → OCRResult.
- Atualizado `OCRResult` com `provider`, `status`, `pipeline_ready`, `text_extracted`, `text`, `confidence`, `processing_time_ms` e `timestamp`.
- Adicionada execução mock no contrato de provider OCR, mantendo `text_extracted=false`, `text=""` e `confidence=0.0`.
- Registrados em log técnico o início do pipeline OCR, provider selecionado, imagem recebida, execução mock, resultado criado e pipeline finalizado.
- Mantida a restrição de não implementar OCR real, Tesseract, EasyOCR, PaddleOCR, Gemini, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 — PTP-016 OCR Provider Adapter Foundation

- Criada a arquitetura de adaptadores OCR em `src/predixai/ocr/providers`.
- Criados `base_provider.py`, `mock_provider.py`, `provider_registry.py`, `provider_selector.py` e `providers/__init__.py`.
- Integrado o `OCREngine` ao `ProviderRegistry` e ao `ProviderSelector`.
- Definido `mock` como provider OCR padrão em `config/config.json`.
- Registrados em log técnico o início do OCR Provider Registry, provider `mock` registrado, provider selecionado e confirmação de que o OCR continua sem extração de texto.
- Mantida a restrição de não implementar Tesseract, EasyOCR, PaddleOCR, Gemini, IA, extração de texto, leitura de RSI, leitura de saldo, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 — PTP-015 OCR Foundation

- Criada a fundação OCR em `src/predixai/ocr`.
- Criados `ocr_engine.py`, `ocr_provider.py`, `ocr_result.py`, `ocr_validator.py`, `init.py` e `__init__.py`.
- Integrado o OCR foundation ao fluxo `python -m predixai.main --capture` após a exportação do PNG da ROI.
- Adicionado contrato técnico para receber imagem da ROI, validar PNG, carregar provider de fundação e marcar o pipeline OCR como pronto.
- Registrados em log técnico `OCR Engine iniciado`, `Imagem recebida`, `OCR Provider carregado` e `Pipeline OCR pronto`.
- Mantida a restrição de não implementar extração de texto, Tesseract, EasyOCR, PaddleOCR, Gemini, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 — PTP-014 ROI Crop Image Export

- Criado o exportador de ROI em `src/predixai/vision`.
- Criados `roi_crop_exporter.py` e `roi_crop_storage.py`.
- Integrada a exportação da ROI `FULL_SCREEN` ao fluxo `python -m predixai.main --capture`.
- A ROI `FULL_SCREEN` é exportada para `captures/rois` reutilizando o PNG original, sem interpretação da imagem.
- Adicionadas regras de `.gitignore` para PNGs gerados em `captures` e `captures/rois`.
- Registrados em log técnico o início do ROI Crop Export, ROI exportada, caminho do PNG exportado e tamanho do arquivo.
- Mantida a restrição de não implementar OCR, OpenCV, Pillow, IA, Gemini, Strategy, Dashboard, Broker Adapter, Auditor, detecção de RSI, saldo, corretora ou leitura interpretativa de pixels.

## 2026-06-25 — PTP-013 ROI Crop Foundation

- Criada a fundação do ROI Crop Engine em `src/predixai/vision`.
- Criados `roi_crop_engine.py`, `roi_crop.py` e `roi_crop_validator.py`.
- Integrado o ROI Crop ao fluxo `python -m predixai.main --capture` após `ImageBuffer` e ROI estarem disponíveis.
- Adicionada validação matemática de ROI contra os limites da imagem usando apenas metadados.
- Registrados em log técnico o início do ROI Crop Engine, ROI validada e `ROICrop` criado.
- Mantida a restrição de não implementar OCR, OpenCV, IA, Gemini, Strategy, Dashboard, Broker Adapter, Auditor, reconhecimento de imagem, leitura visual ou recorte de pixels.

## 2026-06-25 — PTP-012 Image Loader Foundation

- Criada a fundação do Image Loader em `src/predixai/vision`.
- Criados `image_loader.py`, `image_buffer.py` e `image_loader_validator.py`.
- Integrado o Image Loader ao fluxo `python -m predixai.main --capture` após a criação do Frame.
- Adicionada configuração `vision.image_loader.enabled` em `config/config.json`.
- Registrados em log técnico o início do Image Loader, PNG carregado em memória, tamanho em bytes, largura, altura, SHA256 e metadados do Image Buffer.
- Mantida a restrição de não implementar OCR, OpenCV, Pillow, IA, recorte, leitura de pixels, Strategy, Dashboard, Broker Adapter ou Auditor.

## 2026-06-25 — PTP-011 Region of Interest Foundation

- Criada a fundação de ROI em `src/predixai/vision`.
- Criados `roi.py`, `roi_manager.py`, `roi_registry.py` e `roi_validator.py`.
- Adicionada a ROI padrão `FULL_SCREEN` como metadado ocupando 100% da captura.
- Adicionada configuração `vision.roi.enabled` em `config/config.json`.
- Registrados em log técnico o início do ROI Manager, o carregamento do ROI Registry, a quantidade de ROIs e a ROI `FULL_SCREEN`.
- Mantida a restrição de não implementar OCR, OpenCV, recorte, leitura de pixels, IA, Gemini, Dashboard, Strategy, Broker Adapter ou Auditor.

## 2026-06-25 — PTP-010 Vision Engine Foundation

- Criada a fundação do Vision Engine em `src/predixai/vision`.
- Criados `Frame`, `FrameStorage`, `FrameValidator` e `VisionEngine` para registrar apenas metadados técnicos de capturas.
- Adicionada configuração `vision.enabled` em `config/config.json`.
- Integrado o Vision Engine ao fluxo `python -m predixai.main --capture` após a captura manual.
- Registrados em log técnico o início do Vision Engine, frame recebido, arquivo validado, SHA256 calculado e metadados registrados.
- Mantida a restrição de não abrir imagem, não interpretar pixels, não usar OCR, OpenCV, Pillow, IA, Strategy, Dashboard, Broker Adapter ou Auditor.

## 2026-06-25 — PTP-009A Ambiente Oficial Windows 10

- Preparado o workspace oficial em `C:\Users\Leo\Documents\GitHub\predixai-platform`.
- Atualizados `scripts/setup_windows.bat` e `scripts/run_predixai.bat` para resolver a raiz do projeto pela localização do script.
- Adicionada proteção para recusar execução a partir de `C:\Windows\System32`.
- Validada execução de setup, bootstrap e captura manual no workspace oficial.
- Atualizados `PROJECT_STATE.md` e `predixai_context.json` com caminhos oficiais de projeto, logs e capturas.

## 2026-06-25 — PTP-009 Validação Real no Windows 10 do Leo

- Corrigido `PROJECT_STATE.md` para separar Windows 10 do ambiente do Codex e Windows 10 do Leo.
- Criado `docs/setup/Leo_Windows10_Validation.md` com comandos simples para Leo validar setup, execução e captura manual.
- Atualizado `predixai_context.json` para registrar a validação no ambiente Codex como concluída e a validação no computador do Leo como pendente.
- Mantida a restrição de não alterar código, arquitetura, módulos, escopo da V1 ou funcionalidades.

## 2026-06-25 — PTP-008 Arquivos de Governança do Projeto

- Criado `PROJECT_STATE.md` com o estado oficial atual do projeto.
- Criado `DECISIONS.md` com decisões congeladas e regra de alteração.
- Criado `ARCHITECT_NOTES.md` para ideias futuras, backlog técnico, riscos e melhorias propostas.
- Atualizado `predixai_context.json` com referências aos arquivos de governança.
- Mantida a restrição de não alterar código, arquitetura, módulos, escopo da V1 ou funcionalidades.

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
