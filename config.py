from pathlib import Path
import os

BASE_DIR = Path(__file__).parent

def _get_parquet_dir():
    # Leer ruta desde archivo temporal si existe
    marker = Path("/tmp/gkmobile_parquet_dir.txt")
    if marker.exists():
        return Path(marker.read_text().strip())
    return Path(os.getenv("PARQUET_DIR", str(BASE_DIR / "data/parquet")))

def parquet(nombre, cliente=None):
    PARQUET_DIR = _get_parquet_dir()
    if cliente:
        return str(PARQUET_DIR / cliente / f"{nombre}.parquet")
    for sub in ["global", "eatics", "procesa"]:
        path = PARQUET_DIR / sub / f"{nombre}.parquet"
        if path.exists():
            return str(path)
    raise FileNotFoundError(f"Parquet '{nombre}' no encontrado en {PARQUET_DIR}")

CLIENTES = {
    1:   "Philip Morris International",
    26:  "Procesa",
    102: "Castel",
    127: "Xiaomi",
    132: "Danone",
    141: "Clip",
    142: "Rabbit",
    149: "Eatics",
}

CADENAS_NORM = {
    "CHEDRAUI": "Chedraui",
    "SORIANA": "Soriana",
    "SAMS CLUB": "Sam''s Club",
    "SAMS": "Sam''s Club",
    "WALMART": "Walmart",
    "HEB": "HEB",
    "LA COMER": "La Comer",
    "COMERCIAL MEXICANA": "Comercial Mexicana",
    "ALSUPER": "Alsuper",
    "COSTCO": "Costco",
    "CASA LEY": "Casa Ley",
    "CALIMAX": "Calimax",
}

def sql_normalizar_cadena(col: str = "pv.cadena_str") -> str:
    cases = "\n".join([
        f"    WHEN UPPER(TRIM({col})) = '{k}' THEN '{v}'"
        for k, v in CADENAS_NORM.items()
    ])
    return f"""
        CASE
{cases}
            WHEN {col} IS NULL
              OR TRIM({col}) = ''
              OR UPPER(TRIM({col})) = 'NAN' THEN 'Sin cadena'
            ELSE TRIM({col})
        END
    """
