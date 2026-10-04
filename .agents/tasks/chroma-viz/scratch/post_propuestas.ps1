# DEMO / THROWAWAY -- POST de los 21 instrumentos a /vectorizacion/propuestas
# (Momento 1: asociación de KPIs). Sin header Authorization (AUTH_DEV_MODE=true).
# Usa curl.exe (no el alias PS). inst_NN -> id_instrumento = N (ver id_map.json).
$ErrorActionPreference = 'Stop'
$base = 'http://localhost:8002/vectorizacion/propuestas'
$repo = 'c:\Users\yarel\Documents\indagata\indagata'
$ok = 0; $fail = 0; $results = @()

for ($n = 1; $n -le 21; $n++) {
    $nn   = '{0:D2}' -f $n
    $json = Join-Path $repo "storage\raw\inst_$nn.v1.json"
    $md   = Join-Path $repo "storage\raw\inst_$nn.md"
    $id   = $n   # mapeo 1:1 inst_NN -> id_instrumento

    $code = & curl.exe -s -o NUL -w "%{http_code}" -X POST $base `
        -F "archivo_json=@$json;type=application/json" `
        -F "instrumento_original=@$md;type=text/markdown" `
        -F "tipo_instrumento=encuesta" `
        -F "id_instrumento=$id"

    if ($code -eq '200') { $ok++ } else { $fail++ }
    $line = "inst_$nn (id=$id) -> HTTP $code"
    $results += $line
    Write-Host $line
}

Write-Host ""
Write-Host "RESUMEN: $ok OK / $fail fallos de 21"
$results | Set-Content -Path (Join-Path $repo ".agents\tasks\chroma-viz\scratch\post_propuestas_result.txt")
