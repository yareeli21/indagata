# Limpieza medida con errores inyectados (24 oct)

Herramientas: `tools/limpieza/inyectar_errores.py` (semilla 7) y `tools/limpieza/verificar_limpieza.py`.
Diseño con grupo de control: se procesa el archivo sin cambios y el archivo con errores. Lo que se detecta de más
en el segundo se compara con lo inyectado.

Bases: `storage/instrumentos_sinteticos/encuestas/enc_11_respondido.csv` (160 respondentes, seis tipos de pregunta) y
`storage/instrumentos_sinteticos/pruebas/pru_01_respondido.csv` (100 alumnos, 25 reactivos). La verdad de cada
error está en `enc_11_verdad.json` y `pru_01_verdad.json`.

## Antes de las correcciones (instrumentos 115–118)

| Instrumento | Error | Inyectados | Detectados (VP) | Precisión | Recall |
|---|---|---|---|---|---|
| enc_11 | Duplicados | 5 | 0 | — | 0.00 |
| enc_11 | Fuera de escala | 6 | 6 | 1.00 | 1.00 |
| enc_11 | «No sé / No aplica» en escala numérica | 4 | 0 | — | 0.00 |
| enc_11 | Columna muy incompleta | 1 | 1 | 1.00 | 1.00 |
| enc_11 | Encuestados casi sin responder | 4 | 4 | 1.00 | 1.00 |
| enc_11 | Línea recta | 5 | 5 | 1.00 | 1.00 |
| enc_11 | Columnas de plataforma | 2 | 1 | 1.00 | 0.50 |
| pru_01 | Respuestas múltiples | 6 | 6 | 1.00 | 1.00 |
| pru_01 | Ilegibles | 5 | 5 | 1.00 | 1.00 |
| pru_01 | Caracteres inválidos | 4 | 4 | 1.00 | 1.00 |
| pru_01 | ID repetido | 3 | 3 | 1.00 | 1.00 |
| pru_01 | Filas vacías | 2 | 0 | — | 0.00 |

En la primera corrida, la verdad contaba 8 «no-respuestas». Cuatro eran «NA» o «N/A», que la configuración
trata como datos faltantes (`tokens_vacio`), y es correcto que se vacíen. Se corrigió la verdad a 4.

**Causas:**
1. «Dirección IP» no estaba entre los patrones de columnas ajenas. Como cada fila tenía una IP distinta y las
   columnas no ajenas cuentan para detectar duplicados, los 5 duplicados se volvieron filas únicas (falla en cascada).
2. El hallazgo «No sé / No aplica» solo se buscaba en escalas Likert de texto. En una escala 1–5, «No sé» quedaba
   en el CSV limpio mezclado con los números, sin aviso.
3. El lector de CSV compartido descartaba las filas de solo separadores (`;;;;`) antes de que la limpieza las
   contara (`any(row)` es falso cuando todas las celdas están vacías).

## Correcciones
- `services/cleaning-service/config/limpieza.yaml`: patrón de IP en español.
- `services/cleaning-service/services/motores/encuestas/motor.py`: los duplicados ignoran las columnas de valores
  únicos con forma de identificador o de fecha y hora (no las preguntas abiertas); «No sé» se trata igual en las
  escalas numéricas.
- `shared/parsing/tabular_parser.py`: se conservan las filas de solo separadores.
- Pruebas nuevas: `test_ip_en_espanol_y_columnas_de_valores_unicos_no_esconden_duplicados`,
  `test_no_se_en_una_escala_numerica_tambien_se_decide`, `test_fila_de_solo_separadores_se_cuenta_como_vacia`.

## Después de las correcciones (instrumentos 119–122)

| Instrumento | Inyectados | Detectados (VP) | Precisión | Recall |
|---|---|---|---|---|
| enc_11 | 27 | 27 | 1.00 | 1.00 |
| pru_01 | 20 | 20 | 1.00 | 1.00 |

El detalle por tipo está en `enc_11_resultado.json` y `pru_01_resultado.json`.

## Clave de respuestas propuesta contra la clave verdadera
La clave que propone la limpieza (sin archivo de clave) coincide con la verdadera del generador en **50 de 50**
reactivos de opción múltiple y verdadero/falso (pru_01 20/20, pru_02 16/16, pru_04 6/6 y pru_10 8/8). No propone
clave para los 4 reactivos de cálculo numérico de pru_02, que quedan como no calificables
(`evidencias/banco_2026-10-24/clave_verdadera.json`).
