# PredixAI BR — Validação Real no Windows 10 do Leo

Este guia deve ser executado no computador Windows 10 do Leo.

Objetivo: confirmar que a PredixAI roda fora do ambiente do Codex e que a captura manual gera um arquivo PNG em `captures`.

## 1. Atualizar ou clonar o repositório

Se o repositório já existir no computador:

```bat
cd caminho\para\predixai-platform
git pull origin main
```

Se o repositório ainda não existir:

```bat
git clone https://github.com/leon337/predixai-platform.git
cd predixai-platform
```

## 2. Preparar o ambiente

Na raiz do repositório:

```bat
scripts\setup_windows.bat
```

O setup deve terminar com:

```text
PredixAI Windows 10 setup completed.
```

## 3. Executar a PredixAI

```bat
scripts\run_predixai.bat
```

O terminal deve mostrar:

```text
PredixAI Platform 0.1.0-foundation initialized in Observador mode.
```

## 4. Executar captura manual

```bat
scripts\run_predixai.bat --capture
```

O terminal deve mostrar um caminho parecido com:

```text
Manual capture saved: ...\captures\capture_YYYYMMDD_HHMMSS.png
```

## 5. Confirmar o PNG

Abra a pasta:

```text
captures
```

Confirme se existe um arquivo com nome semelhante a:

```text
capture_YYYYMMDD_HHMMSS.png
```

## 6. Confirmar o log

Abra:

```text
logs\predixai.log
```

Procure linhas com:

```text
Início da sessão de captura
Horário da captura
Resolução da captura
Arquivo da captura
Tamanho do arquivo
```

## 7. Resultado esperado

- Setup concluído.
- Core inicializado.
- Perception inicializado.
- Capture Engine inicializado.
- Captura manual executada.
- PNG criado em `captures`.
- Log registrado em `logs\predixai.log`.

## 8. Se falhar

Registre:

- comando executado;
- mensagem completa do erro;
- versão do Python com `python --version`;
- se a pasta `captures` existe;
- se o arquivo `logs\predixai.log` foi criado.

Não altere código durante esta validação.
