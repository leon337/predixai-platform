# PROTOCOLO OFICIAL DE CHAT — PREDIXAI BR

## 1. Escopo

Cada chat deve focar uma PTP/letra principal e suas mini-PTPs internas.

Se o contexto ficar alto, gerar checkpoint e continuar em novo chat dentro da mesma PTP/letra.

## 2. Início

Comando:

    iniciar

O assistente deve:

1. Ler checkpoint.
2. Considerar fontes do projeto no ChatGPT.
3. Confirmar PTP/letra atual.
4. Mostrar roadmap visual.
5. Indicar etapa anterior, etapa atual e próxima ação.
6. Preparar auditoria do repositório real.
7. Não gerar script sem debate e aprovação.

## 3. Fechamento

Comandos:

    fechar
    checkpoint

O assistente deve gerar checkpoint histórico completo com:

- título sugerido do chat;
- objetivo;
- PTP/letra;
- mini-PTPs;
- roadmap visual;
- scripts;
- relatórios;
- Markdown;
- commits;
- pushes;
- problemas;
- decisões;
- pendências;
- próxima ação;
- estado do GitHub;
- instrução de retomada.

## 4. Saúde

Comando:

    saúde

Responder com:

- uso estimado;
- semáforo;
- índice do chat;
- PTP atual;
- decisões;
- scripts;
- relatórios;
- commits/pushes;
- pendências;
- risco;
- ação sugerida.

## 5. Não assumir execução

Sem relatório, print ou confirmação:

    ⏳ AGUARDANDO EXECUÇÃO DO LEO
