
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS, Nominatim
from ia_motor import consultar_ia_riesgos
from navegacion import cargar_mapa, calcular_multiples_rutas
from exportador import generar_gpx
from clima import obtener_clima

# 1. Configuración de página SIEMPRE va primero
st.set_page_config(page_title="Rutas Ciclistas ZMG", layout="wide")

# 2. Inicialización de session_state (Para evitar el NameError)
if 'rutas' not in st.session_state: st.session_state.rutas = None
if 'zonas' not in st.session_state: st.session_state.zonas = None
if 'nombres' not in st.session_state: st.session_state.nombres = None
if 'clima' not in st.session_state: st.session_state.clima = None

def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except: pass

local_css("style.css")

st.title(" CICLISTA-MOVIL")

# Carga del mapa
with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# --- Lógica de Sugerencias ---
@st.cache_data
def obtener_sugerencias(query):
    if len(query) < 3: return {}
    sugerencias = {}
    try:
        res_arc = ArcGIS(user_agent="bici_ia_gdl_pro").geocode(f"{query}, Jalisco, Mexico", exactly_one=False, limit=5, timeout=4)
        if res_arc:
            for l in res_arc:
                clave = f"📍 {l.address.replace(', Jalisco', '').replace(', MEX', '').replace(', Mexico', '').strip()}"
                if clave not in sugerencias: sugerencias[clave] = (l.latitude, l.longitude)
    except: pass
    return sugerencias

# --- Interfaz Lateral ---
st.sidebar.header(" Buscador")
q_o = st.sidebar.text_input("Origen:", "")
sug_o = obtener_sugerencias(q_o)
sel_o = st.sidebar.selectbox("Selecciona partida:", list(sug_o.keys()) if sug_o else ["Sin resultados"])

q_d = st.sidebar.text_input("Destino:", "")
sug_d = obtener_sugerencias(q_d)
sel_d = st.sidebar.selectbox("Selecciona destino:", list(sug_d.keys()) if sug_d else ["Sin resultados"])

if st.sidebar.button("Calcular Ruta Segura"):
    if sel_o in sug_o and sel_d in sug_d:
        co_o, co_d = sug_o[sel_o], sug_d[sel_d]
        
        with st.spinner("Analizando entorno..."):
            estado_clima = obtener_clima(co_o[0], co_o[1])
            zonas = consultar_ia_riesgos(sel_o, sel_d, co_o[0], co_o[1], co_d[0], co_d[1])
            
            # Guardamos en el estado
            st.session_state.clima = estado_clima
            st.session_state.zonas = zonas
            st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, zonas, estado_clima)
            st.session_state.nombres = (sel_o, sel_d)

# --- Visualización Principal ---
if st.session_state.rutas:
    # Mostramos clima
    clima = st.session_state.clima
    if clima and clima.get('lluvia'):
        st.warning(f"🌧️ Lluvia detectada: {clima['temp']}°C. Evitando zonas críticas.")
    
    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    r = st.session_state.rutas[perfil]
    
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Distancia", f"{r['dist_km']:.2f} km")
    c2.metric("Tiempo", f"{int(r['tiempo'])} min")
    c3.metric("Seguridad", r['seguridad'])

    # Mapa con ruta
    coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in r['path']]
    m = folium.Map(location=coords[0], zoom_start=14)
    folium.PolyLine(coords, color=r['color'], weight=6).add_to(m)
    folium.Marker(coords[0], popup="Inicio", icon=folium.Icon(color='green')).add_to(m)
    folium.Marker(coords[-1], popup="Fin", icon=folium.Icon(color='red')).add_to(m)
    st_folium(m, width="100%", height=500, key="mapa_con_ruta")

else:
    # Mapa Base (Vista previa de marcadores)
    st.info("Selecciona origen y destino para comenzar.")
    centro = [20.6767, -103.3475]
    if sel_o in sug_o: centro = sug_o[sel_o]
    
    m_base = folium.Map(location=centro, zoom_start=12)
    if sel_o in sug_o:
        folium.Marker(sug_o[sel_o], popup="Origen", icon=folium.Icon(color='blue')).add_to(m_base)
    if sel_d in sug_d:
        folium.Marker(sug_d[sel_d], popup="Destino", icon=folium.Icon(color='red')).add_to(m_base)
        
    st_folium(m_base, width="100%", height=500, key="mapa_inicial")
