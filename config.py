from pathlib import Path
import os

BASE_DIR    = Path(__file__).parent
PARQUET_DIR = Path(os.getenv("PARQUET_DIR", str(BASE_DIR / "data/parquet")))

def parquet(nombre, cliente=None):
    if cliente:
        return str(PARQUET_DIR / cliente / f"{nombre}.parquet")
    for sub in ["global", "eatics", "procesa"]:
        path = PARQUET_DIR / sub / f"{nombre}.parquet"
        if path.exists():
            return str(path)
    raise FileNotFoundError(f"Parquet '{nombre}' no encontrado")

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