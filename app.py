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
if 'nombres' not in st.session_state: st.session_state.nombres = None
if 'clima' not in st.session_state: st.session_state.clima = None

st.title("🚴 CICLISTA-MOVIL")

with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# --- Lógica de Sugerencias (Tu código original restaurado) ---
@st.cache_data(ttl=3600)
def obtener_sugerencias(query):
    if not query or len(query) < 3: return {}
    sugerencias = {}
    try:
        res_arc = ArcGIS(user_agent="ciclista_movil_v2").geocode(
            f"{query}, Jalisco, Mexico", exactly_one=False, limit=5, timeout=5
        )
        if res_arc:
            for l in res_arc:
                clave = f"📍 {l.address.split(', Jalisco')[0].strip()}"
                if clave not in sugerencias: sugerencias[clave] = (l.latitude, l.longitude)
    except: pass
    return sugerencias

# --- Interfaz Lateral ---
st.sidebar.header("🔍 Buscador")
q_o = st.sidebar.text_input("Origen:", "")
sug_o = obtener_sugerencias(q_o)
sel_o = st.sidebar.selectbox("Selecciona partida:", list(sug_o.keys()) if sug_o else ["Sin resultados"])

q_d = st.sidebar.text_input("Destino:", "")
sug_d = obtener_sugerencias(q_d)
sel_d = st.sidebar.selectbox("Selecciona destino:", list(sug_d.keys()) if sug_d else ["Sin resultados"])

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Capas del Mapa")
ver_mibici = st.sidebar.toggle("Mostrar Estaciones MiBici", value=False)
ver_talleres = st.sidebar.toggle("Mostrar Talleres Cercanos", value=False)

if st.sidebar.button("🚀 Calcular Ruta Segura"):
    if sel_o in sug_o and sel_d in sug_d:
        co_o, co_d = sug_o[sel_o], sug_d[sel_d]
        with st.spinner("Calculando mejor ruta..."):
            st.session_state.clima = obtener_clima(co_o[0], co_o[1])
            st.session_state.nombres = (sel_o, sel_d)
            st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, [], st.session_state.clima)
    else:
        st.sidebar.error("Selecciona puntos válidos.")

# --- Renderizado ---
ruta_activa = None
if st.session_state.rutas:
    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    ruta_activa = st.session_state.rutas[perfil]
else:
    st.info("👋 ¡Bienvenido! Selecciona un origen y destino para comenzar.")

m = renderizar_mapa_pro(G, ruta_activa, st.session_state.zonas, ver_mibici, ver_talleres)
st_folium(m, width="100%", height=550, key="mapa_principal")
