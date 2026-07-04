## 2026-06-30 - PTP-091 PredixAI Supervised Agent Wrapper

- Criado wrapper supervisionado para executar o agente local PredixAI via OpenClaw.
- Criado `scripts/predixai_agent_runner.py`.
- Criado `scripts/predixai_agent.bat`.
- O wrapper limpa ruido de trace, falsa chamada JSON e saidas internas do OpenClaw.
- Validado smoke test com `PREDIXAI_AGENT_WRAPPER_OK`.
- Confirmado COMPILEALL_OK, JSON_OK e DIFF_CHECK_OK.
- Mantido escopo V1 Observador: sem cliques, sem ordens, sem conta real e sem API paga obrigatoria.

## 2026-06-30 - PTP-090 OpenClaw PredixAI Agent Bootstrap

- Validado o OpenClaw local com Gateway, Ollama e modelo `qwen2.5:1.5b`.
- Criado e validado o agente local PredixAI em modo embedded/local.
- Confirmado que o agente responde em portugues e preserva os limites do V1 Observador.
- Confirmado JSON_OK, COMPILEALL_OK e DIFF_CHECK_OK.
- Mantido custo zero: sem API paga, sem conta real, sem cliques, sem ordens e sem automacao de corretora.

## 2026-06-30 - PTP-089 OpenClaw Ollama Provider Binding

- Configurado OpenClaw para usar Ollama local como provider principal.
- Definido `OLLAMA_API_KEY=ollama-local` no ambiente do usu?rio.
- Configurado provider `ollama` com `baseUrl` local `http://127.0.0.1:11434`.
- Definido modelo principal `ollama/qwen2.5:1.5b`.
- Validado `openclaw models status` mostrando default local.
- Validado teste `openclaw infer model run` com provider `ollama` e modelo `qwen2.5:1.5b`.
- Mantido custo zero, execu??o local e aus?ncia de API paga obrigat?ria.

## 2026-06-30 - PTP-088 OpenClaw Official Local Installation

- Instalado e validado o OpenClaw oficial no notebook.
- Criado comando global local `openclaw` apontando para o clone oficial.
- Validado `openclaw --help`.
- Instalado Ollama local.
- Baixado e validado o modelo local `qwen2.5:1.5b`.
- Mantido o escopo gratuito/local, sem API paga, sem clique, sem ordem e sem automacao de corretora.
- Adicionado `openclaw/` ao `.gitignore` para evitar versionar o clone oficial dentro do repositorio PredixAI.

## 2026-06-30 - PTP-087 OpenClaw Windows Command Wrapper

- Criados wrappers Windows em scripts/ para facilitar o uso local do OpenClaw.
- Adicionados scripts/openclaw.bat, scripts/openclaw_status.bat, scripts/openclaw_validate.bat e scripts/openclaw_precheck.bat.
- Mantido o escopo seguro: sem commit automatico, sem push automatico, sem cliques, sem ordens e sem acoes de corretora.

## 2026-06-30 - PTP-086 OpenClaw Local Handoff Foundation

- Criada a fundacao local do OpenClaw em `tools/openclaw/`.
- Adicionado runner seguro com allowlist para executar apenas tarefas locais autorizadas.
- Relatorios locais sao gerados em `tools/openclaw/reports/`, com arquivos `.json` ignorados pelo Git.
- Mantido o escopo seguro: sem commit automatico, sem push automatico, sem comandos destrutivos, sem cliques, sem ordens e sem acoes de corretora.

## 2026-06-30 - PTP-085 Live Evidence Package Foundation

- Criada a fundacao Live Evidence Package para gerar evidencias JSON observadoras ao final de `live_once()`.
- As evidencias sao salvas em `data/live_evidence/` e reaproveitam Candle Snapshot, Candle Statistics, Live Candle Benchmark e Live Validation Benchmark.
- Mantido o escopo V1 Observador, sem cliques, ordens, automacao operacional, decisao operacional, conta real ou alteracao de estrategia.

## 2026-06-30 - PTP-084 Live Loop Countdown Control

- Validado o controle de countdown do `--live-loop` usando `countdown_seconds_override=0`.
- Preservado o countdown padrao de 10 segundos no `--live-once`.
- Mantido o escopo V1 Observador, sem cliques, ordens, automacao operacional, decisao operacional, conta real ou alteracao de estrategia.

## 2026-06-30 - PTP-083 PredixAI Project Memory Spine

- Criada a memoria operacional inicial em `data/project_memory/project_memory_spine.json`.
- Registrada a ligacao minima entre `predixai-platform`, `predixai-knowledge`, Codex, ChatGPT, Leo/Arquiteto e OpenClaw futuro.
- Mantido o escopo V1 Observador, sem cliques, ordens, automacao operacional, decisao operacional, conta real ou dependencia runtime com `predixai-knowledge`.

## 2026-06-27 09:09:21 ? MILESTONE-017

Milestone 017 concluida e publicada.

Entregas:
- Dashboard visual inicial da PredixAI BR.
- Integracao do dashboard com a ultima leitura real.
- Estado runtime oficial.
- Historico de preco.
- Grafico de preco.
- Estatisticas basicas.
- Comando de leitura em loop.
- Refinamento visual do dashboard com horario, variacao e direcao.
- Retencao de historico aumentada para 3000 leituras.
- Checkpoint de continuidade entre chats.

Observacao:
- Produto continua em modo Observador.
- Nenhuma automacao operacional de corretora foi implementada.

# Changelog

## 2026-06-26 - MILESTONE-016 Live Candle Analyzer

- Concluida a fundacao da analise de vela ao vivo com `Field Locator`, `Field Extractor`, `Candle Snapshot`, `Candle Statistics` e `Live Candle Benchmark`.
- Validado o fluxo `python -m predixai.main --live-once` com 6 capturas, extracao de campos e benchmark ao final da vela.
- Registrados os campos detectados e os campos `UNKNOWN` de forma deterministica, sem IA, LLM, Strategy, Dashboard, Broker Adapter ou automacao.
- Corrigido o fechamento do benchmark para usar horario local resiliente e evitar falha de fuso no Windows do Leo.
- Mantida a arquitetura congelada da V1 e a validacao apenas estrutural, sem ampliar o escopo de interpretacao.

## 2026-06-26 - MILESTONE-015 Live Market Validation Foundation

- Concluida a primeira validacao ao vivo observadora com `python -m predixai.main --live-once`.
- Criada a infraestrutura de Live Session, Broker Window Detection, Live Capture Scheduler, Live Market Reading e Live Validation Report.
- Integrado o fluxo ao Core para executar sessoes live sem clicar, operar ou tomar decisao.
- Registrados logs tecnicos no CMD e em `logs/predixai.log` para sessao, janela, capturas, leitura de mercado, relatorio e benchmark ao vivo.
- Mantida a restricao de nao implementar IA, LLM, Gemini, Strategy real, Dashboard, Broker Adapter, automacao de operacoes ou tomada de decisao.

## 2026-06-26 Ã¢â‚¬â€ MILESTONE-014 Strategy Readiness Foundation

- ConcluÃƒÂ­dos os PTPs 068, 069, 070, 071 e 072 em uma ÃƒÂºnica execuÃƒÂ§ÃƒÂ£o de milestone.
- Criada a infraestrutura de Signal Foundation para representar sinais estruturais derivados de Pattern Analysis e Intelligence Snapshot.
- Criado o Signal Registry e o Signal Scoring Foundation com regras fixas e sem tomada de decisÃƒÂ£o.
- Criado o Strategy Readiness Snapshot para consolidar Pattern Analysis, Intelligence Snapshot, Market Hypothesis, Signals e Scores.
- Criado o Strategy Readiness Benchmark com tempo, memÃƒÂ³ria, quantidade de sinais, hipÃƒÂ³teses, anÃƒÂ¡lises e status.
- Mantida a restriÃƒÂ§ÃƒÂ£o de nÃƒÂ£o implementar IA, LLM, Gemini, Strategy real, Dashboard, Broker Adapter, execuÃƒÂ§ÃƒÂ£o de ordens, tomada de decisÃƒÂ£o ou automaÃƒÂ§ÃƒÂ£o.

## 2026-06-26 ? MILESTONE-013 Intelligence Foundation

- Conclu?dos os PTPs 063, 064, 065, 066 e 067 em uma ?nica execu??o de milestone.
- Criado o Intelligence Context Foundation para consolidar o contexto estruturado produzido pelas camadas anteriores.
- Criado o Market Hypothesis Foundation para gerar hip?teses estruturais do mercado.
- Criado o Hypothesis Evaluator para avaliar hip?teses apenas com regras estruturais.
- Criado o Intelligence Snapshot Builder para consolidar Market Structure, Pattern Analysis, Intelligence Context e Market Hypothesis.
- Criado o Intelligence Benchmark com tempo, mem?ria, hip?teses, an?lises, entidades e status.
- Mantida a restri??o de n?o implementar IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automa??o ou tomada de decis?o.

## 2026-06-26 â€” MILESTONE-012 Pattern Analysis Foundation

- ConcluÃ­dos os PTPs 058, 059, 060, 061 e 062 em uma Ãºnica execuÃ§Ã£o de milestone.
- Criado o Pattern Analyzer Foundation para estruturar a anÃ¡lise de padrÃµes sem IA ou tomada de decisÃ£o.
- Criado o Pattern Classification com regras estruturais determinÃ­sticas.
- Criado o Pattern Context Builder para relacionar Pattern Scene, Market Structure, Market Entities e Visual Snapshot.
- Criado o Pattern Analysis Builder para consolidar anÃ¡lise, contexto e classificaÃ§Ã£o.
- Criado o Pattern Analysis Benchmark com tempo, memÃ³ria, padrÃµes analisados, classificaÃ§Ãµes e contextos.
- Mantida a restriÃ§Ã£o de nÃ£o implementar IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.

## 2026-06-26 â€” MILESTONE-011 Pattern Recognition Foundation

- ConcluÃ­dos os PTPs 053, 054, 055, 056 e 057 em uma Ãºnica execuÃ§Ã£o de milestone.
- Criado o Pattern Foundation para representar padrÃµes estruturais derivados da Market Structure.
- Criado o Pattern Registry para registrar padrÃµes com versionamento, perfil e metadados.
- Criado o Pattern Detector com regras determinÃ­sticas sem IA ou tomada de decisÃ£o.
- Criado o Pattern Scene Builder para consolidar Market Structure, Pattern Registry e Patterns.
- Criado o Pattern Benchmark com tempo, memÃ³ria, quantidade de padrÃµes, entidades e regiÃµes.
- Mantida a restriÃ§Ã£o de nÃ£o implementar IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.

## 2026-06-26 â€” MILESTONE-009 Market Interface Foundation

- ConcluÃ­dos os PTPs 043, 044, 045, 046 e 047 em uma Ãºnica execuÃ§Ã£o de milestone.
- Criado o Market Element Foundation para derivar elementos estruturais de mercado a partir da Semantic Scene.
- Criado o Price Region Mapper para mapear regiÃµes estruturais de preÃ§o sem interpretar valores.
- Criado o Time Region Mapper para mapear regiÃµes estruturais de tempo sem interpretar valores.
- Criado o Market Scene Builder para consolidar Visual Scene, Semantic Scene, Market Elements e regiÃµes de mercado.
- Criado o Market Benchmark com tempo de processamento, pico de memÃ³ria, elementos, regiÃµes, entidades e contagens de regiÃµes de preÃ§o e tempo.
- Mantida a restriÃ§Ã£o de nÃ£o implementar IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.

## 2026-06-26 â€” MILESTONE-008 Interface Semantic Foundation

- ConcluÃ­dos os PTPs 038, 039, 040, 041 e 042 em uma Ãºnica execuÃ§Ã£o de milestone.
- Criado o Semantic Element Foundation para derivar entidades semÃ¢nticas de Screen Objects e Visual Scene.
- Criado o Semantic Label Mapper com regras determinÃ­sticas simples baseadas em tipo, regiÃ£o, texto e metadados.
- Criado o Semantic Scene Builder para consolidar Visual Scene, Semantic Elements e Semantic Labels.
- Criado o Semantic Registry para registrar entidades semÃ¢nticas com identificadores estÃ¡veis e reutilizaÃ§Ã£o futura.
- Criado o Semantic Benchmark com tempo de processamento, pico de memÃ³ria, entidades, labels e regiÃµes.
- Mantida a restriÃ§Ã£o de nÃ£o implementar IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.

## 2026-06-26 â€” MILESTONE-007 Visual Understanding Foundation

- ConcluÃ­dos os PTPs 033, 034, 035, 036 e 037 em uma Ãºnica execuÃ§Ã£o de milestone.
- Criado o Screen Elements Foundation para representar elementos visuais derivados do Structured OCR, sem classificaÃ§Ã£o por IA.
- Criado o Screen Layout Builder para organizar elementos em layout estruturado com posiÃ§Ãµes e hierarquia.
- Criado o Screen Object Registry para registrar objetos visuais com identificadores estÃ¡veis e reutilizaÃ§Ã£o futura.
- Criado o Visual Scene Builder para consolidar Visual Snapshot, Structured OCR, Layout e Objetos.
- Criado o Visual Scene Benchmark com tempo de processamento, pico de memÃ³ria, objetos, elementos, regiÃµes e nÃ³s de layout.
- Mantida a restriÃ§Ã£o de nÃ£o implementar IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.

## 2026-06-26 â€” MILESTONE-006 Visual Intelligence Foundation

- ConcluÃ­dos os PTPs 028, 029, 030, 031 e 032 da Milestone-006.
- Criado o OCR Parser para transformar texto bruto do OCR em blocos estruturados.
- Criado o Region Text Mapping para associar textos Ã  regiÃ£o lÃ³gica `FULL_SCREEN`.
- Criado o Structured OCR Result com regiÃµes, textos, posiÃ§Ãµes, confianÃ§a e metadados.
- Criado o Visual Snapshot para consolidar captura, frame, Region Mapping, ROI Export e Structured OCR.
- Criado o Visual Benchmark com tempo de processamento, pico de memÃ³ria, quantidade de regiÃµes, blocos, tamanho do texto e cache hits do OCR.
- Mantida a restriÃ§Ã£o de nÃ£o implementar IA, Gemini, LLM, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.

## 2026-06-25 â€” MILESTONE-005 OCR Real Foundation

- ConcluÃ­dos os PTPs 024, 025, 026 e 027 da Milestone-005.
- Implementada execuÃ§Ã£o real do Tesseract sobre a ROI `FULL_SCREEN` exportada.
- Atualizado `OCRResult` para registrar texto extraÃ­do, confianÃ§a, idioma utilizado, erros, warnings, SHA256 da imagem, cache hit/miss e benchmark.
- Implementada validaÃ§Ã£o de OCR com idioma configurado, fallback de idioma, confianÃ§a mÃ­nima e tratamento de erros.
- Implementado cache OCR por SHA256 em `data/ocr_cache`, com artefatos locais ignorados pelo Git.
- Implementado benchmark tÃ©cnico com tempo de processamento do provider, pico de memÃ³ria, tamanho do texto e status.
- Mantida a restriÃ§Ã£o de nÃ£o implementar IA, Gemini, EasyOCR, PaddleOCR, Strategy, Dashboard, Broker Adapter ou automaÃ§Ã£o de operaÃ§Ãµes.

## 2026-06-25 â€” PTP-023 Tesseract Provider Foundation

- Criada a fundaÃ§Ã£o do Tesseract Provider em `src/predixai/ocr/providers/tesseract_provider.py`.
- Integrado o provider `tesseract` ao `OCREngine`, `ProviderRegistry` e `ProviderSelector`.
- Atualizada a configuraÃ§Ã£o OCR para `provider=tesseract`, `language=por` e `text_extraction_enabled=false`.
- Registrados em log tÃ©cnico `Tesseract Provider iniciado`, versÃ£o detectada, idioma configurado e provider pronto.
- Mantida a restriÃ§Ã£o de nÃ£o executar OCR real, nÃ£o extrair texto, nÃ£o usar IA, Gemini, EasyOCR, PaddleOCR, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 â€” MILESTONE-004 Region Mapping Expansion

- Implementado o Screen Profile Binding com `profile_binding.py` e suporte a regiÃµes no perfil padrÃ£o.
- Expandido o `RegionRegistry` com `version`, `enabled`, `profile_id`, `metadata` e serializaÃ§Ã£o completa.
- Implementado o Region Validation Pipeline para coordenadas, largura, altura, limites da captura e IDs duplicados.
- Integrado o fluxo Capture â†’ Vision â†’ Frame â†’ Region Mapping â†’ ROI â†’ ROICrop â†’ ROI Export â†’ OCR Pipeline.
- Registrados logs de Screen Profile, Region Binding, Region Registry, Region Validation, Region Mapping iniciado e Region Mapping finalizado.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR real, leitura de pixels, OpenCV, Pillow, EasyOCR, Tesseract, Gemini, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 â€” PTP-018 OCR Region Mapping Foundation

- Criada a fundaÃ§Ã£o de Region Mapping em `src/predixai/vision/regions`.
- Criados `region.py`, `region_manager.py`, `region_registry.py`, `region_validator.py` e `__init__.py`.
- Integrado o `RegionManager` ao `VisionEngine` para registrar a regiÃ£o lÃ³gica `FULL_SCREEN` durante o fluxo `python -m predixai.main --capture`.
- Registrados em log tÃ©cnico `Region Manager iniciado`, `Region Registry carregado`, `RegiÃ£o FULL_SCREEN registrada` e o total de regiÃµes registradas.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR real, leitura de pixels, OpenCV, Pillow, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 â€” PTP-017C ForÃ§ar ExecuÃ§Ã£o Real do Pipeline OCR no --capture

- Tornado obrigatÃ³rio o pipeline completo apÃ³s `python -m predixai.main --capture`: Vision, ImageBuffer, ROI, ROICrop, ROI Export e OCR Mock nÃ£o sÃ£o mais ignorados silenciosamente quando exigidos pela captura manual.
- Ajustado o logger para escrever o console em `stdout` e manter o mesmo conteÃºdo em `logs/predixai.log`.
- Padronizadas mensagens literais de validaÃ§Ã£o: `Vision Engine iniciado`, `ImageBuffer criado`, `ROI FULL_SCREEN registrada`, `ROICrop criado`, `ROI exportada`, `Pipeline OCR iniciado`, `Provider selecionado: mock`, `OCR executado (Mock)`, `OCRResult criado` e `Pipeline OCR finalizado`.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR real, extraÃ§Ã£o de texto, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 â€” PTP-017B Hotfix de ValidaÃ§Ã£o do Pipeline OCR no Windows do Leo

- Confirmado que o fluxo `python -m predixai.main --capture` jÃ¡ conectava Capture, Vision, ROI Export, OCR Engine, Provider Selector, Mock Provider e OCRResult.
- Ajustado o logger para exibir no CMD as frases obrigatÃ³rias da validaÃ§Ã£o do Windows do Leo: `OCR Provider Registry iniciado`, `Provider selecionado: mock`, `Resultado criado` e `Pipeline finalizado`.
- Mantidos os logs do PTP-017A para preservar a auditoria anterior do pipeline OCR completo.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR real, extraÃ§Ã£o de texto, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 â€” PTP-017A Validar Pipeline OCR Completo

- Confirmado que o pipeline OCR completo jÃ¡ estava conectado apÃ³s `python -m predixai.main --capture`.
- Padronizados os logs obrigatÃ³rios para registrar `Provider Registry iniciado`, `Provider mock selecionado`, `Imagem enviada ao Mock Provider`, `OCRResult criado` e `Pipeline OCR finalizado`.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR real, extraÃ§Ã£o de texto, Tesseract, EasyOCR, PaddleOCR, OpenCV, Pillow, Gemini, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 â€” PTP-017 OCR Pipeline Validation Foundation

- Validado o fluxo completo Capture â†’ Vision â†’ Frame â†’ ImageBuffer â†’ ROI â†’ ROICrop â†’ ROI Export â†’ OCR Engine â†’ Provider Selector â†’ Mock Provider â†’ OCRResult.
- Atualizado `OCRResult` com `provider`, `status`, `pipeline_ready`, `text_extracted`, `text`, `confidence`, `processing_time_ms` e `timestamp`.
- Adicionada execuÃ§Ã£o mock no contrato de provider OCR, mantendo `text_extracted=false`, `text=""` e `confidence=0.0`.
- Registrados em log tÃ©cnico o inÃ­cio do pipeline OCR, provider selecionado, imagem recebida, execuÃ§Ã£o mock, resultado criado e pipeline finalizado.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR real, Tesseract, EasyOCR, PaddleOCR, Gemini, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 â€” PTP-016 OCR Provider Adapter Foundation

- Criada a arquitetura de adaptadores OCR em `src/predixai/ocr/providers`.
- Criados `base_provider.py`, `mock_provider.py`, `provider_registry.py`, `provider_selector.py` e `providers/__init__.py`.
- Integrado o `OCREngine` ao `ProviderRegistry` e ao `ProviderSelector`.
- Definido `mock` como provider OCR padrÃ£o em `config/config.json`.
- Registrados em log tÃ©cnico o inÃ­cio do OCR Provider Registry, provider `mock` registrado, provider selecionado e confirmaÃ§Ã£o de que o OCR continua sem extraÃ§Ã£o de texto.
- Mantida a restriÃ§Ã£o de nÃ£o implementar Tesseract, EasyOCR, PaddleOCR, Gemini, IA, extraÃ§Ã£o de texto, leitura de RSI, leitura de saldo, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 â€” PTP-015 OCR Foundation

- Criada a fundaÃ§Ã£o OCR em `src/predixai/ocr`.
- Criados `ocr_engine.py`, `ocr_provider.py`, `ocr_result.py`, `ocr_validator.py`, `init.py` e `__init__.py`.
- Integrado o OCR foundation ao fluxo `python -m predixai.main --capture` apÃ³s a exportaÃ§Ã£o do PNG da ROI.
- Adicionado contrato tÃ©cnico para receber imagem da ROI, validar PNG, carregar provider de fundaÃ§Ã£o e marcar o pipeline OCR como pronto.
- Registrados em log tÃ©cnico `OCR Engine iniciado`, `Imagem recebida`, `OCR Provider carregado` e `Pipeline OCR pronto`.
- Mantida a restriÃ§Ã£o de nÃ£o implementar extraÃ§Ã£o de texto, Tesseract, EasyOCR, PaddleOCR, Gemini, IA, Strategy, Dashboard ou Broker Adapter.

## 2026-06-25 â€” PTP-014 ROI Crop Image Export

- Criado o exportador de ROI em `src/predixai/vision`.
- Criados `roi_crop_exporter.py` e `roi_crop_storage.py`.
- Integrada a exportaÃ§Ã£o da ROI `FULL_SCREEN` ao fluxo `python -m predixai.main --capture`.
- A ROI `FULL_SCREEN` Ã© exportada para `captures/rois` reutilizando o PNG original, sem interpretaÃ§Ã£o da imagem.
- Adicionadas regras de `.gitignore` para PNGs gerados em `captures` e `captures/rois`.
- Registrados em log tÃ©cnico o inÃ­cio do ROI Crop Export, ROI exportada, caminho do PNG exportado e tamanho do arquivo.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR, OpenCV, Pillow, IA, Gemini, Strategy, Dashboard, Broker Adapter, Auditor, detecÃ§Ã£o de RSI, saldo, corretora ou leitura interpretativa de pixels.

## 2026-06-25 â€” PTP-013 ROI Crop Foundation

- Criada a fundaÃ§Ã£o do ROI Crop Engine em `src/predixai/vision`.
- Criados `roi_crop_engine.py`, `roi_crop.py` e `roi_crop_validator.py`.
- Integrado o ROI Crop ao fluxo `python -m predixai.main --capture` apÃ³s `ImageBuffer` e ROI estarem disponÃ­veis.
- Adicionada validaÃ§Ã£o matemÃ¡tica de ROI contra os limites da imagem usando apenas metadados.
- Registrados em log tÃ©cnico o inÃ­cio do ROI Crop Engine, ROI validada e `ROICrop` criado.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR, OpenCV, IA, Gemini, Strategy, Dashboard, Broker Adapter, Auditor, reconhecimento de imagem, leitura visual ou recorte de pixels.

## 2026-06-25 â€” PTP-012 Image Loader Foundation

- Criada a fundaÃ§Ã£o do Image Loader em `src/predixai/vision`.
- Criados `image_loader.py`, `image_buffer.py` e `image_loader_validator.py`.
- Integrado o Image Loader ao fluxo `python -m predixai.main --capture` apÃ³s a criaÃ§Ã£o do Frame.
- Adicionada configuraÃ§Ã£o `vision.image_loader.enabled` em `config/config.json`.
- Registrados em log tÃ©cnico o inÃ­cio do Image Loader, PNG carregado em memÃ³ria, tamanho em bytes, largura, altura, SHA256 e metadados do Image Buffer.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR, OpenCV, Pillow, IA, recorte, leitura de pixels, Strategy, Dashboard, Broker Adapter ou Auditor.

## 2026-06-25 â€” PTP-011 Region of Interest Foundation

- Criada a fundaÃ§Ã£o de ROI em `src/predixai/vision`.
- Criados `roi.py`, `roi_manager.py`, `roi_registry.py` e `roi_validator.py`.
- Adicionada a ROI padrÃ£o `FULL_SCREEN` como metadado ocupando 100% da captura.
- Adicionada configuraÃ§Ã£o `vision.roi.enabled` em `config/config.json`.
- Registrados em log tÃ©cnico o inÃ­cio do ROI Manager, o carregamento do ROI Registry, a quantidade de ROIs e a ROI `FULL_SCREEN`.
- Mantida a restriÃ§Ã£o de nÃ£o implementar OCR, OpenCV, recorte, leitura de pixels, IA, Gemini, Dashboard, Strategy, Broker Adapter ou Auditor.

## 2026-06-25 â€” PTP-010 Vision Engine Foundation

- Criada a fundaÃ§Ã£o do Vision Engine em `src/predixai/vision`.
- Criados `Frame`, `FrameStorage`, `FrameValidator` e `VisionEngine` para registrar apenas metadados tÃ©cnicos de capturas.
- Adicionada configuraÃ§Ã£o `vision.enabled` em `config/config.json`.
- Integrado o Vision Engine ao fluxo `python -m predixai.main --capture` apÃ³s a captura manual.
- Registrados em log tÃ©cnico o inÃ­cio do Vision Engine, frame recebido, arquivo validado, SHA256 calculado e metadados registrados.
- Mantida a restriÃ§Ã£o de nÃ£o abrir imagem, nÃ£o interpretar pixels, nÃ£o usar OCR, OpenCV, Pillow, IA, Strategy, Dashboard, Broker Adapter ou Auditor.

## 2026-06-25 â€” PTP-009A Ambiente Oficial Windows 10

- Preparado o workspace oficial em `C:\Users\Leo\Documents\GitHub\predixai-platform`.
- Atualizados `scripts/setup_windows.bat` e `scripts/run_predixai.bat` para resolver a raiz do projeto pela localizaÃ§Ã£o do script.
- Adicionada proteÃ§Ã£o para recusar execuÃ§Ã£o a partir de `C:\Windows\System32`.
- Validada execuÃ§Ã£o de setup, bootstrap e captura manual no workspace oficial.
- Atualizados `PROJECT_STATE.md` e `predixai_context.json` com caminhos oficiais de projeto, logs e capturas.

## 2026-06-25 â€” PTP-009 ValidaÃ§Ã£o Real no Windows 10 do Leo

- Corrigido `PROJECT_STATE.md` para separar Windows 10 do ambiente do Codex e Windows 10 do Leo.
- Criado `docs/setup/Leo_Windows10_Validation.md` com comandos simples para Leo validar setup, execuÃ§Ã£o e captura manual.
- Atualizado `predixai_context.json` para registrar a validaÃ§Ã£o no ambiente Codex como concluÃ­da e a validaÃ§Ã£o no computador do Leo como pendente.
- Mantida a restriÃ§Ã£o de nÃ£o alterar cÃ³digo, arquitetura, mÃ³dulos, escopo da V1 ou funcionalidades.

## 2026-06-25 â€” PTP-008 Arquivos de GovernanÃ§a do Projeto

- Criado `PROJECT_STATE.md` com o estado oficial atual do projeto.
- Criado `DECISIONS.md` com decisÃµes congeladas e regra de alteraÃ§Ã£o.
- Criado `ARCHITECT_NOTES.md` para ideias futuras, backlog tÃ©cnico, riscos e melhorias propostas.
- Atualizado `predixai_context.json` com referÃªncias aos arquivos de governanÃ§a.
- Mantida a restriÃ§Ã£o de nÃ£o alterar cÃ³digo, arquitetura, mÃ³dulos, escopo da V1 ou funcionalidades.

## 2026-06-25 â€” PTP-007 Primeira ExecuÃ§Ã£o Local no Windows 10

- Criado guia `docs/setup/Windows10.md` para primeira execucao local.
- Criado `scripts/setup_windows.bat` para validar Python, ambiente virtual, dependencias, diretorios, compilacao e bootstrap.
- Criado `scripts/run_predixai.bat` para executar a PredixAI localmente com ou sem `--capture`.
- Validada execucao local de `python -m predixai.main` e `python -m predixai.main --capture` no Windows 10.
- Mantida a ausencia de OCR, IA, Strategy, Dashboard, Broker Adapter, Auditor, automacao ou interacao com corretora.

## 2026-06-25 â€” PTP-006 Manual Screen Snapshot Engine

- Implementada captura manual de uma tela inteira via `python -m predixai.main --capture`.
- Criados `capture_snapshot.py` e `snapshot_metadata.py` no Capture Engine.
- A captura manual usa a sessÃ£o do Capture Engine e salva PNG no diretÃ³rio `captures/`.
- Adicionado bootstrap mÃ­nimo de pacote para permitir execuÃ§Ã£o via `python -m predixai.main` a partir da raiz do repositÃ³rio.
- Registrados em log o inÃ­cio da sessÃ£o, horÃ¡rio, resoluÃ§Ã£o, caminho do arquivo e tamanho do arquivo.
- Mantida a ausÃªncia de captura automÃ¡tica, OCR, OpenCV, IA, estratÃ©gia, automaÃ§Ã£o, leitura visual ou interaÃ§Ã£o com corretora.

## 2026-06-25 â€” PTP-005 Screen Capture Engine Foundation

- Criada a fundaÃ§Ã£o do Capture Engine em `src/predixai/capture`.
- Criados contratos tÃ©cnicos para engine, sessÃ£o, storage e validaÃ§Ã£o de captura.
- Adicionada configuraÃ§Ã£o `capture` em `config/config.json`.
- Integrado bootstrap condicional do Capture Engine ao Core.
- Adicionados logs de inicializaÃ§Ã£o, diretÃ³rio, formato e compressÃ£o do Capture Engine.
- Atualizados `PROJECT_RULES.md`, `V1_CHECKLIST.md` e `predixai_context.json`.
- Mantida a restriÃ§Ã£o de nÃ£o realizar captura automÃ¡tica, OCR, IA, estratÃ©gia, automaÃ§Ã£o ou interaÃ§Ã£o com corretora.

## 2026-06-25 â€” PTP-004 Perception Engine Foundation

- Criada a fundaÃ§Ã£o do Perception Engine em `src/predixai/perception`.
- Implementada leitura do ambiente de tela: sistema operacional, resoluÃ§Ã£o, escala, quantidade de monitores, monitor principal e Ã¡rea Ãºtil.
- Implementada listagem inicial de janelas com tÃ­tulo, posiÃ§Ã£o, largura, altura e janela ativa.
- Criado `config/screen_profiles/default_screen_profile.json` sem coordenadas.
- Criada a estrutura inicial do futuro Calibration Wizard sem interface grÃ¡fica.
- Atualizado `config/config.json` com `perception`, `window_detection` e `screen_profile`.
- Integrado log tÃ©cnico de ambiente, monitores, janelas encontradas e janela ativa.
- Atualizados `V1_CHECKLIST.md` e `predixai_context.json`.

## 2026-06-25 â€” PTP-003 FundaÃ§Ã£o tÃ©cnica

- Criada a estrutura tÃ©cnica inicial do projeto.
- Criados os pacotes Python da plataforma em `src/predixai`.
- Criado o Core inicial com bootstrap, leitura de configuraÃ§Ã£o, logger tÃ©cnico e eventos de inicializaÃ§Ã£o.
- Criado `config/config.json` com modo Observador, Fixed Time, Rebote Triplo, Olymp Trade e Gemini.
- Criado `PROJECT_RULES.md` com regras tÃ©cnicas para futuras implementaÃ§Ãµes.
- Criado `requirements.txt` sem dependÃªncias externas para a fundaÃ§Ã£o.
- Criados diretÃ³rios base para testes, dados, logs, capturas e assets.
- Atualizados `MASTER_PLAN.md`, `V1_CHECKLIST.md` e `predixai_context.json`.

## 2026-06-25 â€” PTP-002 CorreÃ§Ã£o documental

- Alinhada a sequÃªncia oficial de fases para Fase 0 a Fase 7.
- Atualizado o contexto do projeto para Fase 1 - FundaÃ§Ã£o TÃ©cnica.
- Marcados como concluÃ­dos os itens documentais jÃ¡ existentes no checklist da V1.
- Separados os mÃ³dulos da V1 dos mÃ³dulos futuros no Blueprint.
- Consolidado o critÃ©rio Ãºnico de sucesso da V1.
- Padronizados os arquivos sensÃ­veis: .env, license.local.json e secrets.local.json.
- Padronizada a linguagem da V1 para modo observando, sinal sugerido e ausÃªncia de execuÃ§Ã£o.

## 2026-06-25 â€” FundaÃ§Ã£o inicial

- Criado repositÃ³rio privado predixai-platform.
- Definido Blueprint Oficial v1.0.
- Definida ConstituiÃ§Ã£o da PredixAI BR.
- Definida arquitetura oficial v1.0.
- Definido checklist completo da V1.
- Definido escopo congelado da V1.


## 2026-06-30 â€” PTP-092

- Adicionado handoff operacional supervisionado do PredixAI.
- Adicionado wrapper scripts/predixai_handoff.bat.
- Adicionado runner scripts/predixai_handoff_runner.py.
- Aplicado guardrail semantico V3 para respostas do agente local.
- Mantido V1 Observador: sem clique, sem ordem, sem conta real, sem promessa de lucro, sem API paga obrigatoria.

## 2026-06-30 â€” PTP-093

- Adicionado runtime supervisionado rÃ¡pido do PredixAI.
- Adicionado `scripts/predixai_runtime_status.py`.
- Adicionado `scripts/predixai_runtime_status.bat`.
- Runtime valida dependÃªncias crÃ­ticas sem chamar o agente local por padrÃ£o.
- Separadas falhas crÃ­ticas de avisos diagnÃ³sticos.
- Mantido V1 Observador e guardrails ativos.

## 2026-06-30 â€” PTP-094

- Adicionado protocolo supervisionado de tarefas.
- Adicionado `scripts/predixai_task_protocol.py`.
- Adicionado `scripts/predixai_task_protocol.bat`.
- Implementadas classificaÃ§Ãµes `SAFE_LOCAL`, `NEEDS_APPROVAL` e `BLOCKED`.
- Implementados testes mÃ­nimos para tarefa segura, tarefa com aprovaÃ§Ã£o e tarefa bloqueada.
- RelatÃ³rios do protocolo agora usam timestamp Ãºnico.
- Mantidos guardrails do modo V1 Observador.

## 2026-06-30 â€” PTP-096

- Adicionada fundaÃ§Ã£o SQLite do PredixAI Trader.
- Adicionado `src/predixai/trader/data_store.py`.
- Atualizado pacote `src/predixai/trader`.
- Adicionados scripts de status do banco.
- Criado schema inicial para sessÃµes, ticks, candles, evidÃªncias, RSI triplo, zonas de suporte/resistÃªncia e observaÃ§Ãµes de Rebote Triplo.
- Banco runtime `data/predixai_trader.sqlite3` ignorado pelo Git.
- Mantido escopo V1 Observador.

## 2026-06-30 â€” PTP-097

- Adicionado Market Session Recorder para o PredixAI Trader.
- Criado CLI `scripts/predixai_market_session.py`.
- Criado wrapper Windows `scripts/predixai_market_session.bat`.
- Adicionadas operaÃ§Ãµes de sessÃ£o:
  - start.
  - list.
  - get.
  - close.
- SessÃµes passam a registrar ativo, timeframe, modo, status, inÃ­cio, fim e notas.
- Mantido escopo V1 Observador.

## 2026-06-30 â€” PTP-098

- Adicionada ponte Live Evidence DB Bridge.
- Criado mÃ³dulo `src/predixai/trader/live_evidence_db_bridge.py`.
- Criado CLI `scripts/predixai_live_evidence_db_bridge.py`.
- Criado wrapper Windows `scripts/predixai_live_evidence_db_bridge.bat`.
- EvidÃªncias JSON podem ser ingeridas no banco SQLite.
- IngestÃ£o cria `market_ticks` e `evidence_records`.
- Adicionado score bÃ¡sico de qualidade da evidÃªncia ingerida.
- Mantido escopo V1 Observador.

## 2026-06-30 â€” PTP-099

- Adicionado Data Quality Score ao PredixAI Trader.
- Criado mÃ³dulo `src/predixai/trader/data_quality_score.py`.
- Criado CLI `scripts/predixai_data_quality_score.py`.
- Criado wrapper Windows `scripts/predixai_data_quality_score.bat`.
- EvidÃªncias passam a receber score formal de qualidade.
- Labels adicionados: EXCELLENT, GOOD, FAIR e POOR.
- A ponte Live Evidence DB Bridge passa a gravar `quality_score` calculado pelo scorer.
- Mantido escopo V1 Observador.

## 2026-06-30 â€” PTP-100

- Adicionado Triple RSI Observer ao PredixAI Trader.
- Criado mÃ³dulo `src/predixai/trader/triple_rsi_observer.py`.
- Criado CLI `scripts/predixai_triple_rsi_observer.py`.
- Criado wrapper Windows `scripts/predixai_triple_rsi_observer.bat`.
- Implementado cÃ¡lculo observador de RSI 7, RSI 14 e RSI 21.
- Resultados persistidos em `indicator_snapshots`.
- Mantido escopo V1 Observador.

## 2026-07-01 â€” PTP-101

- Adicionado Support/Resistance Zone Foundation ao PredixAI Trader.
- Criado mÃ³dulo `src/predixai/trader/support_resistance_zones.py`.
- Criado CLI `scripts/predixai_support_resistance_zones.py`.
- Criado wrapper Windows `scripts/predixai_support_resistance_zones.bat`.
- Implementada detecÃ§Ã£o observadora de zonas por agrupamento de preÃ§os.
- Zonas persistidas em `support_resistance_zones`.
- Mantido escopo V1 Observador.

## 2026-07-01 â€” PTP-102

- Adicionado Triple Rebound Observer ao PredixAI Trader.
- Criado mÃ³dulo `src/predixai/trader/triple_rebound_observer.py`.
- Criado CLI `scripts/predixai_triple_rebound_observer.py`.
- Criado wrapper Windows `scripts/predixai_triple_rebound_observer.bat`.
- Implementada observaÃ§Ã£o integrada de contexto com preÃ§o, zona e Triple RSI.
- ObservaÃ§Ãµes persistidas em `triple_rebound_observations`.
- Adicionado insert compatÃ­vel com schema legado da tabela.
- Mantido escopo V1 Observador.

## 2026-07-01 - PTP-103

- Publicado Overnight Observer do PredixAI Trader.
- Criado modulo `src/predixai/trader/overnight_observer.py`.
- Criado CLI `scripts/predixai_overnight_observer.py`.
- Criado wrapper Windows `scripts/predixai_overnight_observer.bat`.
- Atualizado pacote `src/predixai/trader` para exportar `OvernightObserver`, `OvernightRunResult` e `OvernightCycleResult`.
- Implementada execucao observadora de sessoes longas com ciclos controlados, modo sintetico seguro e relatorio local.
- Corrigida chamada de `MarketSessionRecorder.close_session` para preservar assinatura keyword-only: `close_session(session_id=session.id, status="completed")`.
- Validado Overnight Observer com 30 ciclos sinteticos, Triple RSI, zonas, Triple Rebound e fechamento de sessao.
- Validado PTP-102 como preservado por smoke test do `Triple Rebound Observer`.
- Mantido escopo V1 Observador: sem cliques, sem ordens, sem conta real, sem automacao de corretora, sem decisao operacional e sem promessa de lucro.

## PTP-104 â€” Trader V1 Final Closure

- Encerrada oficialmente a V1 Observador do PredixAI Trader.
- Registrado fechamento pÃ³s PTP-103.
- Preservada regra de nÃ£o migraÃ§Ã£o e nÃ£o criaÃ§Ã£o de novo repositÃ³rio.
- Preparada sincronizaÃ§Ã£o com Knowledge Hub.

## 2026-07-02 - Trader Mobile Observer session reset audit

- Validada rota observadora `POST /api/mobile/reset-session` com backup local antes da limpeza.
- Confirmada nova sessao mobile com `session_id` proprio, limpeza de historico JSON e tabelas SQLite `signals`/`price_ticks`.
- Documentada a logica dos sinais em `docs/trader/MOBILE_SIGNAL_LOGIC_AUDIT.md`.
- Confirmado leitor mobile com lock e `active_reader_count=1` via `POST /api/mobile/start?interval=3`.
- Mantido escopo observador/simulado: sem cliques, sem ordens e sem automacao operacional de corretora.
- Pendente: validar 2 sinais novos fechados quando a janela da corretora estiver ativa e calibrar a logica dos sinais.

---

## 2026-07-03 — Linux Mint Robot Runtime Recovery

### Added
- Registro técnico da recuperação operacional do robô no Linux Mint.
- Dependências reais adicionadas ao `requirements.txt`.
- Documento `docs/trader/LINUX_MINT_ROBOT_RECOVERY.md`.

### Fixed
- Corrigida quebra de importação causada por `ctypes.windll` no Linux.
- `python -m predixai.main --help` voltou a executar no Linux Mint.

### Validated
- `.venv` ativo com Python 3.12.3.
- Flask, Selenium, Pandas, Numpy, OpenCV, Pillow e SQLite importando corretamente.
- Banco `data/predixai_trader.sqlite3` inicializado.
- Schema SQLite versão 1 validado.
- `compileall` executado com sucesso em `src` e `scripts`.

### Notes
- O banco SQLite é memória operacional local e não deve ser tratado como código-fonte.
- Login automático multi-corretora foi aprovado como direção futura, mas ainda não será implementado nesta etapa.

---

## PTP-108 — Linux Mint Robot Runtime Recovery

### Added
- Documento docs/trader/LINUX_MINT_ROBOT_RECOVERY.md.
- Registro da recuperação operacional do robô no Linux Mint.

### Changed
- requirements.txt atualizado com dependências reais do robô.

### Fixed
- Corrigida quebra no Linux causada por ctypes.windll em broker_window_detector.py.

### Validated
- Dependências principais importando corretamente.
- Banco data/predixai_trader.sqlite3 inicializado.
- Schema SQLite versão 1 validado.
- python -m predixai.main --help funcionando no Linux Mint.


---

## PTP-108 — Detector pre-commit fix

### Fixed
- Preservado o fluxo Windows do `BrokerWindowDetector.detect()`.
- Mantido fallback seguro no Linux quando `ctypes.windll` não está disponível.

### Notes
- Correção aplicada antes do commit da PTP-108.


---

## PTP-108 — Publication

### Published
- PTP-108 publicada no GitHub.
- Ambiente operacional Linux Mint recuperado.
- Detector de janela corrigido com fallback seguro para Linux e preservação do fluxo Windows.

### Date
- 2026-07-03T12:49:17-03:00

## 2026-07-04 09:53:31 — PTP-108B publicada

- Publicada a PTP-108B — Linux Mint Dashboard and Observer Runtime Test.
- Corrigido detector Linux para leitura via wmctrl/xprop.
- Validado painel mobile em telefone via porta 8766.
- Corrigido encoding visual do mobile/compacto.
- Validada sessão limpa com leitura estável e SQLite crescendo.
- Mantido modo observador/simulado, sem ordens reais.
- Registrada pendência futura: motor de sinais restritivo.
