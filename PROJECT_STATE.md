# PredixAI BR — Estado Oficial do Projeto

## Projeto

PredixAI Platform

Primeiro produto: PredixAI Trader.

## Fase atual

Fase 3 — Live Market Validation.

A Fase 0 foi concluída, a Fase 1 foi criada e validada, e a base atual já possui Perception Engine foundation, Capture Engine foundation, captura manual, Vision Engine foundation, ROI foundation, Image Loader foundation, ROI Crop foundation, ROI Crop Image Export, OCR foundation, OCR Provider Adapter foundation, OCR Pipeline Validation foundation, hotfix de logs do pipeline OCR para validação no Windows do Leo, execução obrigatória visível do pipeline OCR Mock no `--capture`, OCR Region Mapping foundation, Milestone-004 Region Mapping Expansion, Tesseract Provider foundation, Milestone-005 OCR Real Foundation, Milestone-006 Visual Intelligence Foundation, Milestone-007 Visual Understanding Foundation, Milestone-008 Interface Semantic Foundation, Milestone-009 Market Interface Foundation, Milestone-010 Market Structure Foundation, Milestone-011 Pattern Recognition Foundation, Milestone-012 Pattern Analysis Foundation, Milestone-013 Intelligence Foundation, Milestone-014 Strategy Readiness Foundation, primeira execução local validada no Windows 10 do ambiente do Codex, workspace oficial preparado no Windows 10 do Leo e a primeira validação ao vivo observador com `--live-once` concluída.

## Último PTP aprovado

PTP-077 — Live Validation Report.

## Próximo PTP pendente

PTP-078 — Próximo PTP a definir pelo Leo.

## Status geral

V1 congelada.

A plataforma executa localmente no Windows 10 do ambiente do Codex e no workspace oficial do Windows 10 do Leo, inicializa Core, Perception, Capture Engine e Vision Engine foundation, realiza captura manual em PNG quando solicitada por linha de comando, registra metadados técnicos do frame, carrega o Screen Profile padrão, vincula a região lógica `FULL_SCREEN`, registra a região no `RegionRegistry`, valida o Region Mapping, carrega bytes do PNG em memória como metadados de `ImageBuffer`, registra a ROI padrão `FULL_SCREEN`, cria metadados de `ROICrop` após validação matemática da ROI, exporta a ROI `FULL_SCREEN` em PNG para `captures/rois`, executa OCR real com provider `tesseract`, validação de resultado, cache por SHA256 e benchmark técnico, transforma o texto extraído em blocos estruturados, associa texto à região `FULL_SCREEN`, consolida o Structured OCR Result, cria Visual Snapshot, registra Visual Benchmark, cria Screen Elements, monta Screen Layout, registra Screen Objects, consolida Visual Scene, registra Visual Scene Benchmark, cria Semantic Elements, mapeia Semantic Labels, consolida Semantic Scene, registra Semantic Registry, registra Semantic Benchmark, cria Market Elements, mapeia regiões estruturais de preço e tempo, consolida Market Scene, registra Market Benchmark, consolida Market Structure, Pattern Detector, Pattern Scene e Pattern Benchmark e agora também executa a primeira validação ao vivo observadora com sessão, detecção de janela, captura programada, leitura básica de mercado, relatório e benchmark ao vivo, com logs visíveis no CMD e em `logs/predixai.log`.

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

Linux Mint será validado depois da estabilidade do workspace oficial no Windows 10 do Leo.

## Regra de auditoria

Nenhum PTP é aprovado sem commit, push para `origin/main` e auditoria posterior.

Toda mudança relevante deve atualizar:

- `CHANGELOG.md`
- `predixai_context.json`
- documentos oficiais relacionados

## Resumo do estado atual

- A arquitetura oficial da V1 está congelada.
- A V1 opera em modo Observador.
- A IA é analista, não operadora.
- A V1 não executa cliques, ordens ou automação.
- A estratégia única da V1 é Rebote Triplo.
- O mercado inicial é Fixed Time.
- O Core inicializa configuração, módulos, logs e eventos.
- O Perception Engine identifica ambiente de tela e lista janelas, sem OCR e sem leitura visual.
- O Capture Engine possui sessão, storage, validação e captura manual em PNG.
- O Vision Engine foundation recebe o caminho da captura, valida metadados do PNG, calcula SHA256 e registra um Frame técnico.
- O Vision Engine foundation não abre, decodifica, interpreta pixels, usa OCR, OpenCV, Pillow ou IA.
- O Image Loader foundation carrega os bytes do PNG em memória e registra apenas metadados técnicos em `ImageBuffer`.
- O Image Loader foundation não decodifica pixels, não recorta ROI, não usa OCR, OpenCV, Pillow, IA ou Strategy.
- A ROI foundation registra apenas metadados da região `FULL_SCREEN`, ocupando 100% da captura.
- A ROI foundation não recorta imagem, não lê pixels, não usa OCR, OpenCV ou IA.
- O ROI Crop foundation valida matematicamente se a ROI está dentro dos limites do `ImageBuffer` e cria `ROICrop` apenas com metadados.
- O ROI Crop Image Export exporta a ROI `FULL_SCREEN` em PNG reutilizando a captura original, porque a ROI ocupa 100% da imagem.
- O ROI Crop Image Export não usa OCR, OpenCV, Pillow, IA, Strategy ou leitura interpretativa de pixels.
- O OCR foundation recebe o PNG exportado da ROI, valida a imagem e prepara o pipeline OCR como contrato técnico.
- O OCR foundation não extrai texto, não usa Tesseract, EasyOCR, PaddleOCR, Gemini, IA, Strategy, Dashboard ou Broker Adapter.
- O OCR Provider Adapter foundation registra providers OCR, seleciona o provider configurado e usa `mock` como provider padrão.
- O OCR Provider Adapter foundation mantém `text_extraction_enabled=false` e não implementa OCR funcional, IA, Strategy ou Dashboard.
- O OCR Pipeline Validation foundation executa o fluxo Capture → Vision → Frame → ImageBuffer → ROI → ROICrop → ROI Export → OCR Engine → Provider Selector → Mock Provider → OCRResult.
- O OCR Pipeline Validation foundation cria `OCRResult` com `text_extracted=false`, `text=""`, `confidence=0.0` e tempo de processamento, sem OCR real.
- O PTP-017A confirmou que o pipeline OCR completo já estava conectado e padronizou os logs obrigatórios da validação.
- O PTP-017B confirmou que o pipeline OCR continua conectado e ajustou o logger para exibir no CMD as mensagens literais exigidas na validação do Windows do Leo.
- O PTP-017C tornou obrigatório que `python -m predixai.main --capture` execute Vision, ImageBuffer, ROI, ROICrop, ROI Export e OCR Mock com logs no CMD e em `logs/predixai.log`.
- O OCR Region Mapping foundation registra regiões lógicas de tela em `RegionRegistry`, começando apenas com `FULL_SCREEN`, sem ler texto, pixels ou conteúdo visual.
- O Milestone-004 expandiu Region Mapping com Screen Profile Binding, metadata registry, validação de regiões e integração definitiva entre Frame e ROI.
- O Region Mapping registra apenas metadados: não lê pixels, não executa OCR real, não usa IA e não altera Strategy, Dashboard ou Broker Adapter.
- O PTP-023 criou a fundação do Tesseract Provider, configurado como provider OCR padrão com idioma `por`, sem executar OCR real naquele PTP.
- A Milestone-005 implementou OCR real com Tesseract sobre a ROI `FULL_SCREEN` exportada.
- O OCR Real Foundation gera `OCRResult` com texto extraído, confiança, idioma utilizado, validação, erros, warnings, cache hit/miss, SHA256 e benchmark.
- O Tesseract Provider valida a presença do binário, valida idioma configurado e usa fallback configurado quando o idioma `por` não está instalado localmente.
- O OCR Cache reutiliza resultados por SHA256 da imagem em `data/ocr_cache`.
- O OCR Benchmark registra tempo de processamento, pico de memória, tamanho do texto e status técnico.
- A Milestone-006 Visual Intelligence Foundation transforma o texto bruto do OCR em blocos estruturados, sem IA, Gemini, LLM, Strategy, Dashboard, Broker Adapter, automação ou tomada de decisão.
- O OCR Parser Foundation cria blocos estruturados a partir do texto bruto extraído pelo OCR.
- O Region Text Mapping associa textos extraídos às regiões da tela, iniciando apenas com `FULL_SCREEN`.
- O Structured OCR Result consolida regiões, textos, posições, confiança e metadados em um objeto único serializável.
- O Visual Snapshot consolida captura, frame, Region Mapping, ROI Export e Structured OCR em um snapshot técnico da tela.
- O Visual Benchmark registra tempo de processamento, memória, regiões, blocos, tamanho do texto e cache hits do pipeline visual estruturado.
- A Milestone-007 Visual Understanding Foundation cria a primeira camada estrutural de entendimento da interface, sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter ou tomada de decisão.
- O Screen Elements Foundation cria elementos visuais determinísticos a partir do Structured OCR e preserva posição, texto, confiança e metadados.
- O Screen Layout Builder organiza os elementos em um layout estruturado com raiz de tela e filhos posicionados.
- O Screen Object Registry registra objetos visuais com identificadores estáveis preparados para reutilização entre capturas futuras.
- O Visual Scene Builder consolida Visual Snapshot, Structured OCR, Screen Layout e Screen Object Registry em uma representação única da tela.
- O Visual Scene Benchmark registra tempo de processamento, memória, objetos, elementos, regiões e nós de layout.
- A Milestone-008 Interface Semantic Foundation cria a primeira camada semântica determinística da interface, sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automação ou tomada de decisão.
- O Semantic Element Foundation deriva entidades semânticas a partir de Screen Objects e Visual Scene.
- O Semantic Label Mapper aplica labels determinísticos por regras simples baseadas em tipo, região, texto e metadados.
- O Semantic Scene Builder consolida Visual Scene, Semantic Elements e Semantic Labels em uma representação semântica única da tela.
- O Semantic Registry registra entidades semânticas com identificadores estáveis para reutilização futura entre capturas.
- O Semantic Benchmark registra tempo de processamento, memória, entidades, labels e regiões.
- A Milestone-009 Market Interface Foundation cria a primeira camada estrutural da interface do mercado, sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automação ou tomada de decisão.
- O Market Element Foundation deriva elementos estruturais de mercado a partir da Semantic Scene, incluindo candidatos para preço, tempo, ativos e regiões, sem interpretação operacional.
- O Price Region Mapper mapeia regiões estruturais relacionadas a preço e registra posição e metadados sem interpretar valores.
- O Time Region Mapper mapeia regiões estruturais relacionadas a tempo e registra posição e metadados sem interpretar valores.
- O Market Scene Builder consolida Visual Scene, Semantic Scene, Market Elements e mapeamentos de regiões em uma representação única da interface de mercado.
- O Market Benchmark registra tempo de processamento, memória, elementos, regiões, entidades e contagens de regiões de preço e tempo.
- A Milestone-010 Market Structure Foundation consolida Market Entities, Market Entity Registry, Market Structure, Market Structure Validator e Market Structure Benchmark.
- O Pattern Foundation cria padrão estrutural determinístico a partir de Market Structure, sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automação ou tomada de decisão.
- O Pattern Registry registra padrões estruturais com metadados, versionamento e perfil padrão, sem interpretação inteligente.
- O Pattern Detector usa apenas regras estruturais para derivar padrões a partir da Market Structure.
- O Pattern Scene consolida Market Structure, Pattern Registry e Patterns em uma representação única de padrões.
- O Pattern Benchmark registra tempo, memória, quantidade de padrões, entidades e regiões.
- A Milestone-013 Intelligence Foundation cria a infraestrutura para transformar Pattern Analysis em hipóteses estruturais de mercado sem IA, LLM, Gemini, Strategy, Dashboard, Broker Adapter, automação ou tomada de decisão.
- O Intelligence Context Foundation consolida o contexto estruturado produzido pelas camadas anteriores.
- O Market Hypothesis Foundation gera hipóteses estruturais do mercado.
- O Hypothesis Evaluator avalia hipóteses apenas com regras estruturais.
- O Intelligence Snapshot consolida Market Structure, Pattern Analysis, Intelligence Context e Market Hypothesis.
- O Intelligence Benchmark registra tempo, memória, quantidade de hipóteses, análises, entidades e status.
- A Milestone-014 Strategy Readiness Foundation cria a infraestrutura de preparação para Strategy sem tomada de decisão, execução ou automação.
- O Signal Foundation representa sinais estruturais derivados de Pattern Analysis e Intelligence Snapshot.
- O Signal Registry e o Signal Scoring Foundation registram e pontuam sinais com regras fixas.
- O Strategy Readiness Snapshot consolida Pattern Analysis, Intelligence Snapshot, Market Hypothesis, Signals e Scores.
- O Strategy Readiness Benchmark registra tempo, memória, quantidade de sinais, hipóteses, análises e status.
- A primeira execução local no Windows 10 do ambiente do Codex foi validada.
- O workspace oficial no Windows 10 do Leo foi preparado em `C:\Users\Leo\Documents\GitHub\predixai-platform`.
- `scripts\setup_windows.bat` e `scripts\run_predixai.bat` usam a raiz do repositório e recusam `C:\Windows\System32`.
- O guia para Leo executar a validação real está em `docs/setup/Leo_Windows10_Validation.md`.
- A próxima tarefa será definida pelo Leo em PTP-048.
