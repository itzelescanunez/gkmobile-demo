from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from decimal import Decimal


class EjecucionMarcaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    nombre_marca:     Optional[str]    = None
    fecha:            Optional[datetime] = None
    user_real_name:   Optional[str]    = None
    supervisor:       Optional[str]    = None
    cant_sku:         Optional[int]    = None
    cant_agotados:    Optional[int]    = None
    cant_preagotados: Optional[int]    = None
    con_agotados:     Optional[bool]   = None
    con_preagotados:  Optional[bool]   = None
    planograma:       Optional[bool]   = None
    is_degustacion:   Optional[bool]   = None
    caducidad:        Optional[bool]   = None
    retiro:           Optional[bool]   = None
    punto_venta_id:   Optional[int]    = None
    cadena_id:        Optional[int]    = None
    status:           Optional[bool]   = None


class EjecucionPdvSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    fecha:            Optional[datetime] = None
    user_real_name:   Optional[str]    = None
    supervisor:       Optional[str]    = None
    acomodo:          Optional[bool]   = None
    incidencias:      Optional[str]    = None
    is_degustacion:   Optional[bool]   = None
    material_degus:   Optional[str]    = None
    piezas_degus:     Optional[int]    = None
    sepresento:       Optional[bool]   = None
    sedespidio:       Optional[bool]   = None
    telson:           Optional[bool]   = None
    punto_venta_id:   Optional[int]    = None
    cadena_id:        Optional[int]    = None
    status:           Optional[bool]   = None


class AuditoriaMarcaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    fecha:            Optional[datetime] = None
    nombre_marca:     Optional[str]    = None
    user_real_name:   Optional[str]    = None
    supervisor:       Optional[str]    = None
    cumple_reportado: Optional[bool]   = None
    planograma:       Optional[bool]   = None
    is_degustacion:   Optional[bool]   = None
    punto_venta_id:   Optional[int]    = None
    cadena_id:        Optional[int]    = None
    marca_id:         Optional[int]    = None
    status:           Optional[bool]   = None


class PreciosSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    fecha:            Optional[datetime]  = None
    user_real_name:   Optional[str]       = None
    supervisor:       Optional[str]       = None
    precio:           Optional[Decimal]   = None
    is_propio:        Optional[bool]      = None
    producto_id:      Optional[int]       = None
    categoria_id:     Optional[int]       = None
    punto_venta_id:   Optional[int]       = None
    cadena_id:        Optional[int]       = None
    status:           Optional[bool]      = None


class CompetenciaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    fecha:            Optional[datetime] = None
    user_real_name:   Optional[str]    = None
    supervisor:       Optional[str]    = None
    marca:            Optional[str]    = None
    precio_obs:       Optional[str]    = None
    tipo_promo:       Optional[str]    = None
    desc_promo:       Optional[str]    = None
    frentes:          Optional[str]    = None
    comentario:       Optional[str]    = None
    punto_venta_id:   Optional[int]    = None
    cadena_id:        Optional[int]    = None
    status:           Optional[bool]   = None

