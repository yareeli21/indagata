# Script para limpiar archivos de instrumentos en storage/
# Mantiene la estructura de directorios pero elimina archivos

Write-Host "Limpiando archivos en storage/..." -ForegroundColor Yellow

$directorios = @(
    "storage\raw",
    "storage\json", 
    "storage\sav",
    "storage\temp",
    "storage\data"
)

foreach ($dir in $directorios) {
    if (Test-Path $dir) {
        Write-Host "Limpiando $dir..." -ForegroundColor Cyan
        Get-ChildItem -Path $dir -File | Where-Object { $_.Name -ne ".gitkeep" } | Remove-Item -Force
        $count = (Get-ChildItem -Path $dir -File | Where-Object { $_.Name -ne ".gitkeep" }).Count
        Write-Host "  Archivos restantes: $count" -ForegroundColor Green
    } else {
        Write-Host "  Directorio no existe: $dir" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Limpieza completada" -ForegroundColor Green
