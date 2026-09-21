# Script para testing A/B de modelos Ollama
# Uso: .\test_modelos.ps1

# Texto de prueba (fragmento corto de encuesta)
$prompt = @"
Analiza este fragmento de encuesta educativa:

SECCION 1: DATOS DEMOGRAFICOS
1. Edad: ____
2. Genero: M / F / Otro
3. Nivel educativo: Primaria / Secundaria / Bachillerato

SECCION 2: SATISFACCION DOCENTE
4. ¿Te sientes satisfecho con tu trabajo?
   1=Muy insatisfecho  2=Insatisfecho  3=Neutral  4=Satisfecho  5=Muy satisfecho

5. ¿Cuantos años llevas enseñando?
   Respuesta abierta: _____

6. ¿Recomendarias esta profesion?
   Si / No / Tal vez

Genera 3 propuestas de mejora en formato JSON.
"@

# Modelos a probar
$modelos = @(
    "llama3.2:3b",           # Modelo base sin personalizacion
    "indagata-analyzer",      # Modelo balanceado (si existe)
    "indagata-conservative",  # Modelo conservador (si existe)
    "indagata-creative"       # Modelo creativo (si existe)
)

Write-Host "`n===== TESTING DE MODELOS OLLAMA =====" -ForegroundColor Cyan
Write-Host "Prompt de prueba:" -ForegroundColor Yellow
Write-Host $prompt -ForegroundColor Gray
Write-Host "`n" -ForegroundColor White

foreach ($modelo in $modelos) {
    # Verificar si el modelo existe
    $existe = ollama list | Select-String $modelo
    
    if (!$existe) {
        Write-Host "[SKIP] Modelo '$modelo' no encontrado" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "MODELO: $modelo" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    
    # Medir tiempo de respuesta
    $inicio = Get-Date
    
    # Ejecutar modelo
    $respuesta = $prompt | ollama run $modelo
    
    $fin = Get-Date
    $duracion = ($fin - $inicio).TotalSeconds
    
    # Mostrar resultados
    Write-Host "`nRESPUESTA:" -ForegroundColor Yellow
    Write-Host $respuesta -ForegroundColor White
    
    Write-Host "`nTIEMPO: $([math]::Round($duracion, 2)) segundos" -ForegroundColor Magenta
    Write-Host "`n" -ForegroundColor White
    
    # Pausa entre modelos
    Start-Sleep -Seconds 2
}

Write-Host "`n===== FIN DEL TESTING =====" -ForegroundColor Cyan
Write-Host "`nCompara las respuestas y selecciona el modelo que genere" -ForegroundColor Yellow
Write-Host "propuestas mas utiles para tu caso de uso." -ForegroundColor Yellow
