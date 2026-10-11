# ============================================================================
#  Indagata — Arranque limpio del entorno (Windows / PowerShell)
# ============================================================================
#  Levanta TODO el sistema desde cero: recrea los volumenes (aplica el esquema
#  nuevo con las tablas kpi_calculo y grafo_investigacion), reconstruye las
#  imagenes con el codigo actual de la rama, siembra los datos y reindexa.
#
#  USO:
#     .\arrancar.ps1              # arranque completo (down -v + build + up + seed + reindex)
#     .\arrancar.ps1 -SinBorrar   # NO borra volumenes (conserva la BD actual); solo rebuild+up
#
#  Requisitos: Docker Desktop abierto. El modelo de Ollama (llama3.2:3b) se
#  descarga una sola vez y sobrevive salvo que borres el volumen ollama_data.
# ============================================================================

param(
    [switch]$SinBorrar  # si se pasa, conserva los volumenes (no recrea la BD)
)

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz

function Paso($n, $txt) { Write-Host "`n=== [$n] $txt ===" -ForegroundColor Cyan }

# ---------------------------------------------------------------------------
Paso 1 "Verificando que Docker este corriendo"
try { docker info *> $null } catch {
    Write-Host "ERROR: Docker no responde. Abre Docker Desktop y espera 'Engine running'." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
if (-not $SinBorrar) {
    Paso 2 "Bajando el stack y BORRANDO volumenes (BD + Chroma se recrean)"
    Write-Host "   (Postgres y Chroma quedaran vacios; se vuelven a sembrar mas abajo)" -ForegroundColor Yellow
    docker compose -p indagata down -v
} else {
    Paso 2 "Bajando el stack (CONSERVANDO volumenes: la BD actual se mantiene)"
    docker compose -p indagata down
}

# ---------------------------------------------------------------------------
Paso 3 "Reconstruyendo imagenes con el codigo actual (analysis-service, etc.)"
docker compose -p indagata build analysis-service visualization-service api-gateway instrument-service metadata-service storage-service

# ---------------------------------------------------------------------------
Paso 4 "Levantando infraestructura y microservicios"
docker compose -p indagata up -d postgres redis ollama chromadb api-gateway instrument-service analysis-service metadata-service storage-service visualization-service

# ---------------------------------------------------------------------------
Paso 5 "Esperando a que los servicios respondan (health)"
$puertos = @{ "api-gateway" = 8000; "instrument" = 8001; "analysis" = 8002; "metadata" = 8003; "storage" = 8004; "visualization" = 8005 }
$maxIntentos = 30
foreach ($svc in $puertos.Keys) {
    $p = $puertos[$svc]
    $ok = $false
    for ($i = 0; $i -lt $maxIntentos; $i++) {
        try {
            $r = Invoke-RestMethod -Uri "http://localhost:$p/health" -TimeoutSec 3
            Write-Host "   OK  $svc (:$p)" -ForegroundColor Green
            $ok = $true; break
        } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ok) { Write-Host "   !! $svc (:$p) no respondio tras $($maxIntentos*2)s" -ForegroundColor Yellow }
}

# ---------------------------------------------------------------------------
Paso 6 "Verificando el modelo de Ollama (llama3.2:3b)"
$modelos = docker exec indagata_ollama ollama list 2>$null
if ($modelos -match "llama3.2:3b") {
    Write-Host "   OK  llama3.2:3b ya esta descargado" -ForegroundColor Green
} else {
    Write-Host "   Descargando llama3.2:3b (~2 GB, una sola vez)..." -ForegroundColor Yellow
    docker exec indagata_ollama ollama pull llama3.2:3b
}

# ---------------------------------------------------------------------------
if (-not $SinBorrar) {
    Paso 7 "Sembrando los 55 KPIs reales desde el CSV"
    docker compose -p indagata exec analysis-service python scripts/seed_kpis.py

    Paso 8 "Reindexando la coleccion vectorial de KPIs en ChromaDB"
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:8002/vectorizacion/kpis/reindex" -Method Post -TimeoutSec 120
        Write-Host "   OK  reindex: $($r.n_kpis) KPIs en la coleccion '$($r.coleccion)'" -ForegroundColor Green
    } catch {
        Write-Host "   !! El reindex fallo: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "      Reintenta manual: Invoke-RestMethod http://localhost:8002/vectorizacion/kpis/reindex -Method Post" -ForegroundColor Yellow
    }
} else {
    Paso 7 "Omitido el seed/reindex (-SinBorrar): la BD y Chroma se conservan como estaban"
}

# ---------------------------------------------------------------------------
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " LISTO. El backend esta arriba." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host " Usuarios sembrados:" -ForegroundColor Cyan
Write-Host "   admin         admin@indagata.com         / admin123"
Write-Host "   investigador  investigador@indagata.com  / investigador123"
Write-Host ""
Write-Host " Ahora levanta el FRONTEND en otra terminal:" -ForegroundColor Cyan
Write-Host "   cd pixel-perfect-pixel"
Write-Host "   bun run dev"
Write-Host ""
Write-Host " Luego abre la URL que muestre Vite (normalmente http://localhost:3000)." -ForegroundColor Cyan
Write-Host ""
