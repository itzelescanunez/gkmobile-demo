import os
from pathlib import Path
from huggingface_hub import HfApi
import toml

# Leer token desde secrets.toml
secrets = toml.load(".streamlit/secrets.toml")
token      = secrets["HF_TOKEN"]
dataset_id = secrets["HF_DATASET"]

api = HfApi()

PARQUET_DIR = Path("data/parquet")

print(f"Subiendo parquets a {dataset_id}...\n")

for archivo in sorted(PARQUET_DIR.rglob("*.parquet")):
    ruta_relativa = archivo.relative_to(PARQUET_DIR)
    print(f"  Subiendo {ruta_relativa} ({archivo.stat().st_size / 1_048_576:.1f} MB)...")
    api.upload_file(
        path_or_fileobj=str(archivo),
        path_in_repo=str(ruta_relativa),
        repo_id=dataset_id,
        repo_type="dataset",
        token=token,
    )
    print(f"  ✅ {ruta_relativa}")

print("\n✅ Todos los parquets subidos.")