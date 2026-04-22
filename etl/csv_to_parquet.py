"""
Pipeline CSV → Parquet — GKMobile / Eatics
==========================================
Limpia, transforma y exporta cada vista a Parquet
listo para subir a S3.

Uso:
    pip install pandas pyarrow
    python csv_to_parquet.py

Salida:
    carpeta  ./parquet/
    ├── operacion_promotores.parquet
    ├── ejecucion_eatics.parquet
    ├── agotados_eatics.parquet
    ├── agotados_con_producto.parquet
    ├── venta_cero.parquet
    ├── precios_eatics.parquet
    └── reporte_marca_pdv.parquet
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
import time

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────
BASE_DIR    = Path("/Users/itzelgescalantenunez/Desktop/Ejercicios DuckDB/GKMobile_v2")
OUTPUT_DIR  = BASE_DIR / "parquet"
OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────
def leer_csv(nombre):
    ruta = BASE_DIR / f"{nombre}.csv"
    print(f"\n📂 Leyendo {ruta.name} ({ruta.stat().st_size / 1_048_576:.1f} MB)...")
    return pd.read_csv(ruta, low_memory=False)


def guardar_parquet(df, nombre):
    ruta = OUTPUT_DIR / f"{nombre}.parquet"
    tabla = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(tabla, ruta, compression="snappy")
    size_mb = ruta.stat().st_size / 1_048_576
    print(f"  ✓ Guardado: {ruta.name}  ({len(df):,} filas · {size_mb:.1f} MB)")
    return df


def limpiar_fechas(df, columnas):
    for col in columnas:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def limpiar_bits(df, columnas):
    """Convierte campos BIT de MySQL (0x00/0x01 o 0/1) a bool limpio."""
    for col in columnas:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: True if str(x) in ("1", "0x01", "True", "true")
                else False if str(x) in ("0", "0x00", "False", "false")
                else None
            ).astype("boolean")
    return df


def resumen(df, nombre):
    nulos = df.isnull().sum()
    nulos = nulos[nulos > 0]
    print(f"\n  📊 {nombre}: {len(df):,} filas · {len(df.columns)} columnas")
    if not nulos.empty:
        print(f"  ⚠️  Nulos: {dict(nulos.head(5))}")


# ─────────────────────────────────────────
# 1 — OPERACIÓN PROMOTORES
# ─────────────────────────────────────────
def transformar_operacion():
    df = leer_csv("v_operacion_promotores")

    # Fechas
    df = limpiar_fechas(df, ["fecha", "inicio_jornada", "fin_jornada"])

    # Columnas calculadas
    df["anio"]  = df["fecha"].dt.year
    df["mes"]   = df["fecha"].dt.month
    df["semana"] = df["fecha"].dt.isocalendar().week.astype("Int64")
    df["dia_semana"] = df["fecha"].dt.day_name()

    # Horas laboradas como float limpio
    df["horas_laboradas"] = pd.to_numeric(df["horas_laboradas"], errors="coerce")

    # Porcentajes como float
    df["pct_cumplimiento_plan"]    = pd.to_numeric(df["pct_cumplimiento_plan"],    errors="coerce")
    df["pct_cumplimiento_visitas"] = pd.to_numeric(df["pct_cumplimiento_visitas"], errors="coerce")

    # Bandera de cumplimiento
    df["cumple_plan"] = df["pct_cumplimiento_plan"] >= 80

    # Nulos en texto → cadena vacía
    for col in ["puesto", "agencia", "supervisor", "entidad", "incidencia"]:
        if col in df.columns:
            df[col] = df[col].fillna("Sin dato")

    resumen(df, "operacion_promotores")
    return guardar_parquet(df, "operacion_promotores")


# ─────────────────────────────────────────
# 2 — EJECUCIÓN EATICS
# ─────────────────────────────────────────
def transformar_ejecucion():
    df = leer_csv("v_ejecucion_eatics")

    df = limpiar_fechas(df, ["fecha"])
    df = limpiar_bits(df, ["con_agotados", "con_preagotados", "planograma",
                           "negocicacion", "is_degustacion", "status"])

    df["anio"]   = df["fecha"].dt.year
    df["mes"]    = df["fecha"].dt.month
    df["semana"] = df["fecha"].dt.isocalendar().week.astype("Int64")

    # Porcentaje de agotados por visita
    df["pct_sku_agotados"] = (
            pd.to_numeric(df["cant_agotados"], errors="coerce") /
            pd.to_numeric(df["cant_sku"], errors="coerce").replace(0, float("nan")) * 100
    ).astype(float).round(2)

    for col in ["nombre_marca", "cadena", "punto_venta", "municipio", "estado"]:
        if col in df.columns:
            df[col] = df[col].fillna("Sin dato")

    resumen(df, "ejecucion_eatics")
    return guardar_parquet(df, "ejecucion_eatics")


# ─────────────────────────────────────────
# 3 — AGOTADOS EATICS
# ─────────────────────────────────────────
def transformar_agotados():
    df = leer_csv("v_agotados_eatics")

    # Este CSV no tiene fecha, solo anio_mes (ej: "2026-03")
    df["anio_mes_dt"] = pd.to_datetime(df["anio_mes"], format="%Y-%m", errors="coerce")
    df["anio"] = df["anio_mes_dt"].dt.year
    df["mes"]  = df["anio_mes_dt"].dt.month
    df.drop(columns=["anio_mes_dt"], inplace=True)

    for col in ["marca", "cadena", "punto_venta", "estado", "municipio"]:
        if col in df.columns:
            df[col] = df[col].fillna("Sin dato")

    df["nivel_quiebre"] = pd.cut(
        pd.to_numeric(df["pct_quiebre"], errors="coerce").fillna(0),
        bins=[-1, 0, 5, 15, 100],
        labels=["Sin quiebre", "Bajo", "Medio", "Alto"]
    )

    resumen(df, "agotados_eatics")
    return guardar_parquet(df, "agotados_eatics")


# ─────────────────────────────────────────
# 4 — AGOTADOS CON PRODUCTO
# ─────────────────────────────────────────
def transformar_agotados_producto():
    df = leer_csv("v_agotados_con_producto")

    df = limpiar_fechas(df, ["fecha"])

    for col in ["marca", "cadena", "punto_venta", "estado", "producto_en_riesgo"]:
        if col in df.columns:
            df[col] = df[col].fillna("Sin dato")

    resumen(df, "agotados_con_producto")
    return guardar_parquet(df, "agotados_con_producto")


# ─────────────────────────────────────────
# 5 — VENTA CERO
# ─────────────────────────────────────────
def transformar_venta_cero():
    df = leer_csv("v_detalle_venta_cero")

    df = limpiar_fechas(df, ["fecha"])
    df = limpiar_bits(df, ["ejecutada"])

    df["anio"] = df["fecha"].dt.year
    df["mes"]  = df["fecha"].dt.month

    df["inventario"] = pd.to_numeric(df["inventario"], errors="coerce")

    for col in ["marca", "cadena", "punto_venta", "estado", "producto", "promotor"]:
        if col in df.columns:
            df[col] = df[col].fillna("Sin dato")

    resumen(df, "venta_cero")
    return guardar_parquet(df, "venta_cero")


# ─────────────────────────────────────────
# 6 — PRECIOS EATICS
# ─────────────────────────────────────────
def transformar_precios():
    df = leer_csv("v_precios_eatics")

    df = limpiar_fechas(df, ["fecha"])
    df = limpiar_bits(df, ["is_propio", "status"])

    df["anio"] = df["fecha"].dt.year
    df["mes"]  = df["fecha"].dt.month

    df["precio"] = pd.to_numeric(df["precio"], errors="coerce")

    # Etiqueta legible
    df["tipo_precio"] = df["is_propio"].map(
        {True: "Propio", False: "Competencia", None: "Sin dato"}
    )

    for col in ["producto", "categoria", "cadena", "punto_venta", "estado", "promotor"]:
        if col in df.columns:
            df[col] = df[col].fillna("Sin dato")

    resumen(df, "precios_eatics")
    return guardar_parquet(df, "precios_eatics")


# ─────────────────────────────────────────
# 7 — REPORTE MARCA PDV
# ─────────────────────────────────────────
def transformar_reporte_marca():
    df = leer_csv("v_reporte_marca_pdv")

    df = limpiar_fechas(df, ["fecha"])

    df["anio"]   = df["fecha"].dt.year
    df["mes"]    = df["fecha"].dt.month
    df["semana"] = df["fecha"].dt.isocalendar().week.astype("Int64")

    # Porcentajes como float
    for col in ["pct_planograma", "pct_visitas_agotados", "pct_sku_agotados",
                "pct_visitas_preagotados", "pct_sku_preagotados"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Semáforo de planograma
    df["nivel_planograma"] = pd.cut(
        df["pct_planograma"].fillna(0),
        bins=[-1, 49, 79, 100],
        labels=["Bajo", "Medio", "Alto"]
    )

    for col in ["cadena", "punto_venta", "municipio", "estado", "marca"]:
        if col in df.columns:
            df[col] = df[col].fillna("Sin dato")

    resumen(df, "reporte_marca_pdv")
    return guardar_parquet(df, "reporte_marca_pdv")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  Pipeline CSV → Parquet — GKMobile / Eatics")
    print("=" * 55)

    t_inicio = time.time()

    transformar_operacion()
    transformar_ejecucion()
    transformar_agotados()
    transformar_agotados_producto()
    transformar_venta_cero()
    transformar_precios()
    transformar_reporte_marca()

    t_total = time.time() - t_inicio
    print(f"\n{'=' * 55}")
    print(f"  ✅ Completado en {t_total:.1f}s")
    print(f"  📁 Archivos en: {OUTPUT_DIR}")
    print(f"{'=' * 55}")