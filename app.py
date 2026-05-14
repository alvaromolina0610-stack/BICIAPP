
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

# 1. ESTILOS Y MAPA
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except: pass

local_css("style.css")

with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# 2. SISTEMA DE MEMORIA "BLINDADA"
# Inicializamos el estado si es la primera vez que carga la app
if 'puntos' not in st.session_state:
    st.session_state.puntos = {"origen": None, "destino": None, "nombres": (None, None)}
if 'rutas' not in st.session_state:
    st.session_state.rutas = None
if 'zonas' not in st.session_state:
    st.session_state.zonas = None

@st.cache_data(ttl=3600)
def obtener_sugerencias(query):
    if not query or len(query) < 3: return {}
    sugerencias = {}
    try:
        # Cambiamos el User Agent para asegurar conexión limpia
        geolocator = ArcGIS(user_agent="ciclista_movil_zmg_final_v5")
        res = geolocator.geocode(f"{query}, Jalisco, Mexico", exactly_one=False, limit=5, timeout=5)
        if res:
            for l in res:
                clave = f"📍 {l.address.split(', Jalisco')[0].strip()}"
                sugerencias[clave] = (l.latitude, l.longitude)
    except: pass
    return sugerencias

# --- INTERFAZ LATERAL ---
st.sidebar.header("🔍 Buscador")

# Lógica de Origen con persistencia inmediata
q_o = st.sidebar.text_input("Origen (ej. Akron):", key="txt_o")
sug_o = obtener_sugerencias(q_o)
sel_o = st.sidebar.selectbox("Selecciona punto de partida:", list(sug_o.keys()) if sug_o else ["Sin resultados"], key="sb_o")

# Lógica de Destino con persistencia inmediata
q_d = st.sidebar.text_input("Destino (ej. CUTonalá):", key="txt_d")
sug_d = obtener_sugerencias(q_d)
sel_d = st.sidebar.selectbox("Selecciona punto de destino:", list(sug_d.keys()) if sug_d else ["Sin resultados"], key="sb_d")

# GUARDADO FORZADO EN MEMORIA (Antes del botón)
if sel_o in sug_o:
    st.session_state.puntos["origen"] = sug_o[sel_o]
    st.session_state.puntos["nombres"] = (sel_o, st.session_state.puntos["nombres"][1])
if sel_d in sug_d:
    st.session_state.puntos["destino"] = sug_d[sel_d]
    st.session_state.puntos["nombres"] = (st.session_state.puntos["nombres"][0], sel_d)

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Capas del Mapa")
ver_mibici = st.sidebar.toggle("Mostrar Estaciones MiBici", value=False)
ver_talleres = st.sidebar.toggle("Mostrar Talleres Cercanos", value=False)

# --- BOTÓN DE CÁLCULO (Usa la memoria, no los widgets directamente) ---
if st.sidebar.button("🚀 Calcular Ruta Segura"):
    p = st.session_state.puntos
    if p["origen"] and p["destino"]:
        with st.spinner("Analizando entorno y riesgos..."):
            co_o, co_d = p["origen"], p["destino"]
            
            # 1. Clima
            clima = obtener_clima(co_o[0], co_o[1])
            st.session_state.clima = clima
            
            # 2. Riesgos IA
            zonas = consultar_ia_riesgos(p["nombres"][0], p["nombres"][1], co_o[0], co_o[1], co_d[0], co_d[1])
            st.session_state.zonas = zonas
            
            # 3. Rutas
            st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, zonas, clima)
            st.session_state.nombres = p["nombres"]
    else:
        st.sidebar.error("⚠️ Selecciona ubicaciones válidas de las listas antes de calcular.")

# --- RENDERIZADO Y MAPA ---
ruta_activa = None
if st.session_state.rutas:
    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    ruta_activa = st.session_state.rutas[perfil]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📏 Distancia", f"{ruta_activa['dist_km']:.2f} km")
    c2.metric("⏱️ Tiempo", f"{int(ruta_activa['tiempo'])} min")
    c3.metric("🛡️ Seguridad", ruta_activa['seguridad'])
else:
    st.info("👋 Ingresa origen y destino para trazar la ruta.")

# El mapa siempre se renderiza al final para capturar cualquier cambio de estado
m = renderizar_mapa_pro(G, ruta_activa, st.session_state.zonas, ver_mibici, ver_talleres)

# Capas originales
folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                 attr='Esri', name='🛰️ Satélite Realista', show=False).add_to(m)
folium.LayerControl(position='topright').add_to(m)

st_folium(m, width="100%", height=550, key="mapa_final_definitivo")
