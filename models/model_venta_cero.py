from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, Boolean
from api.database import Base


class DetalleVentaCero(Base):
    __tablename__ = "v_detalle_venta_cero"

    # Clave compuesta simulada para la vista
    punto_venta_id = Column(BigInteger, primary_key=True)
    producto       = Column(String(255), primary_key=True)

    punto_venta    = Column(String(255))
    municipio      = Column(String(255))
    estado         = Column(String(255))
    cadena         = Column(String(255))
    marca          = Column(String(255))
    inventario     = Column(Numeric(19, 2))
    ejecutada      = Column(Boolean)
    fecha          = Column(DateTime)
    anio_mes       = Column(String(7))
    promotor       = Column(String(255))
    supervisor     = Column(String(255))
    upc            = Column(String(255))