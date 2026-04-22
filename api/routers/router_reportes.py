from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date
from collections import defaultdict

from api.database import SessionLocal
from models.model_reporte import ReporteMarcaPdv
from models.model_venta_cero import DetalleVentaCero
from models.model_precios_agotados import AgotadosConProducto

router_reportes = APIRouter(prefix="/reportes", tags=["Reportes"])
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────
# REPORTE MARCA PDV
# ─────────────────────────────────────────
@router_reportes.get("/marca-pdv", response_class=HTMLResponse)
def reporte_marca_pdv(
        request: Request,
        fecha_ini: Optional[str] = None,
        fecha_fin: Optional[str] = None,
        marca: Optional[str] = None,
        cadena: Optional[str] = None,
        db: Session = Depends(get_db),
):
    if not fecha_ini:
        hoy = date.today()
        fecha_ini = hoy.replace(day=1).strftime("%Y-%m-%d")
    if not fecha_fin:
        fecha_fin = date.today().strftime("%Y-%m-%d")

    query = db.query(ReporteMarcaPdv).filter(
        ReporteMarcaPdv.fecha >= fecha_ini,
        ReporteMarcaPdv.fecha <= fecha_fin,
        )
    if marca and marca != "todas":
        query = query.filter(ReporteMarcaPdv.marca == marca)
    if cadena and cadena != "todas":
        query = query.filter(ReporteMarcaPdv.cadena == cadena)

    registros_raw = query.all()

    # Agrupar dinámicamente por cadena + pdv + marca
    agrupado = defaultdict(lambda: {
        "cadena": "", "punto_venta": "", "municipio": "", "estado": "", "marca": "",
        "pdv_id": None,
        "total_visitas": 0, "cant_sku": 0,
        "cumple_planograma": 0,
        "visitas_con_agotados": 0, "cant_sku_agotados": 0,
        "visitas_con_preagotados": 0, "cant_sku_preagotados": 0,
    })

    for r in registros_raw:
        key = (r.cadena, r.pdv_id, r.marca)
        g = agrupado[key]
        g["cadena"]       = r.cadena or ""
        g["punto_venta"]  = r.punto_venta or ""
        g["municipio"]    = r.municipio or ""
        g["estado"]       = r.estado or ""
        g["marca"]        = r.marca or ""
        g["pdv_id"]       = r.pdv_id
        g["total_visitas"]           += int(r.total_visitas or 0)
        g["cant_sku"]                += int(r.cant_sku or 0)
        g["cumple_planograma"]       += int(r.cumple_planograma or 0)
        g["visitas_con_agotados"]    += int(r.visitas_con_agotados or 0)
        g["cant_sku_agotados"]       += int(r.cant_sku_agotados or 0)
        g["visitas_con_preagotados"] += int(r.visitas_con_preagotados or 0)
        g["cant_sku_preagotados"]    += int(r.cant_sku_preagotados or 0)

    # Calcular porcentajes finales
    registros = []
    for g in agrupado.values():
        tv = g["total_visitas"]
        sk = g["cant_sku"]
        g["pct_planograma"]          = round(g["cumple_planograma"] / tv * 100, 1) if tv else 0
        g["pct_visitas_agotados"]    = round(g["visitas_con_agotados"] / tv * 100, 1) if tv else 0
        g["pct_sku_agotados"]        = round(g["cant_sku_agotados"] / sk * 100, 1) if sk else 0
        g["pct_visitas_preagotados"] = round(g["visitas_con_preagotados"] / tv * 100, 1) if tv else 0
        g["pct_sku_preagotados"]     = round(g["cant_sku_preagotados"] / sk * 100, 1) if sk else 0
        registros.append(g)

    registros = sorted(registros, key=lambda x: (x["cadena"], x["punto_venta"], x["marca"]))

    # ── Productos agotados por PDV+marca ──
    pdv_ids_en_reporte = list(set(r["pdv_id"] for r in registros if r["pdv_id"]))
    marcas_en_reporte  = list(set(r["marca"]  for r in registros if r["marca"]))

    agotados_query = db.query(AgotadosConProducto).filter(
        AgotadosConProducto.punto_venta_id.in_(pdv_ids_en_reporte),
        AgotadosConProducto.marca.in_(marcas_en_reporte),
        text(f"fecha >= '{fecha_ini}'"),
        text(f"fecha <= '{fecha_fin}'"),
    )

    agotados_por_pdv = defaultdict(set)
    for a in agotados_query.all():
        if a.producto_en_riesgo and a.cant_agotados and a.cant_agotados > 0:
            key = f"{a.punto_venta_id}_{a.marca}"
            agotados_por_pdv[key].add(a.producto_en_riesgo)

    agotados_por_pdv = {k: list(v) for k, v in agotados_por_pdv.items()}

    # KPIs
    total_visitas     = sum(r["total_visitas"] for r in registros)
    total_sku         = sum(r["cant_sku"] for r in registros)
    total_agotados    = sum(r["cant_sku_agotados"] for r in registros)
    total_preagotados = sum(r["cant_sku_preagotados"] for r in registros)
    pct_agotados_gral = round(total_agotados / total_sku * 100, 1) if total_sku else 0
    pct_pre_gral      = round(total_preagotados / total_sku * 100, 1) if total_sku else 0
    pdvs_unicos       = len(set(r["pdv_id"] for r in registros))

    marcas_disp  = sorted(set(r.marca  for r in db.query(ReporteMarcaPdv.marca).distinct()  if r.marca))
    cadenas_disp = sorted(set(r.cadena for r in db.query(ReporteMarcaPdv.cadena).distinct() if r.cadena))

    return templates.TemplateResponse(
        request=request,
        name="reportes/marca_pdv.html",
        context={
            "registros": registros,
            "agotados_por_pdv": agotados_por_pdv,
            "fecha_ini": fecha_ini, "fecha_fin": fecha_fin,
            "marca": marca or "todas", "cadena": cadena or "todas",
            "marcas_disp": marcas_disp, "cadenas_disp": cadenas_disp,
            "total_visitas": total_visitas, "total_sku": total_sku,
            "total_agotados": total_agotados, "total_preagotados": total_preagotados,
            "pct_agotados_gral": pct_agotados_gral, "pct_pre_gral": pct_pre_gral,
            "pdvs_unicos": pdvs_unicos, "catalogo": "reporte-marca-pdv",
        },
    )


# ─────────────────────────────────────────
# VENTA CERO
# ─────────────────────────────────────────
@router_reportes.get("/venta-cero", response_class=HTMLResponse)
def reporte_venta_cero(
        request: Request,
        fecha_ini: Optional[str] = None,
        fecha_fin: Optional[str] = None,
        marca: Optional[str] = None,
        cadena: Optional[str] = None,
        db: Session = Depends(get_db),
):
    if not fecha_ini:
        fecha_ini = "2026-03-01"
    if not fecha_fin:
        fecha_fin = "2026-03-31"

    query = db.query(DetalleVentaCero)

    if fecha_ini and fecha_fin:
        query = query.filter(
            DetalleVentaCero.fecha >= fecha_ini,
            DetalleVentaCero.fecha <= fecha_fin,
            )
    if marca and marca != "todas":
        query = query.filter(DetalleVentaCero.marca == marca)
    if cadena and cadena != "todas":
        query = query.filter(DetalleVentaCero.cadena == cadena)

    registros = query.order_by(
        DetalleVentaCero.marca,
        DetalleVentaCero.producto,
        DetalleVentaCero.cadena,
    ).limit(1000).all()

    registros_por_marca = defaultdict(list)
    for r in registros:
        registros_por_marca[r.marca or "OTRA"].append(r)

    orden = ["FAGE", "LIFEWAY", "CALIFIA", "FORAGER", "OTRA"]
    registros_por_marca = {
        k: registros_por_marca[k]
        for k in orden
        if k in registros_por_marca
    }

    total_productos = len(registros)
    ejecutados      = sum(1 for r in registros if r.ejecutada)
    pendientes      = total_productos - ejecutados
    inv_total       = sum(float(r.inventario or 0) for r in registros)
    pdvs_afectados  = len(set(r.punto_venta_id for r in registros))

    marcas_disp  = ["FAGE", "LIFEWAY", "CALIFIA", "FORAGER", "OTRA"]
    cadenas_disp = sorted(set(
        r.cadena for r in db.query(DetalleVentaCero.cadena).distinct() if r.cadena
    ))

    return templates.TemplateResponse(
        request=request,
        name="reportes/venta_cero.html",
        context={
            "registros_por_marca": registros_por_marca,
            "fecha_ini": fecha_ini, "fecha_fin": fecha_fin,
            "marca": marca or "todas", "cadena": cadena or "todas",
            "marcas_disp": marcas_disp, "cadenas_disp": cadenas_disp,
            "total_productos": total_productos, "ejecutados": ejecutados,
            "pendientes": pendientes, "inv_total": inv_total,
            "pdvs_afectados": pdvs_afectados,
            "catalogo": "reporte-venta-cero",
        },
    )