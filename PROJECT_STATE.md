# PredixAI BR â€” Estado Oficial do Projeto

## Projeto

PredixAI Platform

Primeiro produto: PredixAI Trader.

## Fase atual

Fase 3 â€” Live Candle Analyzer.

A Fase 0 foi concluÃ­da, a Fase 1 foi criada e validada, e a base atual jÃ¡ possui Perception Engine foundation, Capture Engine foundation, captura manual, Vision Engine foundation, ROI foundation, Image Loader foundation, ROI Crop foundation, ROI Crop Image Export, OCR foundation, OCR Provider Adapter foundation, OCR Pipeline Validation foundation, hotfix de logs do pipeline OCR para validaÃ§Ã£o no Windows do Leo, execuÃ§Ã£o obrigatÃ³ria visÃ­vel do pipeline OCR Mock no `--capture`, OCR Region Mapping foundation, Milestone-004 Region Mapping Expansion, Tesseract Provider foundation, Milestone-005 OCR Real Foundation, Milestone-006 Visual Intelligence Foundation, Milestone-007 Visual Understanding Foundation, Milestone-008 Interface Semantic Foundation, Milestone-009 Market Interface Foundation, Milestone-010 Market Structure Foundation, Milestone-011 Pattern Recognition Foundation, Milestone-012 Pattern Analysis Foundation, Milestone-013 Intelligence Foundation, Milestone-014 Strategy Readiness Foundation, primeira execuÃ§Ã£o local validada no Windows 10 do ambiente do Codex, workspace oficial preparado no Windows 10 do Leo, a primeira validaÃ§Ã£o ao vivo observadora com `--live-once` concluÃ­da, a camada Live Candle Analyzer validada com Field Locator, Field Extractor, Candle Snapshot, Candle Statistics e Live Candle Benchmark, o Project Memory Spine criado como memÃ³ria operacional inicial do projeto, e o Live Loop Countdown Control validado.

## Ãšltimo PTP aprovado

PTP-112 - Mobile-First Strategy Engine e Sessao Simulada.

## PrÃ³ximo PTP pendente

Saneamento futuro dos arquivos trader untracked e legados fora do nucleo PTP-112.

## Status geral

V1 congelada.

A plataforma executa localmente no Windows 10 do ambiente do Codex e no workspace oficial do Windows 10 do Leo, inicializa Core, Perception, Capture Engine e Vision Engine foundation, realiza captura manual em PNG quando solicitada por linha de comando, registra metadados tÃ©cnicos do frame, carrega o Screen Profile padrÃ£o, vincula a regiÃ£o lÃ³gica `FULL_SCREEN`, registra a regiÃ£o no `RegionRegistry`, valida o Region Mapping, carrega bytes do PNG em memÃ³ria como metadados de `ImageBuffer`, registra a ROI padrÃ£o `FULL_SCREEN`, cria metadados de `ROICrop` apÃ³s validaÃ§Ã£o matemÃ¡tica da ROI, exporta a ROI `FULL_SCREEN` em PNG para `captures/rois`, executa OCR real com provider `tesseract`, validaÃ§Ã£o de resultado, cache por SHA256 e benchmark tÃ©cnico, transforma o texto extraÃ­do em blocos estruturados, associa texto Ã  regiÃ£o `FULL_SCREEN`, consolida o Structured OCR Result, cria Visual Snapshot, registra Visual Benchmark, cria Screen Elements, monta Screen Layout, registra Screen Objects, consolida Visual Scene, registra Visual Scene Benchmark, cria Semantic Elements, mapeia Semantic Labels, consolida Semantic Scene, registra Semantic Registry, registra Semantic Benchmark, cria Market Elements, mapeia regiÃµes estruturais de preÃ§o e tempo, consolida Market Scene, registra Market Benchmark, consolida Market Structure, Pattern Detector, Pattern Scene e Pattern Benchmark, executa a primeira validaÃ§Ã£o ao vivo observadora com sessÃ£o, detecÃ§Ã£o de janela, captura programada, leitura bÃ¡sica de mercado, relatÃ³rio e benchmark ao vivo, valida a primeira vela viva com Field Locator, Field Extractor, Candle Snapshot, Candle Statistics e Live Candle Benchmark, possui `data/project_memory/project_memory_spine.json` como memÃ³ria operacional inicial do PTP-083, com ligaÃ§Ã£o mÃ­nima entre `predixai-platform`, `predixai-knowledge`, Codex, ChatGPT, Leo/Arquiteto e OpenClaw futuro, sem dependÃªncia runtime entre repositÃ³rios, e agora preserva o countdown padrÃ£o do `--live-once` enquanto o `--live-loop` usa `countdown_seconds_override=0` para nÃ£o repetir o countdown de 10 segundos a cada ciclo.

## Ambiente principal atual

Windows 10.

Python validado: 3.12.10.

Windows 10 no ambiente do Codex: validado.

Windows 10 do Leo: workspace oficial preparado e validado.

Workspace oficial do projeto:

```text
C:\Users\Leo\Documents\GitHub\predixai-platform
```

Capturas oficiais:

```text
C:\Users\Leo\Documents\GitHub\predixai-platform\captures
```

Logs oficiais:

```text
C:\Users\Leo\Documents\GitHub\predixai-platform\logs
```

Linux Mint serÃ¡ validado depois da estabilidade do workspace oficial no Windows 10 do Leo.

## Regra de auditoria

Nenhum PTP Ã© aprovado sem commit, push para `origin/main` e auditoria posterior.

Toda mudanÃ§a relevante deve atualizar:

- `CHANGELOG.md`
- `predixai_context.json`
- documentos oficiais relacionados

## Resumo do estado atual

- A arquitetura oficial da V1 estÃ¡ congelada.
- A V1 opera em modo Observador.
- A IA Ã© analista, nÃ£o operadora.
- A V1 nÃ£o executa cliques, ordens ou automaÃ§Ã£o.
- O PTP-083 criou `data/project_memory/project_memory_spine.json` como memÃ³ria operacional inicial do projeto.
- O Project Memory Spine registra a ligaÃ§Ã£o mÃ­nima entre `predixai-platform`, `predixai-knowledge`, Codex, ChatGPT, Leo/Arquiteto e OpenClaw futuro, sem alterar o comportamento do Trader.
- O PTP-084 validou o Live Loop Countdown Control: `--live-loop` usa `countdown_seconds_override=0` e `--live-once` preserva o countdown padrÃ£o.
- O PTP-085 criou a Live Evidence Package Foundation: `live_once()` grava evidÃªncias JSON observadoras em `data/live_evidence/`, e `--live-loop` gera evidÃªncias por consequÃªncia ao chamar `live_once()`.
- O PTP-086 criou a fundacao local do OpenClaw em `tools/openclaw/`, com runner seguro por allowlist, relatorios locais ignorados pelo Git e sem commit/push automatico.
- O PTP-087 criou wrappers Windows em scripts/ para executar o OpenClaw com comandos curtos: openclaw.bat, openclaw_status.bat, openclaw_validate.bat e openclaw_precheck.bat.
- O PTP-088 instalou e validou o OpenClaw oficial no notebook, criou comando global `openclaw`, validou Ollama com `qwen2.5:1.5b` e protegeu o clone oficial com `openclaw/` no `.gitignore`.
- O PTP-089 configurou o OpenClaw para usar Ollama local como provider principal, com modelo default `ollama/qwen2.5:1.5b`, preservando custo zero e sem API paga obrigat?ria.
- O PTP-103 publicou o Overnight Observer do Trader, validado com 30 ciclos sinteticos, fechamento de sessao por `close_session(session_id=..., status=...)`, preservacao do PTP-102 e escopo V1 Observador.
- O PTP-112 publicou o Mobile-First Strategy Engine e Sessao Simulada, validando o fluxo Strategy Engine -> Confluence Engine -> Mobile Signal Screen -> Paper Trade -> saldo simulado.
- O PTP-112 preserva o escopo seguro: sem execucao real, sem clique automatico, sem corretora real, sem login, sem senha e sem saldo real.
- A estratÃ©gia Ãºnica da V1 Ã© Rebote Triplo.
- O mercado inicial Ã© Fixed Time.
- O Core inicializa configuraÃ§Ã£o, mÃ³dulos, logs e eventos.
- O Perception Engine identifica ambiente de tela e lista janelas, sem OCR e sem leitura visual.
- O Capture Engine possui sessÃ£o, storage, validaÃ§Ã£o e captura manual em PNG.
- O Vision Engine foundation recebe o caminho da captura, valida metadados do PNG, calcula SHA256 e registra um Frame tÃ©cnico.
- O Vision Engine foundation nÃ£o abre, decodifica, interpreta pixels, usa OCR, OpenCV, Pillow ou IA.
- O Image Loader foundation carrega os bytes do PNG em memÃ³ria e registra apenas metadados tÃ©cnicos em `ImageBuffer`.
- O Image Loader foundation nÃ£o decodifica pixels, nÃ£o recorta ROI, nÃ£o usa OCR, OpenCV, Pillow, IA ou Strategy.
- A ROI foundation registra apenas metadados da regiÃ£o `FULL_SCREEN`, ocupando 100% da captura.
- A ROI foundation nÃ£o recorta imagem, nÃ£o lÃª pixels, nÃ£o usa OCR, OpenCV ou IA.
- O ROI Crop foundation valida matematicamente se a ROI estÃ¡ dentro dos limites do `ImageBuffer` e cria `ROICrop` apenas com metadados.
- O ROI Crop Image Export exporta a ROI `FULL_SCREEN` em PNG reutilizando a captura original, porque a ROI ocupa 100% da imagem.
- O ROI Crop Image Export nÃ£o usa OCR, OpenCV, Pillow, IA, Strategy ou leitura interpretativa de pixels.
- O OCR foundation recebe o PNG exportado da ROI, valida a imagem e prepara o pipeline OCR como contrato tÃ©cnico.
- O OCR foundation nÃ£o extrai texto, nÃ£o usa Tesseract, EasyOCR, PaddleOCR, Gemini, IA, Strategy, Dashboard ou Broker Adapter.
- O OCR Provider Adapter foundation registra providers OCR, seleciona o provider configurado e usa `mock` como provider padrÃ£o.
- O OCR Provider Adapter foundation mantÃ©m `text_extraction_enabled=false` e nÃ£o implementa OCR funcional, IA, Strategy ou Dashboard.
- O OCR Pipeline Validation foundation executa o fluxo Capture â†’ Vision â†’ Frame â†’ ImageBuffer â†’ ROI â†’ ROICrop â†’ ROI Export â†’ OCR Engine â†’ Provider Selector â†’ Mock Provider â†’ OCRResult.
- O OCR Pipeline Validation foundation cria `OCRResult` com `text_extracted=false`, `text=""`, `confidence=0.0` e tempo de processamento, sem OCR real.
- O PTP-017A confirmou que o pipeline OCR completo jÃ¡ estava conectado e padronizou os logs obrigatÃ³rios da validaÃ§Ã£o.
- O PTP-017B confirmou que o pipeline OCR continua conectado e ajustou o logger para exibir no CMD as mensagens literais exigidas na validaÃ§Ã£o do Windows do Leo.
- O PTP-017C tornou obrigatÃ³rio que `python -m predixai.main --capture` execute Vision, ImageBuffer, ROI, ROICrop, ROI Export e OCR Mock com logs no CMD e em `logs/predixai.log`.
- O OCR Region Mapping foundation registra regiÃµes lÃ³gicas de tela em `RegionRegistry`, comeÃ§ando apenas com `FULL_SCREEN`, sem ler texto, pixels ou conteÃºdo visual.
- O Milestone-004 expandiu Region Mapping com Screen Profile Binding, metadata registry, validaÃ§Ã£o de regiÃµes e integraÃ§Ã£o definitiva entre Frame e ROI.
- O Region Mapping registra apenas metadados: nÃ£o lÃª pixels, nÃ£o executa OCR real, nÃ£o usa IA e nÃ£o altera Strategy, Dashboard ou Broker Adapter.
- O PTP-023 criou a fundaÃ§Ã£o do Tesseract Provider, configurado como provider OCR padrÃ£o com idioma `por`, sem executar OCR real naquele PTP.
- A Milestone-005 implementou OCR real com Tesseract sobre a ROI `FULL_SCREEN` exportada.
- O OCR Real Foundation gera `OCRResult` com texto extraÃ­do, confianÃ§a, idioma utilizado, validaÃ§Ã£o, erros, warnings, cache hit/miss, SHA256 e benchmark.
- O Tesseract Provider valida a presenÃ§a do binÃ¡rio, valida idioma configurado e usa fallback configurado quando o idioma `por` nÃ£o estÃ¡ instalado localmente.
- O OCR Cache reutiliza resultados por SHA256 da imagem em `data/ocr_cache`.
- O OCR Benchmark registra tempo de processamento, pico de memÃ³ria, tamanho do texto e status tÃ©cnico.
- A Milestone-006 Visual Intelligence Foundation transforma o texto bruto do OCR em blocos estruturados, sem IA, Gemini, LLM, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.
- O OCR Parser Foundation cria blocos estruturados a partir do texto bruto extraÃ­do pelo OCR.
- O Region Text Mapping associa textos extraÃ­dos Ã s regiÃµes da tela, iniciando apenas com `FULL_SCREEN`.
- O Structured OCR Result consolida regiÃµes, textos, posiÃ§Ãµes, confianÃ§a e metadados em um objeto Ãºnico serializÃ¡vel.
- O Visual Snapshot consolida captura, frame, Region Mapping, ROI Export e Structured OCR em um snapshot tÃ©cnico da tela.
- O Visual Benchmark registra tempo de processamento, memÃ³ria, regiÃµes, blocos, tamanho do texto e cache hits do pipeline visual estruturado.
- A Milestone-007 Visual Understanding Foundation cria a primeira camada estrutural de entendimento da interface, sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter ou tomada de decisÃ£o.
- O Screen Elements Foundation cria elementos visuais determinÃ­sticos a partir do Structured OCR e preserva posiÃ§Ã£o, texto, confianÃ§a e metadados.
- O Screen Layout Builder organiza os elementos em um layout estruturado com raiz de tela e filhos posicionados.
- O Screen Object Registry registra objetos visuais com identificadores estÃ¡veis preparados para reutilizaÃ§Ã£o entre capturas futuras.
- O Visual Scene Builder consolida Visual Snapshot, Structured OCR, Screen Layout e Screen Object Registry em uma representaÃ§Ã£o Ãºnica da tela.
- O Visual Scene Benchmark registra tempo de processamento, memÃ³ria, objetos, elementos, regiÃµes e nÃ³s de layout.
- A Milestone-008 Interface Semantic Foundation cria a primeira camada semÃ¢ntica determinÃ­stica da interface, sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.
- O Semantic Element Foundation deriva entidades semÃ¢nticas a partir de Screen Objects e Visual Scene.
- O Semantic Label Mapper aplica labels determinÃ­sticos por regras simples baseadas em tipo, regiÃ£o, texto e metadados.
- O Semantic Scene Builder consolida Visual Scene, Semantic Elements e Semantic Labels em uma representaÃ§Ã£o semÃ¢ntica Ãºnica da tela.
- O Semantic Registry registra entidades semÃ¢nticas com identificadores estÃ¡veis para reutilizaÃ§Ã£o futura entre capturas.
- O Semantic Benchmark registra tempo de processamento, memÃ³ria, entidades, labels e regiÃµes.
- A Milestone-009 Market Interface Foundation cria a primeira camada estrutural da interface do mercado, sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.
- O Market Element Foundation deriva elementos estruturais de mercado a partir da Semantic Scene, incluindo candidatos para preÃ§o, tempo, ativos e regiÃµes, sem interpretaÃ§Ã£o operacional.
- O Price Region Mapper mapeia regiÃµes estruturais relacionadas a preÃ§o e registra posiÃ§Ã£o e metadados sem interpretar valores.
- O Time Region Mapper mapeia regiÃµes estruturais relacionadas a tempo e registra posiÃ§Ã£o e metadados sem interpretar valores.
- O Market Scene Builder consolida Visual Scene, Semantic Scene, Market Elements e mapeamentos de regiÃµes em uma representaÃ§Ã£o Ãºnica da interface de mercado.
- O Market Benchmark registra tempo de processamento, memÃ³ria, elementos, regiÃµes, entidades e contagens de regiÃµes de preÃ§o e tempo.
- A Milestone-010 Market Structure Foundation consolida Market Entities, Market Entity Registry, Market Structure, Market Structure Validator e Market Structure Benchmark.
- O Pattern Foundation cria padrÃ£o estrutural determinÃ­stico a partir de Market Structure, sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.
- O Pattern Registry registra padrÃµes estruturais com metadados, versionamento e perfil padrÃ£o, sem interpretaÃ§Ã£o inteligente.
- O Pattern Detector usa apenas regras estruturais para derivar padrÃµes a partir da Market Structure.
- O Pattern Scene consolida Market Structure, Pattern Registry e Patterns em uma representaÃ§Ã£o Ãºnica de padrÃµes.
- O Pattern Benchmark registra tempo, memÃ³ria, quantidade de padrÃµes, entidades e regiÃµes.
- A Milestone-013 Intelligence Foundation cria a infraestrutura para transformar Pattern Analysis em hipÃ³teses estruturais de mercado sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automaÃ§Ã£o ou tomada de decisÃ£o.
- O Intelligence Context Foundation consolida o contexto estruturado produzido pelas camadas anteriores.
- O Market Hypothesis Foundation gera hipÃ³teses estruturais do mercado.
- O Hypothesis Evaluator avalia hipÃ³teses apenas com regras estruturais.
- O Intelligence Snapshot consolida Market Structure, Pattern Analysis, Intelligence Context e Market Hypothesis.
- O Intelligence Benchmark registra tempo, memÃ³ria, quantidade de hipÃ³teses, anÃ¡lises, entidades e status.
- A Milestone-014 Strategy Readiness Foundation cria a infraestrutura de preparaÃ§Ã£o para Strategy sem tomada de decisÃ£o, execuÃ§Ã£o ou automaÃ§Ã£o.
- O Signal Foundation representa sinais estruturais derivados de Pattern Analysis e Intelligence Snapshot.
- O Signal Registry e o Signal Scoring Foundation registram e pontuam sinais com regras fixas.
- O Strategy Readiness Snapshot consolida Pattern Analysis, Intelligence Snapshot, Market Hypothesis, Signals e Scores.
- O Strategy Readiness Benchmark registra tempo, memÃ³ria, quantidade de sinais, hipÃ³teses, anÃ¡lises e status.
- A primeira execuÃ§Ã£o local no Windows 10 do ambiente do Codex foi validada.
- O workspace oficial no Windows 10 do Leo foi preparado em `C:\Users\Leo\Documents\GitHub\predixai-platform`.
- `scripts\setup_windows.bat` e `scripts\run_predixai.bat` usam a raiz do repositÃ³rio e recusam `C:\Windows\System32`.
- O guia para Leo executar a validaÃ§Ã£o real estÃ¡ em `docs/setup/Leo_Windows10_Validation.md`.
- O prÃ³ximo PTP pendente serÃ¡ definido pelo Leo.

## PTP-089 - OpenClaw Ollama Provider Binding

Status: CONCLUIDO
Publicado em: 2026-06-30

Resumo:
- OpenClaw configurado para usar Ollama local.
- Vari?vel de ambiente de usu?rio `OLLAMA_API_KEY=ollama-local` definida.
- Provider `ollama` configurado com `baseUrl` local `http://127.0.0.1:11434`.
- Modelo principal definido como `ollama/qwen2.5:1.5b`.
- `openclaw models status` validado com default local.
- `openclaw infer model run` validado usando provider `ollama` e modelo `qwen2.5:1.5b`.

Regra preservada:
- Custo zero.
- Execu??o local.
- Sem OpenAI obrigat?rio.
- Sem API paga obrigat?ria.
- Sem cliques.
- Sem ordens.
- Sem automa??o operacional de corretora.
- Sem decis?o operacional.
- Sem conta real.
- Sem altera??o de estrat?gia.

Ponto t?cnico observado:
- O modelo `qwen2.5:1.5b` ? leve e adequado para o hardware atual, mas pode n?o obedecer instru??es com precis?o alta.
- Pr?ximos PTPs devem usar o modelo local para tarefas simples e supervisionadas primeiro.

Pr?ximo foco:
- PTP-090 - OpenClaw PredixAI Agent Bootstrap.

## PTP-088 - OpenClaw Official Local Installation

Status: CONCLUIDO
Publicado em: 2026-06-30

Resumo:
- OpenClaw oficial clonado localmente.
- Dependencias instaladas com pnpm.
- Build local concluido.
- Comando global `openclaw` criado em `C:\Users\leo\bin\openclaw.cmd`.
- `openclaw --help` validado.
- Ollama instalado localmente.
- Modelo `qwen2.5:1.5b` baixado e validado.
- Pasta `openclaw/` adicionada ao `.gitignore` para nao versionar o clone oficial dentro do PredixAI.

Regra preservada:
- Custo zero.
- Execucao local.
- Sem API paga obrigatoria.
- Sem cliques.
- Sem ordens.
- Sem automacao operacional de corretora.
- Sem decisao operacional.
- Sem conta real.
- Sem alteracao de estrategia.

Ponto tecnico pendente para o proximo PTP:
- OpenClaw ainda esta com modelo default `openai/gpt-5.5` sem autenticacao.
- Proximo PTP deve configurar OpenClaw para usar Ollama local como provedor/modelo principal.

Proximo foco:
- PTP-089 - OpenClaw Ollama Provider Binding.

## PTP-087 - OpenClaw Windows Command Wrapper

Status: CONCLUIDO
Publicado em: 2026-06-30

Resumo:
- Wrappers Windows do OpenClaw criados em scripts/.
- scripts/openclaw.bat permite chamar o runner com argumentos.
- scripts/openclaw_status.bat executa a task status.
- scripts/openclaw_validate.bat executa a task validate_base.
- scripts/openclaw_precheck.bat executa a task ptp086_precheck.
- Os wrappers foram validados localmente e geraram relatorios em tools/openclaw/reports/.

Regra preservada:
- OpenClaw continua limitado por allowlist.
- Sem commit automatico.
- Sem push automatico.
- Sem cliques.
- Sem ordens.
- Sem automacao operacional de corretora.

Proximo foco:
- Evoluir handoff local para gerar pacotes completos de leitura e execucao.

## PTP-086 - OpenClaw Local Handoff Foundation

Status: CONCLUIDO
Publicado em: 2026-06-30

Resumo:
- Fundacao local do OpenClaw criada em `tools/openclaw/`.
- `tools/openclaw/allowlist.json` criado com tarefas seguras permitidas.
- `tools/openclaw/openclaw_runner.py` criado como executor local controlado por allowlist.
- `tools/openclaw/reports/.gitkeep` e `.gitignore` criados para manter a pasta e ignorar relatorios `.json`.
- Tarefas iniciais disponiveis: `status`, `validate_base` e `ptp086_precheck`.
- O bloqueio de comando proibido foi validado com `git push`.

Regra preservada:
- Sem commit automatico.
- Sem push automatico.
- Sem comandos destrutivos.
- Sem cliques.
- Sem ordens.
- Sem automacao operacional de corretora.
- Sem decisao operacional.
- Sem conta real.
- Sem alteracao de estrategia.

Proximo foco:
- Evoluir o handoff local para reduzir trabalho manual de copiar comando, executar e devolver relatorio.

## PTP-085 - Live Evidence Package Foundation

Status: CONCLUIDO
Publicado em: 2026-06-30

Resumo:
- Live Evidence Package Foundation criada.
- `src/predixai/live/live_evidence_package.py` criado com `LiveEvidencePackage` e `LiveEvidencePackageWriter`.
- `live_once()` agora grava uma evidÃªncia JSON observadora ao final da validaÃ§Ã£o ao vivo.
- EvidÃªncias salvas em `data/live_evidence/`.
- `--live-loop` tambÃ©m gera evidÃªncias por consequÃªncia, pois chama `live_once()`.
- A evidÃªncia reaproveita Candle Snapshot, Candle Statistics, Live Candle Benchmark e Live Validation Benchmark.

Regra preservada:
- V1 continua em modo Observador.
- Sem cliques.
- Sem ordens.
- Sem automaÃ§Ã£o operacional de corretora.
- Sem decisÃ£o operacional.
- Sem conta real.
- Sem alteraÃ§Ã£o de estratÃ©gia.

PrÃ³ximo foco:
- PrÃ³ximo PTP a definir pelo Leo.

## PTP-084 â€” Live Loop Countdown Control

Status: CONCLUIDO
Publicado em: 2026-06-30

Resumo:
- Live Loop Countdown Control validado.
- `live_once()` continua funcionando sem argumento.
- `live_once(countdown_seconds_override=0)` foi aceito para uso controlado pelo `--live-loop`.
- `--live-loop` usa `countdown_seconds_override=0` para evitar repetir o countdown de 10 segundos a cada ciclo.
- `--live-once` preserva o countdown padrÃ£o de 10 segundos.

Regra preservada:
- V1 continua em modo Observador.
- Sem cliques.
- Sem ordens.
- Sem automaÃ§Ã£o operacional de corretora.
- Sem decisÃ£o operacional.
- Sem conta real.

PrÃ³ximo foco:
- PrÃ³ximo PTP a definir pelo Leo.

## PTP-083 â€” PredixAI Project Memory Spine

Status: CONCLUIDO
Publicado em: 2026-06-30

Resumo:
- Project Memory Spine criado em `data/project_memory/project_memory_spine.json`.
- MemÃ³ria operacional inicial registrada para continuidade entre estado oficial, contexto estruturado e agentes de execuÃ§Ã£o.
- LigaÃ§Ã£o mÃ­nima registrada entre `predixai-platform`, `predixai-knowledge`, Codex, ChatGPT, Leo/Arquiteto e OpenClaw futuro.
- Nenhuma dependÃªncia runtime foi criada entre `predixai-platform` e `predixai-knowledge`.

Regra preservada:
- V1 continua em modo Observador.
- Sem cliques.
- Sem ordens.
- Sem automaÃ§Ã£o operacional de corretora.
- Sem decisÃ£o operacional.
- Sem conta real.

PrÃ³ximo foco:
- PrÃ³ximo PTP a definir pelo Leo.

## Milestone 017 ? Dashboard Visual Inicial da PredixAI BR

Status: CONCLUIDA
Publicado em: 2026-06-27 09:09:21

Resumo:
- Dashboard local criado com `python -m predixai.main --dashboard`.
- Ultima leitura real exibida no painel visual.
- Estado runtime salvo em `data/runtime/last_live_reading.json`.
- Historico de preco salvo em `data/runtime/live_price_history.json`.
- Grafico inicial de preco implementado no dashboard.
- Estatisticas basicas exibidas: minima, maxima, media e amplitude.
- Comando `--live-loop` criado para multiplas leituras em sequencia.
- Dashboard refinado com horario inicial, horario final, primeiro preco, ultimo preco, variacao e direcao.
- Limite de historico aumentado para 3000 leituras.
- Checkpoint de continuidade entre chats criado com `CHAT_CONTEXT.md` e `CHAT_STARTUP_INSTRUCTIONS.md`.

Comandos validados:
- `python -m predixai.main --live-calibrate`
- `python -m predixai.main --live-once`
- `python -m predixai.main --dashboard`
- `python -m predixai.main --live-loop --loop-count 3 --loop-interval 5`

Regra preservada:
- V1 continua em modo Observador.
- Sem cliques.
- Sem ordens.
- Sem automacao operacional de corretora.
- Sem promessa de lucro.
- Sem previsao ainda.
- Agora nao e previsao. Agora e memoria.

Proximo foco:
- Milestone 018 ? Fundacao da Inteligencia Observadora.

## PTP-090 - OpenClaw PredixAI Agent Bootstrap

Status: CONCLUIDO
Publicado em: 2026-06-30

Resumo:
- OpenClaw instalado e validado no notebook local.
- Ollama instalado e vinculado ao OpenClaw.
- Modelo local ativo: `ollama/qwen2.5:1.5b`.
- Gateway local validado.
- Agente local PredixAI respondeu com execucao embedded/local.
- Workspace do agente mantido em `tools/openclaw/predixai_agent_workspace/` e ignorado pelo Git.

Regra preservada:
- Sem API paga.
- Sem cliques.
- Sem ordens.
- Sem conta real.
- Sem automacao operacional de corretora.
- Sem decisao operacional.
- Sem alteracao de estrategia.

Proximo foco:
- PTP-091 - Supervisao local e fluxo de handoff ChatGPT -> OpenClaw -> PredixAI.

## PTP-091 - PredixAI Supervised Agent Wrapper

Status: CONCLUIDO
Publicado em: 2026-06-30

Resumo:
- Criado wrapper supervisionado para o agente local PredixAI.
- O comando oficial de uso local passa a ser `scripts\predixai_agent.bat`.
- O runner rastreavel fica em `scripts\predixai_agent_runner.py`.
- O wrapper chama OpenClaw local com Ollama e modelo `ollama/qwen2.5:1.5b`.
- O wrapper remove ruido operacional, trace interno e falsas chamadas JSON antes de exibir a resposta util.
- Smoke test validado com `PREDIXAI_AGENT_WRAPPER_OK`.

Regra preservada:
- Sem cliques.
- Sem ordens.
- Sem conta real.
- Sem automacao operacional de corretora.
- Sem API paga obrigatoria.
- Sem promessa de lucro.
- Sem alteracao de estrategia.

Proximo foco:
- PTP-093 â€” Runtime Supervisionado PredixAI

## PTP-093 â€” Runtime Supervisionado PredixAI

- Status: publicado.
- Criados scripts/predixai_handoff.bat e scripts/predixai_h publicado.
- Criados scripts/predixai_handoff.bandoff_runner.py.
- Handoff local ChatGPT/Codex -> OpenClaw -> Ollama validado.
- Guardrail semantico V3 aplicado para bloquear linguagem de operacao, decisao, corretora, conta real, transacoes, promessa de lucro e API paga obrigatoria.
- Validacoes: NORMAL_SAFE_TEST_OK, GUARDRAIL_BLOCK_TEST_OK, COMPILEALL_OK, JSON_OK, DIFF_CHECK_OK.

## PTP-094 â€” Task Protocol Supervisionado

- Status: publicado.
- Criado `scripts/predixai_task_protocol.py`.
- Criado `scripts/predixai_task_protocol.bat`.
- Implementada classificaÃ§Ã£o local de tarefas antes do handoff para OpenClaw/Ollama.
- ClassificaÃ§Ãµes suportadas:
  - `SAFE_LOCAL`: tarefa local segura.
  - `NEEDS_APPROVAL`: tarefa exige aprovaÃ§Ã£o do Leo antes de execuÃ§Ã£o.
  - `BLOCKED`: tarefa bloqueada pelo escopo V1 Observador.
- Testes validados:
  - `SAFE_TASK_TEST_OK`.
  - `APPROVAL_TASK_TEST_OK`.
  - `BLOCKED_TASK_TEST_OK`.
- Corrigida geraÃ§Ã£o de relatÃ³rios com timestamp Ãºnico em microssegundos.
- Mantido escopo V1 Observador: sem clique, sem ordem, sem conta real, sem automaÃ§Ã£o de corretora, sem promessa de lucro e sem API paga obrigatÃ³ria.

DecisÃ£o operacional:
- Toda tarefa sensÃ­vel deve ser classificada antes de chegar ao agente local.
- O agente local continua sem permissÃ£o para decidir, operar, clicar ou publicar sem supervisÃ£o.

## PTP-096 â€” Trader Data Store Foundation

- Status: publicado.
- Criado `src/predixai/trader/data_store.py`.
- Atualizado `src/predixai/trader/__init__.py`.
- Criado `scripts/predixai_trader_db_status.py`.
- Criado `scripts/predixai_trader_db_status.bat`.
- Criado banco local runtime `data/predixai_trader.sqlite3`.
- Banco runtime ignorado pelo Git via `.gitignore`.
- Schema versionado com `schema_version = 1`.
- Tabelas criadas:
  - `schema_metadata`.
  - `market_sessions`.
  - `market_ticks`.
  - `market_candles`.
  - `evidence_records`.
  - `indicator_snapshots`.
  - `support_resistance_zones`.
  - `triple_rebound_observations`.
- ValidaÃ§Ãµes concluÃ­das:
  - `DB_INIT_TEST_OK`.
  - `DB_STATUS_TEST_OK`.
  - `DB_SCHEMA_SANITY_OK`.
  - `DB_GITIGNORE_TEST_OK`.
  - `COMPILEALL_OK`.
  - `JSON_OK`.
  - `DIFF_CHECK_OK`.

DecisÃ£o operacional:
- A V1 passa a ter fundaÃ§Ã£o de memÃ³ria local em SQLite.
- O banco de dados runtime nÃ£o serÃ¡ versionado no GitHub.
- A V1 continua em modo Observador, sem clique, sem ordem, sem conta real, sem automaÃ§Ã£o de corretora e sem promessa de lucro.

## PTP-097 â€” Market Session Recorder

- Status: publicado.
- Criado `src/predixai/trader/market_session_recorder.py`.
- Atualizado `src/predixai/trader/__init__.py`.
- Criado `scripts/predixai_market_session.py`.
- Criado `scripts/predixai_market_session.bat`.
- O Trader agora consegue abrir, consultar, listar e encerrar sessÃµes observadoras de mercado.
- Cada sessÃ£o possui:
  - `asset`.
  - `timeframe`.
  - `mode`.
  - `status`.
  - `started_at`.
  - `ended_at`.
  - `notes`.
  - contagem de ticks.
  - contagem de candles.
  - contagem de evidÃªncias.
- ValidaÃ§Ãµes concluÃ­das:
  - `SESSION_START_TEST_OK`.
  - `SESSION_GET_TEST_OK`.
  - `SESSION_LIST_TEST_OK`.
  - `SESSION_CLOSE_TEST_OK`.
  - `SESSION_FINAL_GET_TEST_OK`.
  - `DB_STATUS_TEST_OK`.
  - `COMPILEALL_OK`.
  - `JSON_OK`.
  - `DIFF_CHECK_OK`.

DecisÃ£o operacional:
- A V1 passa a ter controle formal de sessÃµes de coleta por ativo/timeframe.
- Este PTP ainda nÃ£o grava `live_once` no banco.
- A V1 continua em modo Observador, sem clique, sem ordem, sem conta real, sem automaÃ§Ã£o de corretora e sem promessa de lucro.

## PTP-098 â€” Live Evidence DB Bridge

- Status: publicado.
- Criado `src/predixai/trader/live_evidence_db_bridge.py`.
- Atualizado `src/predixai/trader/__init__.py`.
- Criado `scripts/predixai_live_evidence_db_bridge.py`.
- Criado `scripts/predixai_live_evidence_db_bridge.bat`.
- O Trader agora consegue ingerir evidÃªncias JSON do Live Analyzer para o banco SQLite.
- A ponte consegue:
  - ler arquivo JSON de evidÃªncia.
  - associar evidÃªncia a uma sessÃ£o.
  - criar sessÃ£o automaticamente quando necessÃ¡rio.
  - extrair preÃ§o bÃ¡sico quando disponÃ­vel.
  - registrar `market_tick`.
  - registrar `evidence_record`.
  - calcular `quality_score` bÃ¡sico.
- ValidaÃ§Ãµes concluÃ­das:
  - `SESSION_START_TEST_OK`.
  - `LIVE_EVIDENCE_INGEST_TEST_OK`.
  - `SESSION_GET_AFTER_INGEST_OK`.
  - `SESSION_CLOSE_TEST_OK`.
  - `DB_STATUS_TEST_OK`.
  - `COMPILEALL_OK`.
  - `JSON_OK`.
  - `DIFF_CHECK_OK`.

DecisÃ£o operacional:
- Este PTP valida a ponte isolada entre evidÃªncia e banco.
- A conexÃ£o automÃ¡tica com `live_once`/`live_loop` ficarÃ¡ para etapa posterior.
- A V1 continua em modo Observador, sem clique, sem ordem, sem conta real, sem automaÃ§Ã£o de corretora e sem promessa de lucro.

## PTP-099 â€” Data Quality Score

- Status: publicado.
- Criado `src/predixai/trader/data_quality_score.py`.
- Atualizado `src/predixai/trader/live_evidence_db_bridge.py`.
- Atualizado `src/predixai/trader/__init__.py`.
- Criado `scripts/predixai_data_quality_score.py`.
- Criado `scripts/predixai_data_quality_score.bat`.
- O Trader agora classifica a qualidade das evidÃªncias observadoras antes de consolidar memÃ³ria.
- Labels implementados:
  - `EXCELLENT`.
  - `GOOD`.
  - `FAIR`.
  - `POOR`.
- O score considera:
  - preÃ§o detectado.
  - `candle_snapshot`.
  - `candle_statistics`.
  - `field_values`.
  - `unknown_fields`.
  - benchmark.
  - timestamp.
  - asset.
  - timeframe.
- A ponte `Live Evidence DB Bridge` agora usa `DataQualityScorer` para gravar `quality_score`.
- ValidaÃ§Ãµes concluÃ­das:
  - `GOOD_SCORE_TEST_OK`.
  - `POOR_SCORE_TEST_OK`.
  - `BRIDGE_QUALITY_SCORE_TEST_OK`.
  - `SESSION_GET_AFTER_INGEST_OK`.
  - `SESSION_CLOSE_TEST_OK`.
  - `DB_STATUS_TEST_OK`.
  - `COMPILEALL_OK`.
  - `JSON_OK`.
  - `DIFF_CHECK_OK`.

DecisÃ£o operacional:
- A V1 passa a ter proteÃ§Ã£o inicial contra aprendizado com dado ruim.
- EvidÃªncias com baixa qualidade podem ser identificadas antes de alimentar memÃ³ria e anÃ¡lises futuras.
- A V1 continua em modo Observador, sem clique, sem ordem, sem conta real, sem automaÃ§Ã£o de corretora e sem promessa de lucro.

## PTP-100 â€” Triple RSI Observer

- Status: publicado.
- Criado `src/predixai/trader/triple_rsi_observer.py`.
- Atualizado `src/predixai/trader/__init__.py`.
- Criado `scripts/predixai_triple_rsi_observer.py`.
- Criado `scripts/predixai_triple_rsi_observer.bat`.
- O Trader agora calcula 3 RSI observadores a partir dos preÃ§os gravados em `market_ticks`.
- PerÃ­odos padrÃ£o:
  - RSI curto: 7.
  - RSI mÃ©dio: 14.
  - RSI longo: 21.
- O resultado Ã© salvo em `indicator_snapshots`.
- O CLI permite:
  - calcular Triple RSI por sessÃ£o.
  - listar snapshots de RSI por sessÃ£o.
- ValidaÃ§Ãµes concluÃ­das:
  - `SESSION_START_TEST_OK`.
  - `TEST_TICKS_INSERT_OK`.
  - `TRIPLE_RSI_CALC_TEST_OK`.
  - `TRIPLE_RSI_LIST_TEST_OK`.
  - `SESSION_CLOSE_TEST_OK`.
  - `DB_STATUS_TEST_OK`.
  - `COMPILEALL_OK`.
  - `JSON_OK`.
  - `DIFF_CHECK_OK`.

DecisÃ£o operacional:
- A V1 passa a ter camada observadora dos 3 RSI da estratÃ©gia Rebote Triplo.
- O RSI ainda nÃ£o gera sinal operacional, clique, ordem ou recomendaÃ§Ã£o de entrada.
- A V1 continua em modo Observador, sem clique, sem ordem, sem conta real, sem automaÃ§Ã£o de corretora e sem promessa de lucro.

## PTP-101 â€” Support/Resistance Zone Foundation

- Status: publicado.
- Criado `src/predixai/trader/support_resistance_zones.py`.
- Atualizado `src/predixai/trader/__init__.py`.
- Criado `scripts/predixai_support_resistance_zones.py`.
- Criado `scripts/predixai_support_resistance_zones.bat`.
- O Trader agora detecta zonas observadoras de suporte e resistÃªncia a partir dos preÃ§os gravados em `market_ticks`.
- A detecÃ§Ã£o considera:
  - agrupamento de preÃ§os prÃ³ximos.
  - tolerÃ¢ncia percentual configurÃ¡vel.
  - mÃ­nimo de toques configurÃ¡vel.
  - preÃ§o inferior da zona.
  - preÃ§o superior da zona.
  - preÃ§o mÃ©dio da zona.
  - contagem de toques.
  - `strength_score`.
  - classificaÃ§Ã£o `support` ou `resistance`.
- O resultado Ã© salvo em `support_resistance_zones`.
- O CLI permite:
  - detectar zonas por sessÃ£o.
  - listar zonas por sessÃ£o.
- ValidaÃ§Ãµes concluÃ­das:
  - `SESSION_START_TEST_OK`.
  - `TEST_ZONE_TICKS_INSERT_OK`.
  - `ZONE_DETECTION_TEST_OK`.
  - `ZONE_LIST_TEST_OK`.
  - `SESSION_CLOSE_TEST_OK`.
  - `DB_STATUS_TEST_OK`.
  - `COMPILEALL_OK`.
  - `JSON_OK`.
  - `DIFF_CHECK_OK`.

DecisÃ£o operacional:
- A V1 passa a ter fundaÃ§Ã£o observadora de suporte e resistÃªncia.
- A combinaÃ§Ã£o com Triple RSI e regra de Rebote Triplo ficarÃ¡ para o PTP-102.
- A V1 continua em modo Observador, sem clique, sem ordem, sem conta real, sem automaÃ§Ã£o de corretora e sem promessa de lucro.

## PTP-102 â€” Triple Rebound Observer

- Status: publicado.
- Criado `src/predixai/trader/triple_rebound_observer.py`.
- Atualizado `src/predixai/trader/__init__.py`.
- Criado `scripts/predixai_triple_rebound_observer.py`.
- Criado `scripts/predixai_triple_rebound_observer.bat`.
- O Trader agora observa contexto tÃ©cnico de Rebote Triplo combinando:
  - preÃ§o atual.
  - zona de suporte/resistÃªncia.
  - distÃ¢ncia percentual atÃ© a zona.
  - RSI curto.
  - RSI mÃ©dio.
  - RSI longo.
  - `confidence_score`.
- O resultado Ã© salvo em `triple_rebound_observations`.
- O mÃ³dulo foi ajustado para compatibilidade com o schema legado da tabela `triple_rebound_observations`, incluindo campos obrigatÃ³rios como `touch_index`.
- O CLI permite:
  - observar contexto de Rebote Triplo por sessÃ£o.
  - listar observaÃ§Ãµes por sessÃ£o.
- ValidaÃ§Ãµes concluÃ­das:
  - `TRIPLE_REBOUND_SCHEMA_COMPAT_FIX_APLICADO`.
  - `SESSION_START_TEST_OK`.
  - `TEST_REBOUND_TICKS_INSERT_OK`.
  - `TRIPLE_RSI_PREP_TEST_OK`.
  - `ZONE_PREP_TEST_OK`.
  - `TRIPLE_REBOUND_OBSERVE_TEST_OK`.
  - `TRIPLE_REBOUND_LIST_TEST_OK`.
  - `SESSION_CLOSE_TEST_OK`.
  - `DB_STATUS_TEST_OK`.
  - `COMPILEALL_OK`.
  - `JSON_OK`.
  - `DIFF_CHECK_OK`.

DecisÃ£o operacional:
- A V1 passa a ter observaÃ§Ã£o integrada de Rebote Triplo.
- O observador registra contexto tÃ©cnico, mas nÃ£o gera ordem, clique, recomendaÃ§Ã£o operacional ou promessa de lucro.
- A V1 continua em modo Observador, sem clique, sem ordem, sem conta real e sem automaÃ§Ã£o de corretora.

## PTP-103 - Overnight Observer

- Status: publicado.
- Criado `src/predixai/trader/overnight_observer.py`.
- Atualizado `src/predixai/trader/__init__.py`.
- Criado `scripts/predixai_overnight_observer.py`.
- Criado `scripts/predixai_overnight_observer.bat`.
- O Trader agora possui observador supervisionado de sessoes longas com ciclos controlados.
- O Overnight Observer combina sessao de mercado, ticks sinteticos de validacao, Triple RSI, zonas de suporte/resistencia e Triple Rebound Observer.
- O modo sintetico permite validacao local segura sem corretora, cliques, ordens, conta real ou automacao operacional.
- O erro de fechamento de sessao foi corrigido preservando a assinatura keyword-only de `MarketSessionRecorder.close_session`:
  - `close_session(session_id=session.id, status="completed")`.
- PTP-102 foi validado como preservado por smoke test do `Triple Rebound Observer`.
- Validacoes concluidas:
  - `OVERNIGHT_OBSERVER_SMOKE_OK`.
  - `MARKET_SESSION_SMOKE_OK`.
  - `PTP102_TRIPLE_REBOUND_SMOKE_OK`.
  - `COMPILEALL_OK`.
  - `HELP_OK`.
  - `DIFF_CHECK_OK`.

Decisao operacional:
- A V1 passa a ter observacao supervisionada para sessoes longas/overnight.
- O observador registra contexto tecnico e relatorio local, mas nao gera ordem, clique, recomendacao operacional ou promessa de lucro.
- A V1 continua em modo Observador, sem clique, sem ordem, sem conta real e sem automacao de corretora.
- Proximo passo recomendado: auditoria final da V1 Trader.

<!-- PTP-104-TRADER-V1-FINAL-CLOSURE:START -->
## PTP-104 â€” Trader V1 Final Closure

Status: concluÃ­do

A V1 Observador do PredixAI Trader foi fechada como base tÃ©cnica validada apÃ³s PTP-103.

DecisÃ£o oficial:
PredixAI Trader V1 Observador estÃ¡ encerrada como versÃ£o observadora.

Regras:
- NÃ£o migrar Trader ainda.
- NÃ£o criar predixai-trader ainda.
- NÃ£o iniciar produto novo.
- Knowledge Hub deve registrar o fechamento.
<!-- PTP-104-TRADER-V1-FINAL-CLOSURE:END -->

## Trader Mobile Observer - Session Reset Audit

Status: validacao parcial local em 2026-07-02.

Resumo:
- Mobile Observer roda localmente em modo observador/simulado.
- A leitura leve prioriza preco por `window_title`; OCR completo nao e usado no ciclo mobile de 3s.
- `POST /api/mobile/reset-session` cria backup local, gera novo `session_id`, limpa historico JSON e limpa as tabelas SQLite `signals` e `price_ticks`.
- O painel mobile filtra historico e sinais por `session_id` e ativo atual para evitar mistura entre Cafeina Index, LATAM Index e dados antigos.
- `POST /api/mobile/start?interval=3` preserva lock do leitor e evita leitores duplicados.
- Auditoria curta da logica dos sinais registrada em `docs/trader/MOBILE_SIGNAL_LOGIC_AUDIT.md`.

Validacao pratica:
- Reset real executado com backup local.
- Estado limpo confirmado apos reset.
- Leitor confirmado com `active_reader_count=1`.
- Dois sinais novos fechados ainda pendentes porque a janela ativa no momento da validacao nao era a corretora.

Pendencia:
- Calibrar a logica dos sinais com amostra limpa por ativo e confirmar pelo menos 2 sinais novos fechados em sessao atual.

---

## 2026-07-03 — Linux Mint Robot Runtime Recovery

Status: PUBLICADO

Resumo:
- Ambiente principal migrado para Linux Mint + VS Code.
- Dependências reais do robô instaladas no ambiente virtual `.venv`.
- `requirements.txt` atualizado para refletir dependências reais.
- Banco SQLite base inicializado em `data/predixai_trader.sqlite3`.
- Schema do banco validado como versão 1.
- Correção aplicada em `src/predixai/live/broker_window_detector.py` para impedir quebra no Linux por `ctypes.windll`.
- `python -m predixai.main --help` voltou a funcionar no Linux Mint.
- `compileall` passou em `src` e `scripts`.

Problema encontrado:
- O projeto ainda carregava importação direta de `ctypes.windll`, recurso disponível apenas no Windows.
- Isso impedia o carregamento do módulo principal no Linux Mint.

Solução aplicada:
- O detector de janela passou a tratar Linux como ambiente sem detecção automática via `windll`.
- No Linux, o sistema retorna estado seguro informando que a detecção automática de janela Windows não está disponível.
- A lógica Windows foi preservada.

Pendência:
- Testar dashboard/robô em modo observador.
- Ajustar detecção de janela para Linux usando alternativa compatível, se necessário.
- Evoluir posteriormente para tela inicial multi-corretora com OlympTrade, IQ Option e Avalon.

---

## PTP-108 — Linux Mint Robot Runtime Recovery

Data: 2026-07-03
Status: publicado

Objetivo:
Recuperar o ambiente operacional do PredixAI Trader no Linux Mint.

Alterações realizadas:
- Dependências reais instaladas no ambiente virtual.
- requirements.txt atualizado.
- Banco SQLite inicializado em data/predixai_trader.sqlite3.
- Schema SQLite versão 1 validado.
- Compatibilidade Linux corrigida em src/predixai/live/broker_window_detector.py.
- python -m predixai.main --help voltou a funcionar no Linux Mint.
- Documentação técnica criada em docs/trader/LINUX_MINT_ROBOT_RECOVERY.md.

Pendências:
- Validar dashboard local.
- Validar modo observador.
- PTP-108 publicada no GitHub.


---

## 2026-07-03 — PTP-108 detector pre-commit fix

Status: CORREÇÃO APLICADA ANTES DO COMMIT

Resumo:
- Auditoria pré-commit encontrou risco no método `detect()` do detector de janela.
- A correção Linux precisava preservar o fluxo Windows.
- O detector foi ajustado para retornar estado seguro no Linux e manter a detecção via `ctypes.windll` no Windows.

Validação exigida:
- Executar `compileall`.
- Executar `python -m predixai.main --help`.
- Conferir `git diff --check`.
- Gerar relatório TXT antes do commit.


---

## 2026-07-03 — PTP-108 publicação

Status: PUBLICADO

Resumo:
- PTP-108 publicada após validação local.
- Ambiente Linux Mint recuperado para execução do PredixAI Trader.
- Dependências reais documentadas.
- Banco SQLite inicializado localmente.
- Compatibilidade Linux corrigida no detector de janela.
- GitHub atualizado como memória viva do projeto.

Publicado em: 2026-07-03T12:49:17-03:00

Próxima etapa:
- Validar dashboard local.
- Validar robô em modo observador.
- Depois iniciar PTP-109 — Multi-Broker Startup and Auto Login.

## PTP-108B — Linux Mint Dashboard and Observer Runtime Test

Status: PUBLICADA

Resumo:
- Detector Linux via wmctrl/xprop validado.
- Fluxo Windows com ctypes.windll preservado.
- Leitura observadora em Linux Mint validada.
- Mobile server validado na porta 8766.
- Dashboard/API validado na porta 8765.
- Encoding visual do mobile/compacto corrigido.
- Sessão limpa validada por aproximadamente 13 minutos.
- Histórico limpo validado de 0 até 508 leituras.
- price_ticks SQLite validado de 0 até 508.
- Média observada de leitura: aproximadamente 1.5s.
- Ativo validado: LATAM Index.
- Modo mantido: observador/simulado, sem execução de ordens.

Observações:
- Motor de sinais permaneceu restritivo e não gerou sinais na sessão limpa.
- Isso não bloqueia a PTP-108B, pois o escopo era runtime, leitura, dashboard e mobile.
- Melhorias de sinal, scalper, day trade, backtest, Avalon/Quadcode, OCR, SDK e Session Launcher ficam para PTPs futuras.

## PTP-112 — Mobile-First Strategy Engine e Sessao Simulada

Status: PUBLICADA

Publicado em: 2026-07-05T15:30:23-03:00

Resumo:
- PTP-112 publicada como milestone mobile-first do PredixAI Trader.
- PTP-112A ate PTP-112I concluidas.
- PTP-112J.0, PTP-112J.0.1, PTP-112J.1 e PTP-112J.2 realizadas como auditoria, saneamento e publicacao final controlada.
- Fluxo validado: Strategy Engine -> Confluence Engine -> Mobile Signal Screen -> Paper Trade -> saldo simulado.
- Mobile preservado como controle operacional.
- Dashboard preservado como historico/auditoria.
- Paper trade preservado como sessao simulada.
- Validacao cumulativa aprovada com todos os validadores `scripts/ptp112*.py`.
- `compileall` aprovado em `src` e `scripts`.
- `git diff --check` e `git diff --cached --check` aprovados.

Regra preservada:
- Sem execucao real de ordem.
- Sem clique automatico.
- Sem corretora real.
- Sem login.
- Sem senha.
- Sem saldo real.
- Sem compra/venda real.

Pendencias futuras:
- Decidir destino dos arquivos untracked fora do nucleo em `src/predixai/trader/`.
- Tratar em mini-PTP futura os legados `scripts/run_minimal_trader_test.py` e `tests/test_trader_basic.py`, que importam `PaperTrader` inexistente no desenho atual.
