"""
KPIs de Eatics — capa de lógica de negocio.
Las funciones reciben DataFrames ya filtrados y retornan métricas o DataFrames listos para graficar.
"""
import pandas as pd


# ─────────────────────────────────────────
# EJECUCIÓN — reporte_marca_pdv
# ─────────────────────────────────────────

def kpi_generales(df: pd.DataFrame) -> dict:
    """KPIs resumen de ejecución."""
    total_visitas     = int(df["total_visitas"].sum())
    total_sku         = int(df["cant_sku"].sum())
    total_agotados    = int(df["cant_sku_agotados"].sum())
    total_preagotados = int(df["cant_sku_preagotados"].sum())
    return {
        "pdvs_unicos":       df["punto_venta"].nunique(),
        "total_visitas":     total_visitas,
        "total_sku":         total_sku,
        "total_agotados":    total_agotados,
        "total_preagotados": total_preagotados,
        "pct_planograma":    round(df["cumple_planograma"].sum() / total_visitas * 100, 1) if total_visitas else 0,
        "pct_agotados":      round(total_agotados    / total_sku * 100, 1) if total_sku else 0,
        "pct_preagotados":   round(total_preagotados / total_sku * 100, 1) if total_sku else 0,
    }


def visitas_por_marca(df: pd.DataFrame) -> pd.DataFrame:
    """Total de visitas agrupadas por marca."""
    return (
        df.groupby("marca")["total_visitas"]
        .sum().reset_index()
        .sort_values("total_visitas", ascending=True)
    )


def cumplimiento_planograma_por_marca(df: pd.DataFrame) -> pd.DataFrame:
    """% cumplimiento de planograma por marca."""
    res = df.groupby("marca").agg(
        planograma=("cumple_planograma", "sum"),
        visitas=("total_visitas", "sum")
    ).reset_index()
    res["pct_planograma"] = (res["planograma"] / res["visitas"] * 100).round(1)
    return res


def top_pdvs_por_visitas(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N PDVs con más visitas."""
    return (
        df.groupby(["cadena", "punto_venta", "estado"])["total_visitas"]
        .sum().reset_index()
        .sort_values("total_visitas", ascending=False)
        .head(n)
    )


def agotados_por_marca(df: pd.DataFrame) -> pd.DataFrame:
    """% SKU agotados y preagotados por marca."""
    res = df.groupby("marca").agg(
        sku_agotados=("cant_sku_agotados", "sum"),
        sku_preagotados=("cant_sku_preagotados", "sum"),
        sku=("cant_sku", "sum")
    ).reset_index()
    res["pct_agotados"]    = (res["sku_agotados"]    / res["sku"] * 100).round(1)
    res["pct_preagotados"] = (res["sku_preagotados"] / res["sku"] * 100).round(1)
    return res


def top_pdvs_agotados(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N PDVs con más SKU agotados."""
    return (
        df.groupby("punto_venta")["cant_sku_agotados"]
        .sum().reset_index()
        .sort_values("cant_sku_agotados", ascending=False)
        .head(n)
    )


# ─────────────────────────────────────────
# VENTA CERO — venta_cero
# ─────────────────────────────────────────

def kpi_venta_cero(df: pd.DataFrame) -> dict:
    """KPIs resumen de venta cero."""
    return {
        "total_registros": len(df),
        "ejecutadas":      int(df["ejecutada"].sum()),
        "pendientes":      int((df["ejecutada"] == 0).sum()),
        "pct_ejecutado":   round(df["ejecutada"].sum() / len(df) * 100, 1) if len(df) else 0,
        "marcas_afectadas": df["marca"].nunique(),
        "pdvs_afectados":  df["punto_venta"].nunique(),
    }


def venta_cero_por_marca(df: pd.DataFrame) -> pd.DataFrame:
    """Conteo de registros de venta cero por marca."""
    return df.groupby("marca").size().reset_index(name="registros")


def estatus_ejecucion(df: pd.DataFrame) -> dict:
    """Conteo ejecutada vs pendiente."""
    counts = df["ejecutada"].value_counts()
    return {
        "ejecutada": int(counts.get(1, 0)),
        "pendiente": int(counts.get(0, 0)),
    }


# ─────────────────────────────────────────
# PRECIOS — precios_eatics
# ─────────────────────────────────────────

def kpi_precios(df: pd.DataFrame) -> dict:
    """KPIs resumen de precios."""
    propios      = df[df["is_propio"] == 1]["precio"]
    competencia  = df[df["is_propio"] == 0]["precio"]
    return {
        "total_registros":      len(df),
        "precio_promedio_propio":      round(propios.mean(), 2)     if len(propios) else 0,
        "precio_promedio_competencia": round(competencia.mean(), 2) if len(competencia) else 0,
        "productos_propios":    df[df["is_propio"] == 1]["producto"].nunique(),
        "productos_competencia":df[df["is_propio"] == 0]["producto"].nunique(),
        "cadenas_monitoreadas": df["cadena"].nunique(),
    }


def precio_promedio_por_tipo(df: pd.DataFrame) -> pd.DataFrame:
    """Precio promedio agrupado por tipo (Propio / Competencia)."""
    df = df.copy()
    df["tipo"] = df["is_propio"].apply(lambda x: "Propio" if int(x or 0) == 1 else "Competencia")
    return df.groupby("tipo")["precio"].mean().round(2).reset_index()


def precio_por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    """Precio promedio por categoría y tipo."""
    df = df.copy()
    df["tipo"] = df["is_propio"].apply(lambda x: "Propio" if int(x or 0) == 1 else "Competencia")
    return (
        df[df["categoria"].notna()]
        .groupby(["categoria", "tipo"])["precio"]
        .mean().round(2).reset_index()
    )


# ─────────────────────────────────────────
# EJECUCIÓN DETALLE — ejecucion_eatics
# ─────────────────────────────────────────

def ejecucion_por_promotor(df: pd.DataFrame) -> pd.DataFrame:
    """Resumen de ejecución por promotor."""
    return (
        df.groupby("promotor").agg(
            visitas=("punto_venta_id", "count"),
            agotados=("cant_agotados", "sum"),
            preagotados=("cant_preagotados", "sum"),
            sku=("cant_sku", "sum"),
            con_planograma=("planograma", "sum"),
        ).reset_index()
        .sort_values("visitas", ascending=False)
    )


def ejecucion_por_cadena(df: pd.DataFrame) -> pd.DataFrame:
    """Resumen de ejecución por cadena."""
    return (
        df.groupby("cadena").agg(
            visitas=("punto_venta_id", "count"),
            pdvs=("punto_venta_id", "nunique"),
            agotados=("cant_agotados", "sum"),
            sku=("cant_sku", "sum"),
        ).reset_index()
        .sort_values("visitas", ascending=False)
    )


# ─────────────────────────────────────────
# AGOTADOS — agotados_eatics
# ─────────────────────────────────────────

def quiebre_por_marca(df: pd.DataFrame) -> pd.DataFrame:
    """% quiebre de stock por marca."""
    return (
        df.groupby("marca").agg(
            total_agotados=("total_agotados", "sum"),
            total_sku=("total_sku", "sum"),
            visitas=("visitas", "sum"),
        ).reset_index()
        .assign(pct_quiebre=lambda x: (x["total_agotados"] / x["total_sku"] * 100).round(1))
        .sort_values("pct_quiebre", ascending=False)
    )


def top_pdvs_quiebre(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N PDVs con mayor % de quiebre."""
    return (
        df.groupby(["punto_venta", "cadena", "estado"]).agg(
            total_agotados=("total_agotados", "sum"),
            total_sku=("total_sku", "sum"),
        ).reset_index()
        .assign(pct_quiebre=lambda x: (x["total_agotados"] / x["total_sku"] * 100).round(1))
        .sort_values("pct_quiebre", ascending=False)
        .head(n)
    )
