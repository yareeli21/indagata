# Script para limpiar archivos de cache antiguos en storage/data
# Ejecutar como tarea programada (cron job) diariamente
# Uso: .\limpiar_cache_antiguedad.ps1

param(
    [int]$DiasRetencion = 90  # Por defecto 90 dias (3 meses)
)

Write-Host "Limpieza de cache antiguo en storage/data" -ForegroundColor Cyan
Write-Host "Retencion configurada: $DiasRetencion dias`n" -ForegroundColor Yellow

$dataPath = "storage\data"

if (!(Test-Path $dataPath)) {
    Write-Host "ADVERTENCIA: No existe el directorio $dataPath" -ForegroundColor Yellow
    exit 0
}

$fechaLimite = (Get-Date).AddDays(-$DiasRetencion)
$archivos = Get-ChildItem -Path $dataPath -Filter "*.txt" -File

if ($archivos.Count -eq 0) {
    Write-Host "No hay archivos .txt en $dataPath" -ForegroundColor Gray
    exit 0
}

Write-Host "Total archivos en cache: $($archivos.Count)" -ForegroundColor White

$eliminados = 0
$conservados = 0
$espacioLiberado = 0

foreach ($archivo in $archivos) {
    if ($archivo.LastWriteTime -lt $fechaLimite) {
        $tamano = $archivo.Length
        $espacioLiberado += $tamano
        
        Write-Host "  [ELIMINAR] $($archivo.Name) - Modificado: $($archivo.LastWriteTime.ToString('yyyy-MM-dd'))" -ForegroundColor Red
        Remove-Item $archivo.FullName -Force
        $eliminados++
    }
    else {
        $conservados++
        Write-Host "  [CONSERVAR] $($archivo.Name) - Modificado: $($archivo.LastWriteTime.ToString('yyyy-MM-dd'))" -ForegroundColor Green
    }
}

Write-Host "`nResumen:" -ForegroundColor Cyan
Write-Host "  Archivos eliminados: $eliminados" -ForegroundColor Red
Write-Host "  Archivos conservados: $conservados" -ForegroundColor Green
Write-Host "  Espacio liberado: $([math]::Round($espacioLiberado / 1MB, 2)) MB" -ForegroundColor Yellow

# Registrar en log (opcional)
$logEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Eliminados: $eliminados, Conservados: $conservados, Liberados: $([math]::Round($espacioLiberado / 1MB, 2)) MB"
Add-Content -Path "storage\data\limpieza.log" -Value $logEntry
