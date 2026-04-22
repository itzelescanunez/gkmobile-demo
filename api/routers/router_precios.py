from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from collections import defaultdict

from api.database import SessionLocal
from models.model_precios_agotados import PreciosEatics, AgotadosConProducto

router_precios = APIRouter(prefix="/eatics", tags=["Precios"])
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router_precios.get("/precios", response_class=HTMLResponse)
def vista_precios(
        request: Request,
        fecha_ini: Optional[str] = None,
        fecha_fin: Optional[str] = None,
        cadena: Optional[str] = None,
        q: Optional[str] = None,
        tipo: Optional[str] = None,
        db: Session = Depends(get_db),
):
    if not fecha_ini:
        hoy = date.today()
        fecha_ini = hoy.replace(day=1).strftime("%Y-%m-%d")
    if not fecha_fin:
        fecha_fin = date.today().strftime("%Y-%m-%d")

    query = db.query(PreciosEatics).filter(
        PreciosEatics.fecha >= fecha_ini,
        PreciosEatics.fecha <= fecha_fin,
        PreciosEatics.status == True,
        )

    if cadena and cadena != "todas":
        query = query.filter(PreciosEatics.cadena == cadena)
    if q:
        query = query.filter(PreciosEatics.producto.ilike(f"%{q}%"))
    if tipo == "propio":
        query = query.filter(PreciosEatics.is_propio == True)
    elif tipo == "competencia":
        query = query.filter(PreciosEatics.is_propio == False)

    registros = query.order_by(
        PreciosEatics.producto,
        PreciosEatics.cadena,
        PreciosEatics.fecha.desc(),
    ).limit(500).all()

# Normalizar is_propio a bool limpio
    for r in registros:
        r.is_propio = int(r.is_propio or 0) == 1

    total       = len(registros)
    propios     = sum(1 for r in registros if r.is_propio)
    competencia = total - propios

    cadenas_disp = sorted(set(
        r.cadena for r in db.query(PreciosEatics.cadena).distinct() if r.cadena
    ))

    return templates.TemplateResponse(
        request=request,
        name="eatics/precios_list.html",
        context={
            "registros": registros,
            "fecha_ini": fecha_ini, "fecha_fin": fecha_fin,
            "cadena": cadena or "todas", "q": q or "",
            "tipo": tipo or "todos",
            "cadenas_disp": cadenas_disp,
            "total": total, "propios": propios, "competencia": competencia,
            "catalogo": "precios",
        },
    )