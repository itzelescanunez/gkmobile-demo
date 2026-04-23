import sys
sys.path.insert(0, '.')

import pytest
import pandas as pd
from clients.eatics.kpis import (
    kpi_generales,
    visitas_por_marca,
    cumplimiento_planograma_por_marca,
    top_pdvs_por_visitas,
    agotados_por_marca,
    top_pdvs_agotados,
    kpi_venta_cero,
    venta_cero_por_marca,
    estatus_ejecucion,
    kpi_precios,
    precio_promedio_por_tipo,
    precio_por_categoria,
    ejecucion_por_promotor,
    ejecucion_por_cadena,
    quiebre_por_marca,
    top_pdvs_quiebre,
)

# ─────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────

@pytest.fixture
def df_ejecucion():
    return pd.DataFrame({
        "punto_venta":          ["PDV A", "PDV B", "PDV A", "PDV C"],
        "cadena":               ["Walmart", "Oxxo", "Walmart", "7Eleven"],
        "estado":               ["CDMX", "MTY", "CDMX", "GDL"],
        "marca":                ["MarcaX", "MarcaY", "MarcaX", "MarcaY"],
        "total_visitas":        [10, 5, 8, 3],
        "cant_sku":             [100, 50, 80, 30],
        "cumple_planograma":    [8, 3, 6, 2],
        "cant_sku_agotados":    [5, 2, 3, 1],
        "cant_sku_preagotados": [3, 1, 2, 0],
    })

@pytest.fixture
def df_venta_cero():
    return pd.DataFrame({
        "marca":       ["MarcaX", "MarcaX", "MarcaY", "MarcaY"],
        "producto":    ["Prod1", "Prod2", "Prod3", "Prod4"],
        "punto_venta": ["PDV A", "PDV B", "PDV A", "PDV C"],
        "ejecutada":   [1, 0, 1, 0],
    })

@pytest.fixture
def df_precios():
    return pd.DataFrame({
        "producto":   ["Prod1", "Prod2", "Prod3", "Prod4"],
        "categoria":  ["Cat A", "Cat A", "Cat B", "Cat B"],
        "cadena":     ["Walmart", "Oxxo", "Walmart", "Oxxo"],
        "precio":     [10.0, 12.0, 8.0, 9.0],
        "is_propio":  [1, 1, 0, 0],
    })

@pytest.fixture
def df_ejecucion_detalle():
    return pd.DataFrame({
        "promotor":       ["Ana", "Ana", "Bob", "Bob"],
        "punto_venta_id": [1, 2, 3, 4],
        "cadena":         ["Walmart", "Oxxo", "Walmart", "7Eleven"],
        "cant_sku":       [10, 8, 12, 6],
        "cant_agotados":  [1, 0, 2, 1],
        "cant_preagotados": [0, 1, 1, 0],
        "planograma":     [1, 1, 0, 1],
    })

@pytest.fixture
def df_agotados():
    return pd.DataFrame({
        "marca":            ["MarcaX", "MarcaX", "MarcaY"],
        "punto_venta":      ["PDV A", "PDV B", "PDV A"],
        "cadena":           ["Walmart", "Oxxo", "Walmart"],
        "estado":           ["CDMX", "MTY", "CDMX"],
        "total_agotados":   [5, 3, 2],
        "total_preagotados":[2, 1, 1],
        "total_sku":        [50, 30, 20],
        "visitas":          [10, 6, 4],
    })

# ─────────────────────────────────────────
# TESTS — kpi_generales
# ─────────────────────────────────────────

def test_kpi_generales_keys(df_ejecucion):
    result = kpi_generales(df_ejecucion)
    expected_keys = {"pdvs_unicos","total_visitas","total_sku","total_agotados",
                     "total_preagotados","pct_planograma","pct_agotados","pct_preagotados"}
    assert expected_keys == set(result.keys())

def test_kpi_generales_valores(df_ejecucion):
    result = kpi_generales(df_ejecucion)
    assert result["total_visitas"]  == 26
    assert result["total_sku"]      == 260
    assert result["total_agotados"] == 11
    assert result["pdvs_unicos"]    == 3

def test_kpi_generales_df_vacio():
    df = pd.DataFrame(columns=["punto_venta","total_visitas","cant_sku",
                                "cumple_planograma","cant_sku_agotados","cant_sku_preagotados"])
    result = kpi_generales(df)
    assert result["pct_planograma"] == 0
    assert result["pct_agotados"]   == 0

# ─────────────────────────────────────────
# TESTS — visitas_por_marca
# ─────────────────────────────────────────

def test_visitas_por_marca_columnas(df_ejecucion):
    result = visitas_por_marca(df_ejecucion)
    assert "marca" in result.columns
    assert "total_visitas" in result.columns

def test_visitas_por_marca_valores(df_ejecucion):
    result = visitas_por_marca(df_ejecucion)
    marcax = result[result["marca"] == "MarcaX"]["total_visitas"].values[0]
    assert marcax == 18

# ─────────────────────────────────────────
# TESTS — top_pdvs_por_visitas
# ─────────────────────────────────────────

def test_top_pdvs_limite(df_ejecucion):
    result = top_pdvs_por_visitas(df_ejecucion, n=2)
    assert len(result) <= 2

def test_top_pdvs_orden(df_ejecucion):
    result = top_pdvs_por_visitas(df_ejecucion)
    assert result.iloc[0]["total_visitas"] >= result.iloc[1]["total_visitas"]

# ─────────────────────────────────────────
# TESTS — agotados_por_marca
# ─────────────────────────────────────────

def test_agotados_por_marca_columnas(df_ejecucion):
    result = agotados_por_marca(df_ejecucion)
    assert "pct_agotados"    in result.columns
    assert "pct_preagotados" in result.columns

def test_agotados_pct_rango(df_ejecucion):
    result = agotados_por_marca(df_ejecucion)
    assert (result["pct_agotados"] >= 0).all()
    assert (result["pct_agotados"] <= 100).all()

# ─────────────────────────────────────────
# TESTS — venta_cero
# ─────────────────────────────────────────

def test_kpi_venta_cero_keys(df_venta_cero):
    result = kpi_venta_cero(df_venta_cero)
    assert "total_registros" in result
    assert "pct_ejecutado"   in result

def test_kpi_venta_cero_valores(df_venta_cero):
    result = kpi_venta_cero(df_venta_cero)
    assert result["total_registros"] == 4
    assert result["ejecutadas"]      == 2
    assert result["pendientes"]      == 2
    assert result["pct_ejecutado"]   == 50.0

def test_estatus_ejecucion(df_venta_cero):
    result = estatus_ejecucion(df_venta_cero)
    assert result["ejecutada"] == 2
    assert result["pendiente"] == 2

# ─────────────────────────────────────────
# TESTS — precios
# ─────────────────────────────────────────

def test_kpi_precios_keys(df_precios):
    result = kpi_precios(df_precios)
    assert "precio_promedio_propio"      in result
    assert "precio_promedio_competencia" in result
    assert "cadenas_monitoreadas"        in result

def test_kpi_precios_valores(df_precios):
    result = kpi_precios(df_precios)
    assert result["precio_promedio_propio"]      == 11.0
    assert result["precio_promedio_competencia"] == 8.5

def test_precio_promedio_por_tipo_columnas(df_precios):
    result = precio_promedio_por_tipo(df_precios)
    assert "tipo"   in result.columns
    assert "precio" in result.columns
    assert set(result["tipo"]) == {"Propio", "Competencia"}

def test_precio_por_categoria_columnas(df_precios):
    result = precio_por_categoria(df_precios)
    assert "categoria" in result.columns
    assert "tipo"      in result.columns
    assert "precio"    in result.columns

# ─────────────────────────────────────────
# TESTS — ejecucion detalle
# ─────────────────────────────────────────

def test_ejecucion_por_promotor_columnas(df_ejecucion_detalle):
    result = ejecucion_por_promotor(df_ejecucion_detalle)
    assert "promotor" in result.columns
    assert "visitas"  in result.columns

def test_ejecucion_por_promotor_orden(df_ejecucion_detalle):
    result = ejecucion_por_promotor(df_ejecucion_detalle)
    assert result.iloc[0]["visitas"] >= result.iloc[1]["visitas"]

def test_ejecucion_por_cadena_columnas(df_ejecucion_detalle):
    result = ejecucion_por_cadena(df_ejecucion_detalle)
    assert "cadena"  in result.columns
    assert "visitas" in result.columns

# ─────────────────────────────────────────
# TESTS — agotados
# ─────────────────────────────────────────

def test_quiebre_por_marca_columnas(df_agotados):
    result = quiebre_por_marca(df_agotados)
    assert "marca"       in result.columns
    assert "pct_quiebre" in result.columns

def test_quiebre_pct_rango(df_agotados):
    result = quiebre_por_marca(df_agotados)
    assert (result["pct_quiebre"] >= 0).all()
    assert (result["pct_quiebre"] <= 100).all()

def test_top_pdvs_quiebre_limite(df_agotados):
    result = top_pdvs_quiebre(df_agotados, n=2)
    assert len(result) <= 2
