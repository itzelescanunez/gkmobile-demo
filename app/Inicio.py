import path_setup
import streamlit as st

pg = st.navigation([
    st.Page("pages/1_Operacion_Global.py", title="Operación Global", icon="📊", default=True),
    st.Page("pages/2_Monitor_Geo.py",      title="Monitor Geo",      icon="📍"),
    st.Page("pages/3_Inicio_Eatics.py",    title="Eatics Dashboard", icon="🛒"),
    st.Page("pages/4_Procesa_SellOut.py",    title="Procesa Sell Out", icon="📦"),
])

pg.run()
