# Script para crear modelo personalizado de Ollama
# Uso: .\crear_modelo_ollama.ps1

Write-Host "[INFO] Creando modelo personalizado INDAGATA..." -ForegroundColor Cyan

# Verificar que Ollama este instalado
if (!(Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Ollama no esta instalado o no esta en PATH" -ForegroundColor Red
    Write-Host "        Instalar desde: https://ollama.ai/download" -ForegroundColor Yellow
    exit 1
}

# Verificar que el modelo base este descargado
Write-Host "[INFO] Verificando modelo base llama3.2:3b..." -ForegroundColor Yellow
$modeloBase = ollama list | Select-String "llama3.2:3b"

if (!$modeloBase) {
    Write-Host "[INFO] Descargando modelo base llama3.2:3b (puede tardar varios minutos)..." -ForegroundColor Yellow
    ollama pull llama3.2:3b
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo al descargar modelo base" -ForegroundColor Red
        exit 1
    }
}

# Crear modelo personalizado
Write-Host "[INFO] Creando modelo indagata-analyzer..." -ForegroundColor Yellow
ollama create indagata-analyzer -f Modelfile

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Modelo 'indagata-analyzer' creado exitosamente" -ForegroundColor Green
    
    Write-Host "`n[SIGUIENTE] Para usar este modelo:" -ForegroundColor Cyan
    Write-Host "  1. Actualiza tu .env:" -ForegroundColor White
    Write-Host "     OLLAMA_MODEL=indagata-analyzer" -ForegroundColor Gray
    Write-Host "`n  2. Reinicia FastAPI" -ForegroundColor White
    Write-Host "     uvicorn main:app --reload" -ForegroundColor Gray
    
    Write-Host "`n[TEST] Probar modelo en consola:" -ForegroundColor Cyan
    Write-Host "  ollama run indagata-analyzer" -ForegroundColor Gray
    
    Write-Host "`n[CLEANUP] Para eliminar modelo:" -ForegroundColor Cyan
    Write-Host "  ollama rm indagata-analyzer" -ForegroundColor Gray
    
} else {
    Write-Host "[ERROR] Fallo al crear modelo" -ForegroundColor Red
    Write-Host "Verifica que el Modelfile este en el directorio actual" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[INFO] Modelos disponibles:" -ForegroundColor Cyan
ollama list
