import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS, Nominatim
from ia_motor import consultar_ia_riesgos
from navegacion import cargar_mapa, calcular_multiples_rutas, obtener_estaciones_mibici
from exportador import generar_gpx
from clima import obtener_clima

st.set_page_config(page_title="Rutas Ciclistas ZMG", layout="wide")

if 'rutas' not in st.session_state: st.session_state.rutas = None
if 'zonas' not in st.session_state: st.session_state.zonas = None

st.title("🚴 CICLISTA-MOVIL")

with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# --- Interfaz Lateral ---
st.sidebar.header("🔍 Buscador")
# (Aquí va tu lógica de buscador ArcGIS/Nominatim original)

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Capas del Mapa")
ver_mibici = st.sidebar.toggle("Mostrar Estaciones MiBici", value=False)
ver_talleres = st.sidebar.toggle("Mostrar Talleres Cercanos", value=False)

# --- Botón de Cálculo ---
if st.sidebar.button("🚀 Calcular Ruta Segura"):
    # (Aquí va tu lógica de cálculo que ya tienes)
    st.session_state.rutas = calcular_multiples_rutas(G, (20.67, -103.34), (20.62, -103.24), [], {}) # Ejemplo

# --- Lógica de Visualización Principal ---
if st.session_state.rutas:
    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    r = st.session_state.rutas[perfil]
    
    # IMPORTANTE: Pasamos los estados de los toggles al renderizado
    from generar_mapa import renderizar_mapa_pro
    m = renderizar_mapa_pro(G, r, st.session_state.zonas, ver_mibici, ver_talleres)
    st_folium(m, width="100%", height=550)
