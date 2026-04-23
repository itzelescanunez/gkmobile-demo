import sys
sys.path.insert(0, '.')

import pytest
import pandas as pd
from clients.procesa.kpis import (
    kpi_sell_out,
    venta_por_region,
    venta_por_canal,
    venta_por_producto,
    tendencia_mensual_sell_out,
    top_pdvs_sell_out,
    kpi_inventario,
    inventario_por_region,
    productos_sobre_inventario,
    inventario_vs_venta,
    tendencia_mensual_inventario,
    catalogo_resumen,
    productos_por_marca,
)

# ─────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────

@pytest.fixture
def df_sell_out():
    return pd.DataFrame({
        "venta":          [100.0, 200.0, 150.0, 50.0],
        "monto":          [1000.0, 2000.0, 1500.0, 500.0],
        "piezas":         [10, 20, 15, 5],
        "precio":         [10.0, 10.0, 10.0, 10.0],
        "punto_venta_id": [1, 2, 1, 3],
        "producto_id":    [101, 102, 101, 103],
        "canal_id":       [1, 1, 2, 2],
        "region":         ["Norte", "Sur", "Norte", "Sur"],
        "anio":           [2025, 2025, 2025, 2025],
        "mes":            [1, 1, 2, 2],
    })

@pytest.fixture
def df_inventario():
    return pd.DataFrame({
        "id":                   [1, 2, 3, 4],
        "existencia":           [500.0, 300.0, 200.0, 100.0],
        "venta":                [50.0, 30.0, 20.0, 10.0],
        "dias_inventario":      [10.0, 8.0, 12.0, 6.0],
        "is_sobre_inventario":  [1, 0, 1, 0],
        "is_sobre_inventario4sem": [1, 0, 1, 0],
        "punto_venta_id":       [1, 2, 1, 3],
        "producto_id":          [101, 102, 101, 103],
        "region":               ["Norte", "Sur", "Norte", "Sur"],
        "anio":                 [2025, 2025, 2025, 2025],
        "mes":                  [1, 1, 2, 2],
    })

@pytest.fixture
def df_productos():
    return pd.DataFrame({
        "id":      [1, 2, 3, 4],
        "nombre":  ["Prod A", "Prod B", "Prod C", "Prod D"],
        "marca":   ["MarcaX", "MarcaX", "MarcaY", "MarcaY"],
        "status":  [1, 1, 0, 1],
        "precio":  [10.0, 20.0, 15.0, 25.0],
        "canal_id":[1, 1, 2, 2],
    })

# ─────────────────────────────────────────
# TESTS — sell out
# ─────────────────────────────────────────

def test_kpi_sell_out_keys(df_sell_out):
    result = kpi_sell_out(df_sell_out)
    assert "total_venta"     in result
    assert "total_monto"     in result
    assert "total_piezas"    in result
    assert "pdvs_activos"    in result
    assert "precio_promedio" in result

def test_kpi_sell_out_valores(df_sell_out):
    result = kpi_sell_out(df_sell_out)
    assert result["total_venta"]  == 500.0
    assert result["total_monto"]  == 5000.0
    assert result["total_piezas"] == 50
    assert result["pdvs_activos"] == 3

def test_venta_por_region_columnas(df_sell_out):
    result = venta_por_region(df_sell_out)
    assert "region" in result.columns
    assert "venta"  in result.columns
    assert "monto"  in result.columns

def test_venta_por_region_orden(df_sell_out):
    result = venta_por_region(df_sell_out)
    assert result.iloc[0]["venta"] >= result.iloc[1]["venta"]

def test_venta_por_canal_columnas(df_sell_out):
    result = venta_por_canal(df_sell_out)
    assert "canal_id" in result.columns
    assert "venta"    in result.columns

def test_venta_por_producto_limite(df_sell_out):
    result = venta_por_producto(df_sell_out, n=2)
    assert len(result) <= 2

def test_tendencia_mensual_columnas(df_sell_out):
    result = tendencia_mensual_sell_out(df_sell_out)
    assert "periodo" in result.columns
    assert "venta"   in result.columns

def test_tendencia_mensual_orden(df_sell_out):
    result = tendencia_mensual_sell_out(df_sell_out)
    periodos = result["periodo"].tolist()
    assert periodos == sorted(periodos)

def test_top_pdvs_sell_out_limite(df_sell_out):
    result = top_pdvs_sell_out(df_sell_out, n=2)
    assert len(result) <= 2

# ─────────────────────────────────────────
# TESTS — inventario
# ─────────────────────────────────────────

def test_kpi_inventario_keys(df_inventario):
    result = kpi_inventario(df_inventario)
    assert "existencia_total"     in result
    assert "dias_inventario_prom" in result
    assert "sobre_inventario"     in result
    assert "pct_sobre_inventario" in result

def test_kpi_inventario_valores(df_inventario):
    result = kpi_inventario(df_inventario)
    assert result["existencia_total"]   == 1100.0
    assert result["sobre_inventario"]   == 2
    assert result["pct_sobre_inventario"] == 50.0

def test_inventario_por_region_columnas(df_inventario):
    result = inventario_por_region(df_inventario)
    assert "region"               in result.columns
    assert "existencia"           in result.columns
    assert "dias_inventario_prom" in result.columns

def test_productos_sobre_inventario(df_inventario):
    result = productos_sobre_inventario(df_inventario)
    assert "producto_id" in result.columns
    assert "casos"       in result.columns
    assert (result["casos"] > 0).all()

def test_inventario_vs_venta_columnas(df_inventario):
    result = inventario_vs_venta(df_inventario)
    assert "existencia"      in result.columns
    assert "venta"           in result.columns
    assert "ratio_inv_venta" in result.columns

def test_tendencia_inventario_orden(df_inventario):
    result = tendencia_mensual_inventario(df_inventario)
    periodos = result["periodo"].tolist()
    assert periodos == sorted(periodos)

# ─────────────────────────────────────────
# TESTS — productos
# ─────────────────────────────────────────

def test_catalogo_resumen_keys(df_productos):
    result = catalogo_resumen(df_productos)
    assert "total_productos" in result
    assert "activos"         in result
    assert "marcas"          in result
    assert "precio_promedio" in result

def test_catalogo_resumen_valores(df_productos):
    result = catalogo_resumen(df_productos)
    assert result["total_productos"] == 4
    assert result["activos"]         == 3
    assert result["marcas"]          == 2

def test_productos_por_marca_columnas(df_productos):
    result = productos_por_marca(df_productos)
    assert "marca"           in result.columns
    assert "total"           in result.columns
    assert "precio_promedio" in result.columns

def test_productos_por_marca_orden(df_productos):
    result = productos_por_marca(df_productos)
    assert result.iloc[0]["total"] >= result.iloc[1]["total"]
