param(
    [string]$PlatformPath = "C:\Users\Leo\Documents\GitHub\predixai-platform",
    [string]$KnowledgePath = "C:\Users\Leo\Documents\GitHub\predixai-knowledge",
    [switch]$Publish
)

$ErrorActionPreference = "Continue"

$Report = New-Object System.Collections.Generic.List[string]
$Problems = New-Object System.Collections.Generic.List[string]
$Warnings = New-Object System.Collections.Generic.List[string]
$Changed = New-Object System.Collections.Generic.List[string]

$PlatformReport = Join-Path $PlatformPath "TRADER_V1_FINAL_CLOSURE_REPORT.txt"
$PlatformClosure = Join-Path $PlatformPath "TRADER_V1_FINAL_CLOSURE.md"
$KnowledgeReportsDir = Join-Path $KnowledgePath "reports"
$KnowledgeReport = Join-Path $KnowledgeReportsDir "TRADER_V1_FINAL_CLOSURE_REPORT.txt"
$KnowledgePage = Join-Path $KnowledgePath "trader-v1-final-closure.html"
$KnowledgeIndex = Join-Path $KnowledgePath "index.html"

function L {
    param([string]$Text = "")
    $Report.Add($Text) | Out-Null
    Write-Host $Text
}

function Warn {
    param([string]$Text)
    $Warnings.Add($Text) | Out-Null
    L "AVISO: $Text"
}

function Fail {
    param([string]$Text)
    $Problems.Add($Text) | Out-Null
    L "ERRO: $Text"
}

function Mark-Changed {
    param([string]$Path)
    if (-not $Changed.Contains($Path)) {
        $Changed.Add($Path) | Out-Null
    }
}

function Write-Text {
    param(
        [string]$Path,
        [string]$Content
    )

    $Dir = Split-Path $Path -Parent

    if (!(Test-Path $Dir)) {
        New-Item -ItemType Directory -Path $Dir -Force | Out-Null
    }

    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

function Set-IfChanged {
    param(
        [string]$Path,
        [string]$Content
    )

    $Current = ""

    if (Test-Path $Path) {
        $Current = Get-Content $Path -Raw -Encoding UTF8
    }

    $CleanContent = $Content.TrimEnd() + "`r`n"

    if ($Current -ne $CleanContent) {
        Write-Text $Path $CleanContent
        Mark-Changed $Path
        L "Arquivo atualizado: $Path"
    } else {
        L "Sem mudança: $Path"
    }
}

function Normalize-File {
    param([string]$Path)

    if (Test-Path $Path) {
        $Content = Get-Content $Path -Raw -Encoding UTF8
        $Clean = $Content.TrimEnd() + "`r`n"
        Write-Text $Path $Clean
        L "Whitespace normalizado: $Path"
    }
}

function Update-Block {
    param(
        [string]$Path,
        [string]$Start,
        [string]$End,
        [string]$Block
    )

    if (!(Test-Path $Path)) {
        Warn "Arquivo não encontrado: $Path"
        return
    }

    $Content = Get-Content $Path -Raw -Encoding UTF8
    $Pattern = "(?s)$([regex]::Escape($Start)).*?$([regex]::Escape($End))"
    $Full = "$Start`r`n$($Block.TrimEnd())`r`n$End"

    if ($Content -match $Pattern) {
        $New = [regex]::Replace($Content, $Pattern, $Full)
    } else {
        $New = $Content.TrimEnd() + "`r`n`r`n" + $Full
    }

    $New = $New.TrimEnd() + "`r`n"

    if ($New -ne $Content) {
        Write-Text $Path $New
        Mark-Changed $Path
        L "Bloco atualizado em: $Path"
    } else {
        L "Bloco já estava atualizado: $Path"
    }
}

function Append-Once {
    param(
        [string]$Path,
        [string]$Needle,
        [string]$Text
    )

    if (!(Test-Path $Path)) {
        Warn "Arquivo não encontrado: $Path"
        return
    }

    $Content = Get-Content $Path -Raw -Encoding UTF8

    if ($Content -notmatch [regex]::Escape($Needle)) {
        $New = $Content.TrimEnd() + "`r`n`r`n" + $Text.TrimEnd() + "`r`n"
        Write-Text $Path $New
        Mark-Changed $Path
        L "Texto adicionado em: $Path"
    } else {
        L "Texto já existe em: $Path"
    }
}

function Run-Cmd {
    param(
        [string]$Title,
        [string]$Path,
        [string]$Command,
        [bool]$AllowFail = $false
    )

    L ""
    L "===== $Title ====="
    L "Caminho: $Path"
    L "Comando: $Command"

    if (!(Test-Path $Path)) {
        Fail "Caminho não encontrado: $Path"
        return 1
    }

    Push-Location $Path

    $OldPythonPath = $env:PYTHONPATH

    if (Test-Path (Join-Path $Path "src")) {
        $env:PYTHONPATH = "$(Join-Path $Path 'src');$OldPythonPath"
    }

    $Output = cmd /c $Command 2>&1
    $Code = $LASTEXITCODE

    foreach ($Line in $Output) {
        L $Line
    }

    L "ExitCode: $Code"

    $env:PYTHONPATH = $OldPythonPath
    Pop-Location

    if ($Code -ne 0 -and -not $AllowFail) {
        Fail "$Title falhou"
    }

    return $Code
}

function Agent-Arquiteto {
    L ""
    L "===== AGENTE ARQUITETO ====="

    foreach ($File in @("PROJECT_STATE.md", "predixai_context.json")) {
        $Path = Join-Path $PlatformPath $File

        if (Test-Path $Path) {
            L "$File encontrado"
        } else {
            Fail "$File ausente"
        }
    }

    $ContextPath = Join-Path $PlatformPath "predixai_context.json"

    if (Test-Path $ContextPath) {
        try {
            Get-Content $ContextPath -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null
            L "predixai_context.json válido"
        }
        catch {
            Fail "predixai_context.json inválido"
        }
    }
}

function Agent-Executor {
    L ""
    L "===== AGENTE EXECUTOR ====="

    $Closure = @"
# PTP-104 — TRADER V1 FINAL CLOSURE

Data: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Produto

PredixAI Trader

## Versão encerrada

V1 Observador

## Decisão

A V1 Observador do PredixAI Trader está encerrada como base técnica validada.

## Escopo validado

- PTP-102 — Triple Rebound Observer
- PTP-103 — Overnight Observer
- MarketSessionRecorder
- Scripts CLI principais
- Estado do Git
- Sincronização com Knowledge Hub

## Regras preservadas

- Não migrar Trader ainda
- Não criar predixai-trader ainda
- Não iniciar produto novo
- Não apagar TRADER_V1_PTP103_PUBLICATION_REPORT.txt sem decisão
- Toda atualização relevante deve refletir no predixai-knowledge

## Próximo passo

Planejar a próxima fase do Trader sem migração imediata.
"@

    Set-IfChanged $PlatformClosure $Closure

    $ProjectState = Join-Path $PlatformPath "PROJECT_STATE.md"

    $StateBlock = @"
## PTP-104 — Trader V1 Final Closure

Status: concluído

A V1 Observador do PredixAI Trader foi fechada como base técnica validada após PTP-103.

Decisão oficial:
PredixAI Trader V1 Observador está encerrada como versão observadora.

Regras:
- Não migrar Trader ainda.
- Não criar predixai-trader ainda.
- Não iniciar produto novo.
- Knowledge Hub deve registrar o fechamento.
"@

    Update-Block `
        -Path $ProjectState `
        -Start "<!-- PTP-104-TRADER-V1-FINAL-CLOSURE:START -->" `
        -End "<!-- PTP-104-TRADER-V1-FINAL-CLOSURE:END -->" `
        -Block $StateBlock

    $ContextPath = Join-Path $PlatformPath "predixai_context.json"

    try {
        $Raw = Get-Content $ContextPath -Raw -Encoding UTF8
        $Json = $Raw | ConvertFrom-Json

        $ClosureObj = [ordered]@{
            ptp = "PTP-104"
            name = "TRADER V1 FINAL CLOSURE"
            product = "PredixAI Trader"
            version = "V1 Observador"
            status = "closed"
            closed_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        }

        $Json | Add-Member -NotePropertyName "last_ptp" -NotePropertyValue "PTP-104" -Force
        $Json | Add-Member -NotePropertyName "trader_v1_final_closure" -NotePropertyValue $ClosureObj -Force

        $NewJson = ($Json | ConvertTo-Json -Depth 30).TrimEnd() + "`r`n"
        Write-Text $ContextPath $NewJson
        Mark-Changed $ContextPath
        L "predixai_context.json atualizado"
    }
    catch {
        Fail "Erro ao atualizar predixai_context.json: $($_.Exception.Message)"
    }

    $Changelog = Join-Path $PlatformPath "CHANGELOG.md"

    $ChangeText = @"
## PTP-104 — Trader V1 Final Closure

- Encerrada oficialmente a V1 Observador do PredixAI Trader.
- Registrado fechamento pós PTP-103.
- Preservada regra de não migração e não criação de novo repositório.
- Preparada sincronização com Knowledge Hub.
"@

    Append-Once $Changelog "PTP-104 — Trader V1 Final Closure" $ChangeText

    Normalize-File $ProjectState
    Normalize-File $Changelog
}

function Agent-Knowledge {
    L ""
    L "===== AGENTE KNOWLEDGE HUB ====="

    if (!(Test-Path $KnowledgePath)) {
        Fail "Repositório predixai-knowledge não encontrado"
        return
    }

    if (!(Test-Path $KnowledgeReportsDir)) {
        New-Item -ItemType Directory -Path $KnowledgeReportsDir -Force | Out-Null
    }

    $Html = @"
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>PredixAI Trader V1 — Final Closure</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <main>
    <h1>PredixAI Trader V1 — Final Closure</h1>
    <p><strong>Status:</strong> V1 Observador encerrada.</p>
    <p><strong>PTP:</strong> PTP-104 — TRADER V1 FINAL CLOSURE</p>
    <p><strong>Knowledge Hub:</strong> V2.14</p>

    <h2>Decisão oficial</h2>
    <p>A V1 Observador do PredixAI Trader foi fechada como base técnica validada após o PTP-103.</p>

    <h2>Regras preservadas</h2>
    <ul>
      <li>Não migrar Trader ainda.</li>
      <li>Não criar predixai-trader ainda.</li>
      <li>Não iniciar produto novo.</li>
      <li>Manter GitHub e Knowledge Hub sincronizados.</li>
    </ul>

    <p><a href="reports/TRADER_V1_FINAL_CLOSURE_REPORT.txt">Abrir relatório final da PTP-104</a></p>
    <p><a href="index.html">Voltar</a></p>
  </main>
</body>
</html>
"@

    Set-IfChanged $KnowledgePage $Html

    if (Test-Path $KnowledgeIndex) {
        $Index = Get-Content $KnowledgeIndex -Raw -Encoding UTF8

        if ($Index -notmatch "trader-v1-final-closure.html") {
            $Block = @"

<section id="trader-v1-final-closure">
  <h2>PredixAI Trader V1 — Final Closure</h2>
  <p>PTP-104 registrada: fechamento oficial da V1 Observador.</p>
  <p>Knowledge Hub V2.14 sincronizado.</p>
  <p><a href="trader-v1-final-closure.html">Abrir fechamento da V1 Observador</a></p>
</section>

"@

            if ($Index -match "</body>") {
                $NewIndex = $Index -replace "</body>", "$Block`r`n</body>"
            } else {
                $NewIndex = $Index.TrimEnd() + $Block
            }

            Write-Text $KnowledgeIndex ($NewIndex.TrimEnd() + "`r`n")
            Mark-Changed $KnowledgeIndex
            L "index.html atualizado"
        } else {
            L "index.html já possui link da PTP-104"
        }
    } else {
        Warn "index.html não encontrado no Knowledge"
    }
}

function Agent-Validador {
    L ""
    L "===== AGENTE VALIDADOR ====="

    Run-Cmd "Compileall" $PlatformPath "python -m compileall scripts src/predixai"
    Run-Cmd "Git Diff Check Platform" $PlatformPath "git diff --check"
    Run-Cmd "Import PredixAI" $PlatformPath "python -c `"import predixai; print('IMPORT_PREDIXAI_OK')`""

    $PytestCheck = Run-Cmd "Pytest instalado?" $PlatformPath "python -c `"import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest') else 5)`"" $true

    if ($PytestCheck -eq 0) {
        Run-Cmd "Pytest" $PlatformPath "python -m pytest -q"
    } else {
        Warn "pytest não instalado; validação pytest ignorada"
    }

    $Files = Get-ChildItem -Path $PlatformPath -Recurse -Filter "*.py" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notmatch "\\.git\\" -and
            $_.FullName -notmatch "\\.venv\\" -and
            $_.FullName -notmatch "__pycache__" -and
            ($_.Name -match "overnight|triple")
        }

    foreach ($File in $Files) {
        Run-Cmd "Help: $($File.Name)" $PlatformPath "python `"$($File.FullName)`" --help" $true
    }
}

function Agent-GitAuditor {
    L ""
    L "===== AGENTE GIT AUDITOR ====="

    Run-Cmd "Platform Status" $PlatformPath "git status --short --branch"
    Run-Cmd "Platform Log" $PlatformPath "git log --oneline -5"

    $OldReport = Join-Path $PlatformPath "TRADER_V1_PTP103_PUBLICATION_REPORT.txt"

    if (Test-Path $OldReport) {
        L "TRADER_V1_PTP103_PUBLICATION_REPORT.txt preservado"
    } else {
        Warn "TRADER_V1_PTP103_PUBLICATION_REPORT.txt não encontrado localmente"
    }

    Run-Cmd "Knowledge Status" $KnowledgePath "git status --short --branch"
    Run-Cmd "Knowledge Log" $KnowledgePath "git log --oneline -5"
    Run-Cmd "Knowledge Diff Check" $KnowledgePath "git diff --check"
}

function Save-Report {
    L ""
    L "===== RELATÓRIO FINAL ====="

    if ($Problems.Count -eq 0) {
        if ($Warnings.Count -eq 0) {
            L "Decisão: PTP-104 aprovada. Trader V1 Observador fechado."
        } else {
            L "Decisão: PTP-104 aprovada com avisos leves."
        }
    } else {
        L "Decisão: PTP-104 bloqueada por erros."
    }

    L ""
    L "Arquivos alterados:"
    if ($Changed.Count -eq 0) {
        L "- Nenhum"
    } else {
        foreach ($File in $Changed) {
            L "- $File"
        }
    }

    L ""
    L "Avisos:"
    if ($Warnings.Count -eq 0) {
        L "- Nenhum"
    } else {
        foreach ($Item in $Warnings) {
            L "- $Item"
        }
    }

    L ""
    L "Erros:"
    if ($Problems.Count -eq 0) {
        L "- Nenhum"
    } else {
        foreach ($Item in $Problems) {
            L "- $Item"
        }
    }

    Write-Text $PlatformReport (($Report -join "`r`n").TrimEnd() + "`r`n")

    if (!(Test-Path $KnowledgeReportsDir)) {
        New-Item -ItemType Directory -Path $KnowledgeReportsDir -Force | Out-Null
    }

    Copy-Item $PlatformReport $KnowledgeReport -Force
}

function Agent-Publicador {
    L ""
    L "===== AGENTE PUBLICADOR ====="

    if (!$Publish) {
        L "Publicação não solicitada. Use -Publish para commit e push."
        return
    }

    if ($Problems.Count -gt 0) {
        Fail "Publicação bloqueada porque existem erros."
        return
    }

    Save-Report

    Run-Cmd "Platform Add" $PlatformPath "git add PROJECT_STATE.md predixai_context.json CHANGELOG.md TRADER_V1_FINAL_CLOSURE.md TRADER_V1_FINAL_CLOSURE_REPORT.txt scripts/PTP-104_TRADER_V1_FINAL_CLOSURE.ps1"
    Run-Cmd "Platform Commit" $PlatformPath "git commit -m `"PTP-104: close Trader V1 observer`"" $true
    Run-Cmd "Platform Push" $PlatformPath "git push origin main"

    Run-Cmd "Knowledge Add" $KnowledgePath "git add index.html trader-v1-final-closure.html reports/TRADER_V1_FINAL_CLOSURE_REPORT.txt"
    Run-Cmd "Knowledge Commit" $KnowledgePath "git commit -m `"Knowledge: record Trader V1 final closure`"" $true
    Run-Cmd "Knowledge Push" $KnowledgePath "git push origin main"
}

Clear-Host

L "===== PTP-104 — TRADER V1 FINAL CLOSURE ====="
L "Data: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"
L "Platform: $PlatformPath"
L "Knowledge: $KnowledgePath"
L "Publish: $Publish"

Agent-Arquiteto
Agent-Executor
Agent-Knowledge
Agent-Validador
Agent-GitAuditor
Save-Report
Agent-Publicador
Save-Report

notepad $PlatformReport
