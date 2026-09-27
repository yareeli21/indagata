# Testing de modelos Ollama

## Crear modelo personalizado

```powershell
# 1. Crear modelo
.\crear_modelo_ollama.ps1

# 2. Actualizar .env
# OLLAMA_MODEL=indagata-analyzer

# 3. Reiniciar backend
uvicorn main:app --reload
```

---

## Testing A/B de parametros

### **Crear variantes:**

**Modelo conservador (mas preciso, menos creativo):**

```modelfile
# Modelfile.conservative
FROM llama3.2:3b
PARAMETER temperature 0.3
PARAMETER top_p 0.7
PARAMETER num_ctx 8192
SYSTEM """..."""
```

```powershell
ollama create indagata-conservative -f Modelfile.conservative
```

**Modelo creativo (mas variedad, menos preciso):**

```modelfile
# Modelfile.creative
FROM llama3.2:3b
PARAMETER temperature 0.9
PARAMETER top_p 0.95
PARAMETER num_ctx 8192
SYSTEM """..."""
```

```powershell
ollama create indagata-creative -f Modelfile.creative
```

**Modelo balanceado (default):**

```modelfile
# Modelfile (ya existe)
FROM llama3.2:3b
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
SYSTEM """..."""
```

```powershell
ollama create indagata-analyzer -f Modelfile
```

### **Probar en consola:**

```powershell
# Conservador
ollama run indagata-conservative "Analiza esta encuesta: [texto]"

# Creativo
ollama run indagata-creative "Analiza esta encuesta: [texto]"

# Balanceado
ollama run indagata-analyzer "Analiza esta encuesta: [texto]"
```

### **Probar con el endpoint:**

```powershell
# 1. Cambiar en .env
OLLAMA_MODEL=indagata-conservative

# 2. Reiniciar backend
uvicorn main:app --reload

# 3. Probar endpoint
# GET /instrumentos/1/etl/extract

# 4. Comparar propuestas generadas
```

---

## Parametros explicados

| Parametro | Valor bajo | Valor alto | Recomendado |
|-----------|-----------|-----------|-------------|
| **temperature** | 0.1-0.3 (preciso) | 0.8-1.0 (creativo) | 0.7 |
| **top_p** | 0.5-0.7 (conservador) | 0.9-1.0 (diverso) | 0.9 |
| **num_ctx** | 2048 (rapido) | 32768 (completo) | 8192 |
| **repeat_penalty** | 1.0 (sin penalizacion) | 2.0 (evita repetir) | 1.1 |

---

## Listar y eliminar modelos

```powershell
# Ver modelos instalados
ollama list

# Eliminar modelo
ollama rm indagata-analyzer
ollama rm indagata-conservative
ollama rm indagata-creative

# Descargar otros modelos base
ollama pull qwen2.5:latest      # Modelo chino, muy bueno
ollama pull mistral:latest       # Modelo frances, rapido
ollama pull phi3:latest          # Modelo Microsoft, pequeno
```

---

## Cambiar modelo base

Para usar un modelo diferente en lugar de llama3.2:3b:

```modelfile
# Modelfile con Qwen2.5
FROM qwen2.5:latest
PARAMETER temperature 0.7
# ... resto igual
```

```powershell
ollama create indagata-qwen -f Modelfile.qwen
```

Actualizar `.env`:
```ini
OLLAMA_MODEL=indagata-qwen
```

---

## Recomendaciones

1. **Empezar con el modelo balanceado** (indagata-analyzer)
2. Si las propuestas son muy "locas", usar modelo conservador
3. Si las propuestas son muy repetitivas, usar modelo creativo
4. Para produccion, testear con 10-20 instrumentos diferentes
5. Documentar cual modelo dio mejores resultados
