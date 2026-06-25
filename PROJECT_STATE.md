# PredixAI BR — Estado Oficial do Projeto

## Projeto

PredixAI Platform

Primeiro produto: PredixAI Trader.

## Fase atual

Fase 2 — Vision.

A Fase 0 foi concluída, a Fase 1 foi criada e validada, e a base atual já possui Perception Engine foundation, Capture Engine foundation, captura manual, Vision Engine foundation, ROI foundation, Image Loader foundation, ROI Crop foundation, ROI Crop Image Export, OCR foundation, OCR Provider Adapter foundation, OCR Pipeline Validation foundation, primeira execução local validada no Windows 10 do ambiente do Codex e workspace oficial preparado no Windows 10 do Leo.

## Último PTP aprovado

PTP-017 — OCR Pipeline Validation Foundation.

## Próximo PTP pendente

PTP-018 — A definir pelo Leo.

## Status geral

V1 congelada.

A plataforma executa localmente no Windows 10 do ambiente do Codex e no workspace oficial do Windows 10 do Leo, inicializa Core, Perception, Capture Engine e Vision Engine foundation, realiza captura manual em PNG quando solicitada por linha de comando, registra metadados técnicos do frame, carrega bytes do PNG em memória como metadados de `ImageBuffer`, registra a ROI padrão `FULL_SCREEN`, cria metadados de `ROICrop` após validação matemática da ROI, exporta a ROI `FULL_SCREEN` em PNG para `captures/rois` e valida o pipeline OCR completo com provider `mock` sem extrair texto.

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
- A primeira execução local no Windows 10 do ambiente do Codex foi validada.
- O workspace oficial no Windows 10 do Leo foi preparado em `C:\Users\Leo\Documents\GitHub\predixai-platform`.
- `scripts\setup_windows.bat` e `scripts\run_predixai.bat` usam a raiz do repositório e recusam `C:\Windows\System32`.
- O guia para Leo executar a validação real está em `docs/setup/Leo_Windows10_Validation.md`.
- A próxima tarefa será definida pelo Leo em PTP sequencial.
