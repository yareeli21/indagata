"""
coherencia.py — respuestas coherentes para las preguntas de encuesta que no son Likert.

Problema que resuelve
---------------------
En la versión 1.0 del motor, las preguntas de opción múltiple, Sí/No y escala numérica se
sorteaban con la misma probabilidad para todas las opciones: no dependían del perfil del
estudiante ni de sus otras respuestas. Este módulo las hace depender de FACTORES del propio
respondente, con reglas escritas en `config/coherencia_encuestas.json`.

Cómo funciona (una sola idea para todos los tipos)
--------------------------------------------------
1. Cada pregunta declara de qué depende y con qué peso:
       "factores": {"promedio_gpa": -0.6, "dimension:Organización del tiempo": 0.4}
   - Un factor puede ser:
       · "likert": el promedio de todas las respuestas Likert de la persona;
       · "dimension:<nombre>": el promedio de los ítems de esa dimensión;
       · un dato de contexto numérico: edad, semestre, promedio_gpa, horas_trabajo_semana,
         o uno booleano: tiene_beca, primera_generacion (1 = sí, 0 = no).
   - El signo del peso es la dirección (positivo: a más factor, más «Sí», número más alto
     u opción más al final de la lista) y su tamaño, la fuerza (0 = no influye, 1 = decide).
2. Con esos factores se calcula, para cada persona, una TENDENCIA:
       tendencia = Σ peso · factor_estandarizado + ruido
   El ruido completa lo que los factores no explican, así que nadie queda determinado.
3. La tendencia se convierte en la respuesta según el tipo de pregunta:
   - Sí/No: «Sí» para quienes tienen tendencia alta; `prob_si` fija cuántos en total.
   - Opción múltiple: se ordenan las opciones de menor a mayor (`orden`) y la tendencia elige
     la posición; `proporciones` fija qué parte de la muestra cae en cada opción.
   - Escala numérica: número = media + desviación · tendencia, recortado al rango.
   - Selección múltiple: cada opción se marca o no como un Sí/No con su propia regla.
   - Jerarquización: cada opción recibe un puntaje (sus factores + ruido) y se ordenan.
   - Abierta: la tendencia elige el tono de la respuesta (baja, media o alta) de unas
     plantillas escritas en la definición del instrumento.
4. Dos reglas especiales para datos que deben cuadrar exactamente:
   - "cortes": la respuesta sale de un número por tramos (horas de trabajo → «No trabajo»,
     «Menos de 20 h»…). El número puede ser un dato de contexto o la respuesta a otra pregunta
     («pregunta:<texto>»).
   - "mapa": la respuesta sale de un dato de contexto de categorías (genero, perfil, tiene_beca)
     con una probabilidad por opción.
Una pregunta sin regla conserva el sorteo uniforme de la versión 1.0 (o `proporciones`).
"""
from __future__ import annotations

from statistics import NormalDist

import numpy as np

_NORMAL = NormalDist()
_BOOLEANOS = {"tiene_beca", "primera_generacion"}


def _estandarizar(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    sd = x.std()
    return (x - x.mean()) / sd if sd > 0 else np.zeros_like(x)


class Factores:
    """Valores de cada factor por respondente, ya estandarizados (media 0, desviación 1)."""

    def __init__(self, likert: np.ndarray, dimensiones: list[dict], demografia: list[dict]):
        self._valores: dict[str, np.ndarray] = {"likert": _estandarizar(likert.mean(axis=1))}
        inicio = 0
        for d in dimensiones:
            fin = inicio + d["n_items"]
            self._valores[f"dimension:{d['nombre']}"] = _estandarizar(likert[:, inicio:fin].mean(axis=1))
            inicio = fin
        self.demografia = demografia
        self.respuestas: dict[str, list] = {}  # texto de pregunta → respuestas ya generadas

    def __call__(self, nombre: str) -> np.ndarray:
        if nombre in self._valores:
            return self._valores[nombre]
        if nombre.startswith("pregunta:"):
            return _estandarizar(np.array(self.crudo(nombre), dtype=float))
        if nombre in _BOOLEANOS or nombre in self.demografia[0]:
            return _estandarizar(np.array(self.crudo(nombre), dtype=float))
        raise KeyError(f"Factor desconocido en coherencia_encuestas.json: {nombre!r}")

    def crudo(self, nombre: str, numerico: bool = True) -> list:
        """Valor sin estandarizar: número para factores y «cortes»; tal cual para «mapa»."""
        if nombre.startswith("pregunta:"):
            return self.respuestas[nombre.removeprefix("pregunta:")]
        return [float(d[nombre]) if numerico and nombre in _BOOLEANOS else d[nombre] for d in self.demografia]


def tendencia(factores: Factores, pesos: dict[str, float], rng: np.random.Generator) -> np.ndarray:
    """Σ peso · factor + ruido, estandarizada: la «inclinación» de cada persona en la pregunta."""
    n = len(factores.demografia)
    suma = np.zeros(n)
    for nombre, peso in (pesos or {}).items():
        suma += float(peso) * factores(nombre)
    explicado = min(sum(float(p) ** 2 for p in (pesos or {}).values()), 0.95)
    return _estandarizar(suma + np.sqrt(1 - explicado) * rng.standard_normal(n))


def _cortes_normales(proporciones: list[float]) -> list[float]:
    acumulada = np.cumsum(np.asarray(proporciones, dtype=float) / sum(proporciones))[:-1]
    return [_NORMAL.inv_cdf(min(max(p, 1e-6), 1 - 1e-6)) for p in acumulada]


def _por_cortes(valores: list, cortes: list[float], opciones: list[str]) -> list[str]:
    return [opciones[sum(1 for c in cortes if float(v) >= c)] for v in valores]


def _por_mapa(valores: list, mapa: dict, opciones: list[str], rng: np.random.Generator) -> list[str]:
    salida = []
    for v in valores:
        dist = mapa.get(str(v), mapa.get("*"))
        if isinstance(dist, str):
            salida.append(dist)
            continue
        dist = dist or {o: 1 for o in opciones}
        nombres, pesos = list(dist), np.array(list(dist.values()), dtype=float)
        salida.append(str(rng.choice(nombres, p=pesos / pesos.sum())))
    return salida


def opcion(regla: dict, opciones: list[str], factores: Factores, rng: np.random.Generator) -> list[str]:
    """Opción múltiple (una respuesta) o Sí/No (opciones = ["Sí", "No"])."""
    n = len(factores.demografia)
    if "cortes" in regla:
        return _por_cortes(factores.crudo(regla["variable"]), regla["cortes"], regla.get("orden") or opciones)
    if "mapa" in regla:
        return _por_mapa(factores.crudo(regla["variable"], numerico=False), regla["mapa"], opciones, rng)
    orden = regla.get("orden") or opciones
    proporciones = regla.get("proporciones") or [1] * len(orden)
    if not regla.get("factores"):  # sin factores: sorteo con las proporciones dadas
        p = np.asarray(proporciones, dtype=float)
        return [str(o) for o in rng.choice(orden, size=n, p=p / p.sum())]
    t = tendencia(factores, regla["factores"], rng)
    return _por_cortes(t, _cortes_normales(proporciones), orden)


def si_no(regla: dict, factores: Factores, rng: np.random.Generator) -> list[str]:
    if "mapa" in regla:
        return _por_mapa(factores.crudo(regla["variable"], numerico=False), regla["mapa"], ["Sí", "No"], rng)
    prob_si = float(regla.get("prob_si", 0.5))
    return opcion({"factores": regla.get("factores"), "orden": ["No", "Sí"],
                   "proporciones": [1 - prob_si, prob_si]}, ["No", "Sí"], factores, rng)


def escala(regla: dict, minimo: int, maximo: int, factores: Factores, rng: np.random.Generator) -> list[int]:
    media = float(regla.get("media", (minimo + maximo) / 2))
    desviacion = float(regla.get("desviacion", (maximo - minimo) / 5))
    t = tendencia(factores, regla.get("factores"), rng)
    return [int(v) for v in np.clip(np.rint(media + desviacion * t), minimo, maximo)]


def seleccion_multiple(opciones: dict[str, dict], factores: Factores, rng: np.random.Generator,
                       ninguna: str = "Ninguno") -> list[str]:
    marcadas = {}
    for nombre, regla in opciones.items():
        marcadas[nombre] = si_no({"factores": regla.get("factores"), "prob_si": regla.get("prob", 0.35)}, factores, rng)
    n = len(factores.demografia)
    return ["; ".join(o for o in opciones if marcadas[o][i] == "Sí") or ninguna for i in range(n)]


def jerarquizacion(opciones: dict[str, dict], factores: Factores, rng: np.random.Generator) -> list[str]:
    nombres = list(opciones)
    puntajes = np.column_stack([
        float(regla.get("base", 0)) + tendencia(factores, regla.get("factores"), rng) for regla in opciones.values()
    ])
    return [", ".join(nombres[j] for j in np.argsort(-fila)) for fila in puntajes]


def abierta(regla: dict, plantillas: dict[str, list[str]], factores: Factores, rng: np.random.Generator) -> list[str]:
    t = tendencia(factores, regla.get("factores"), rng)
    tercil = _NORMAL.inv_cdf(2 / 3)
    nivel = ["baja" if x < -tercil else "alta" if x > tercil else "media" for x in t]
    return [str(rng.choice(plantillas[nv])) for nv in nivel]
