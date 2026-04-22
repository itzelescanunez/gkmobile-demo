from sqlalchemy import Column, BigInteger, String, Integer, Numeric, Date
from api.database import Base


class ReporteMarcaPdv(Base):
    __tablename__ = "v_reporte_marca_pdv"

    # Vista — clave compuesta simulada
    pdv_id        = Column(BigInteger, primary_key=True)
    fecha         = Column(String(10),  primary_key=True)
    marca         = Column(String(255), primary_key=True)

    cadena        = Column(String(255))
    punto_venta   = Column(String(255))
    municipio     = Column(String(255))
    estado        = Column(String(255))
    anio_mes      = Column(String(7))

    total_visitas         = Column(Integer)
    cant_sku              = Column(Integer)

    cumple_planograma     = Column(Integer)
    pct_planograma        = Column(Numeric(5, 1))

    visitas_con_agotados  = Column(Integer)
    pct_visitas_agotados  = Column(Numeric(5, 1))
    cant_sku_agotados     = Column(Integer)
    pct_sku_agotados      = Column(Numeric(5, 1))

    visitas_con_preagotados = Column(Integer)
    pct_visitas_preagotados = Column(Numeric(5, 1))
    cant_sku_preagotados    = Column(Integer)
    pct_sku_preagotados     = Column(Numeric(5, 1))