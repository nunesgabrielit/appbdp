$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Resolve-BasePython {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return [pscustomobject]@{
            Exe  = $py.Source
            Args = @("-3")
        }
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return [pscustomobject]@{
            Exe  = $python.Source
            Args = @()
        }
    }
    throw "Python não encontrado. Instale o Python (ou o Python Launcher 'py') e tente novamente."
}

function Read-DotenvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string]$Key
    )

    if (!(Test-Path $FilePath)) {
        return $null
    }

    $pattern = "^\s*$([regex]::Escape($Key))\s*=\s*(.*)\s*$"
    foreach ($line in Get-Content -LiteralPath $FilePath -ErrorAction Stop) {
        if ($line -match $pattern) {
            $value = $Matches[1].Trim()
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            if ($value) {
                return $value
            }
        }
    }
    return $null
}

$basePython = Resolve-BasePython
$venvDir = Join-Path $ProjectRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (!(Test-Path $venvPython)) {
    if (Test-Path $venvDir) {
        Remove-Item -LiteralPath $venvDir -Recurse -Force
    }
    & $basePython.Exe @($basePython.Args) -m venv $venvDir
}

& $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

if (-not $env:DATABASE_URL) {
    $dotenvPath = Join-Path $ProjectRoot ".env"
    $dotenvValue = Read-DotenvValue -FilePath $dotenvPath -Key "DATABASE_URL"
    if ($dotenvValue) {
        $env:DATABASE_URL = $dotenvValue
    }
}

if (-not $env:DATABASE_URL) {
    throw "DATABASE_URL não está configurada. Defina em .env (raiz do projeto) ou como variável de ambiente."
}

& $venvPython .\start_bdp.py
