import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

# ── Descarga parquets desde HF y escribe ruta a /tmp ──
hf_token   = st.secrets.get("HF_TOKEN")
hf_dataset = st.secrets.get("HF_DATASET")

if hf_token and hf_dataset:
    cache_dir = Path("/tmp/gkmobile_parquets")
    marker    = Path("/tmp/gkmobile_parquets/.ready")

    if not marker.exists():
        with st.spinner("Descargando datos... esto puede tardar unos minutos."):
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=hf_dataset,
                repo_type="dataset",
                token=hf_token,
                local_dir=str(cache_dir),
                ignore_patterns=["*.md", ".gitattributes"],
            )
            marker.touch()

    # Escribir ruta a archivo para que config.py la lea
    Path("/tmp/gkmobile_parquet_dir.txt").write_text(str(cache_dir))

from app.auth import check_password
check_password()

pg = st.navigation([
    st.Page("pages/1_Operacion_Global.py", title="Operación Global", icon="📊", default=True),
    st.Page("pages/2_Monitor_Geo.py",      title="Monitor Geo",      icon="📍"),
    st.Page("pages/3_Inicio_Eatics.py",    title="Eatics Dashboard", icon="🛒"),
    st.Page("pages/4_Procesa_SellOut.py",  title="Procesa Sell Out", icon="📦"),
])
pg.run()
