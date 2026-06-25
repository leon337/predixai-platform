# PredixAI BR — Setup Local no Windows 10

Este guia prepara a primeira execução local da PredixAI BR no Windows 10.

O objetivo e validar que a fundacao tecnica criada ate o PTP-006 executa corretamente fora do ambiente do Codex. Este setup nao implementa OCR, IA, Strategy, Dashboard, Broker Adapter, Auditor, automacao ou interacao com corretora.

## Requisitos

- Windows 10.
- Python 3.11 ou superior.
- Git instalado.
- Terminal aberto na raiz do repositorio `predixai-platform`.

## Instalar

Na raiz do repositorio, execute:

```bat
scripts\setup_windows.bat
```

O script verifica:

- Python disponivel.
- Versao minima do Python.
- Ambiente virtual `.venv`.
- `pip`.
- `requirements.txt`.
- Diretorios obrigatorios: `config`, `data`, `logs`, `captures`, `assets` e `tests`.
- Compilacao dos pacotes Python.
- Bootstrap da aplicacao.

O projeto ainda usa apenas biblioteca padrao do Python. Por isso, `requirements.txt` nao instala dependencias externas nesta etapa.

## Executar

Para inicializar Core, Perception e Capture Engine:

```bat
scripts\run_predixai.bat
```

Com Python diretamente:

```bat
python -m predixai.main
```

## Captura Manual

Para executar uma captura manual de tela:

```bat
scripts\run_predixai.bat --capture
```

Com Python diretamente:

```bat
python -m predixai.main --capture
```

A imagem PNG sera salva em:

```text
captures\capture_YYYYMMDD_HHMMSS.png
```

Os logs tecnicos ficam em:

```text
logs\predixai.log
```

## Atualizar

Para atualizar uma instalacao local:

```bat
git pull origin main
scripts\setup_windows.bat
```

Se o ambiente virtual precisar ser recriado, remova `.venv` e execute o setup novamente:

```bat
rmdir /s /q .venv
scripts\setup_windows.bat
```

## Checklist de Primeira Execucao Local

- [x] Python 3.11+ verificado.
- [x] Ambiente virtual preparado.
- [x] Dependencias verificadas.
- [x] Estrutura do projeto validada.
- [x] Diretorios obrigatorios validados.
- [x] Permissao de escrita em `logs` validada.
- [x] Permissao de escrita em `captures` validada.
- [x] Core inicializado.
- [x] Perception inicializado.
- [x] Capture Engine inicializado.
- [x] Captura manual em PNG validada.

## Resultado da Validacao PTP-007

Ambiente validado:

- Sistema operacional: Windows 10.
- Python: 3.12.10.
- Core: executado com sucesso.
- Perception: executado com sucesso.
- Capture Engine: executado com sucesso.
- Captura manual: executada com sucesso.

Problema encontrado:

- `where python` pode nao localizar o Python em alguns ambientes Windows, mesmo quando `python --version` funciona.
- O ambiente sem permissao de sessao grafica completa pode bloquear a captura de tela. A execucao local normal do Windows 10 permitiu a captura corretamente.

Problema corrigido:

- Criados scripts de apoio para padronizar setup, ambiente virtual e inicializacao local.
- O script de setup passou a validar `python` e `py -3` executando os comandos diretamente.

## Proximos Ajustes Antes do Linux Mint

- Criar um backend de captura compativel com Linux Mint.
- Documentar dependencias graficas do Linux, como servidor X11 ou Wayland.
- Definir comportamento quando a sessao grafica nao permitir captura.
- Validar caminhos e permissoes em filesystem Linux.
