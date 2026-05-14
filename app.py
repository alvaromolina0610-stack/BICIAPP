import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS, Nominatim
from ia_motor import consultar_ia_riesgos
from navegacion import cargar_mapa, calcular_multiples_rutas, obtener_estaciones_mibici
from exportador import generar_gpx
from clima import obtener_clima
from generar_mapa import renderizar_mapa_pro

st.set_page_config(page_title="Rutas Ciclistas ZMG", layout="wide")

if 'rutas' not in st.session_state: st.session_state.rutas = None
if 'zonas' not in st.session_state: st.session_state.zonas = None

st.title("🚴 CICLISTA-MOVIL")

with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# --- Interfaz Lateral ---
st.sidebar.header("🔍 Buscador")
# (Aquí mantienes tus inputs q_o, sel_o, q_d, sel_d y la lógica de obtener_sugerencias)

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Capas del Mapa")
ver_mibici = st.sidebar.toggle("Mostrar Estaciones MiBici", value=False)
ver_talleres = st.sidebar.toggle("Mostrar Talleres Cercanos", value=False)

# --- Botón de Cálculo ---
if st.sidebar.button("🚀 Calcular Ruta Segura"):
    # Sustituye estas coordenadas de ejemplo por tus sel_o y sel_d reales
    # co_o, co_d = sug_o[sel_o], sug_d[sel_d]
    # st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, [], {})
    st.session_state.rutas = calcular_multiples_rutas(G, (20.67, -103.34), (20.62, -103.24), [], {}) 

# --- Lógica de Visualización Principal ---

# 1. Si hay rutas, mostramos el selector de perfil arriba del mapa
ruta_para_renderizar = None
if st.session_state.rutas:
    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    ruta_para_renderizar = st.session_state.rutas[perfil]
else:
    st.info("👋 ¡Bienvenido! Selecciona un origen y destino para comenzar o activa las capas laterales.")

# 2. Renderizado del Mapa (Siempre visible)
m = renderizar_mapa_pro(
    G, 
    ruta_para_renderizar, 
    st.session_state.zonas, 
    ver_mibici, 
    ver_talleres
)

# Mostramos el mapa. Usamos una key diferente para que Streamlit detecte el cambio de estado.
st_folium(m, width="100%", height=550, key="mapa_principal")
