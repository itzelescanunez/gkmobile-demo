"""
KPIs de Procesa — capa de lógica de negocio.
Las funciones reciben DataFrames ya filtrados y retornan metricas o DataFrames listos para graficar.
"""
import pandas as pd


# ─────────────────────────────────────────
# SELL OUT — detalle_sell_out_procesa
# ─────────────────────────────────────────

def kpi_sell_out(df: pd.DataFrame) -> dict:
    """KPIs resumen de sell out."""
    return {
        "total_venta":     round(float(df["venta"].sum()), 2),
        "total_monto":     round(float(df["monto"].sum()), 2),
        "total_piezas":    int(df["piezas"].sum()),
        "pdvs_activos":    df["punto_venta_id"].nunique(),
        "productos":       df["producto_id"].nunique(),
        "precio_promedio": round(float(df["precio"].mean()), 2) if df["precio"].notna().any() else 0,
    }


def venta_por_region(df: pd.DataFrame) -> pd.DataFrame:
    """Venta agrupada por region."""
    return (
        df.groupby("region").agg(
            venta=("venta", "sum"),
            monto=("monto", "sum"),
            piezas=("piezas", "sum"),
            pdvs=("punto_venta_id", "nunique"),
        ).reset_index()
        .sort_values("venta", ascending=False)
    )


def venta_por_canal(df: pd.DataFrame) -> pd.DataFrame:
    """Venta agrupada por canal."""
    return (
        df.groupby("canal_id").agg(
            venta=("venta", "sum"),
            monto=("monto", "sum"),
            piezas=("piezas", "sum"),
        ).reset_index()
        .sort_values("venta", ascending=False)
    )


def venta_por_producto(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N productos por venta."""
    return (
        df.groupby("producto_id").agg(
            venta=("venta", "sum"),
            monto=("monto", "sum"),
            piezas=("piezas", "sum"),
        ).reset_index()
        .sort_values("venta", ascending=False)
        .head(n)
    )


def tendencia_mensual_sell_out(df: pd.DataFrame) -> pd.DataFrame:
    """Venta mensual para grafica de tendencia."""
    return (
        df.groupby(["anio", "mes"]).agg(
            venta=("venta", "sum"),
            monto=("monto", "sum"),
            piezas=("piezas", "sum"),
        ).reset_index()
        .sort_values(["anio", "mes"])
        .assign(periodo=lambda x: x["anio"].astype(str) + "-" + x["mes"].astype(str).str.zfill(2))
    )


def top_pdvs_sell_out(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N PDVs por venta."""
    return (
        df.groupby("punto_venta_id").agg(
            venta=("venta", "sum"),
            monto=("monto", "sum"),
            piezas=("piezas", "sum"),
        ).reset_index()
        .sort_values("venta", ascending=False)
        .head(n)
    )


# ─────────────────────────────────────────
# INVENTARIO — detalle_inventario_procesa
# ─────────────────────────────────────────

def kpi_inventario(df: pd.DataFrame) -> dict:
    """KPIs resumen de inventario."""
    return {
        "existencia_total":       round(float(df["existencia"].sum()), 2),
        "dias_inventario_prom":   round(float(df["dias_inventario"].mean()), 1),
        "sobre_inventario":       int(df["is_sobre_inventario"].sum()),
        "pct_sobre_inventario":   round(df["is_sobre_inventario"].sum() / len(df) * 100, 1) if len(df) else 0,
        "pdvs_monitoreados":      df["punto_venta_id"].nunique(),
        "productos_monitoreados": df["producto_id"].nunique(),
        "venta_total":            round(float(df["venta"].sum()), 2),
    }


def inventario_por_region(df: pd.DataFrame) -> pd.DataFrame:
    """Inventario y dias promedio por region."""
    return (
        df.groupby("region").agg(
            existencia=("existencia", "sum"),
            dias_inventario_prom=("dias_inventario", "mean"),
            sobre_inventario=("is_sobre_inventario", "sum"),
            pdvs=("punto_venta_id", "nunique"),
        ).reset_index()
        .assign(dias_inventario_prom=lambda x: x["dias_inventario_prom"].round(1))
        .sort_values("existencia", ascending=False)
    )


def productos_sobre_inventario(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N productos con mas casos de sobre inventario."""
    return (
        df[df["is_sobre_inventario"] == 1]
        .groupby("producto_id").agg(
            casos=("id", "count"),
            existencia_total=("existencia", "sum"),
            dias_inventario_prom=("dias_inventario", "mean"),
        ).reset_index()
        .assign(dias_inventario_prom=lambda x: x["dias_inventario_prom"].round(1))
        .sort_values("casos", ascending=False)
        .head(n)
    )


def inventario_vs_venta(df: pd.DataFrame) -> pd.DataFrame:
    """Relacion existencia vs venta por producto."""
    return (
        df.groupby("producto_id").agg(
            existencia=("existencia", "sum"),
            venta=("venta", "sum"),
            dias_inventario_prom=("dias_inventario", "mean"),
        ).reset_index()
        .assign(
            ratio_inv_venta=lambda x: (x["existencia"] / x["venta"].replace(0, pd.NA)).round(2),
            dias_inventario_prom=lambda x: x["dias_inventario_prom"].round(1),
        )
        .sort_values("existencia", ascending=False)
    )


def tendencia_mensual_inventario(df: pd.DataFrame) -> pd.DataFrame:
    """Existencia e inventario promedio mensual."""
    return (
        df.groupby(["anio", "mes"]).agg(
            existencia=("existencia", "sum"),
            dias_inventario_prom=("dias_inventario", "mean"),
            sobre_inventario=("is_sobre_inventario", "sum"),
        ).reset_index()
        .sort_values(["anio", "mes"])
        .assign(
            periodo=lambda x: x["anio"].astype(str) + "-" + x["mes"].astype(str).str.zfill(2),
            dias_inventario_prom=lambda x: x["dias_inventario_prom"].round(1),
        )
    )


# ─────────────────────────────────────────
# PRODUCTOS — producto_procesa
# ─────────────────────────────────────────

def catalogo_resumen(df: pd.DataFrame) -> dict:
    """Resumen del catalogo de productos."""
    return {
        "total_productos": len(df),
        "activos":         int((df["status"] == 1).sum()),
        "marcas":          df["marca"].nunique(),
        "canales":         df["canal_id"].nunique(),
        "precio_promedio": round(float(df["precio"].mean()), 2) if df["precio"].notna().any() else 0,
    }


def productos_por_marca(df: pd.DataFrame) -> pd.DataFrame:
    """Conteo de productos por marca."""
    return (
        df.groupby("marca").agg(
            total=("id", "count"),
            activos=("status", "sum"),
            precio_promedio=("precio", "mean"),
        ).reset_index()
        .assign(precio_promedio=lambda x: x["precio_promedio"].round(2))
        .sort_values("total", ascending=False)
    )
