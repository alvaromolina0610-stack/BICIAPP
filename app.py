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

# Mantenemos tus estilos originales
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except: pass

local_css("style.css")

st.title("🚴 CICLISTA-MOVIL")

with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# --- INICIALIZACIÓN DE MEMORIA ---
# Añadimos llaves específicas para 'congelar' los puntos seleccionados
for key in ['rutas', 'zonas', 'nombres', 'clima', 'puntos_confirmados']:
    if key not in st.session_state: st.session_state[key] = None
if 'puntos_confirmados' not in st.session_state or st.session_state.puntos_confirmados is None:
    st.session_state.puntos_confirmados = {'origen': None, 'destino': None}

@st.cache_data(ttl=3600)
def obtener_sugerencias(query):
    if not query or len(query) < 3: return {}
    sugerencias = {}
    try:
        # User Agent único para evitar bloqueos del servidor ArcGIS
        res_arc = ArcGIS(user_agent="bici_ia_tonala_v4").geocode(
            f"{query}, Jalisco, Mexico", exactly_one=False, limit=5, timeout=5
        )
        if res_arc:
            for l in res_arc:
                clave = f"📍 {l.address.split(', Jalisco')[0].strip()}"
                sugerencias[clave] = (l.latitude, l.longitude)
    except: pass
    return sugerencias

# --- INTERFAZ LATERAL ---
st.sidebar.header("🔍 Buscador")

# Lógica de Origen
q_o = st.sidebar.text_input("Origen (ej. Akron):", key="in_origen")
sug_o = obtener_sugerencias(q_o)
sel_o = st.sidebar.selectbox("Selecciona partida:", list(sug_o.keys()) if sug_o else ["Sin resultados"], key="sel_origen")

# Lógica de Destino
q_d = st.sidebar.text_input("Destino (ej. CUTonalá):", key="in_destino")
sug_d = obtener_sugerencias(q_d)
sel_d = st.sidebar.selectbox("Selecciona destino:", list(sug_d.keys()) if sug_d else ["Sin resultados"], key="sel_destino")

# --- PUENTE DE VALIDACIÓN ---
# Actualizamos los puntos confirmados solo si la selección es válida
if sel_o in sug_o:
    st.session_state.puntos_confirmados['origen'] = sug_o[sel_o]
if sel_d in sug_d:
    st.session_state.puntos_confirmados['destino'] = sug_d[sel_d]

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Capas del Mapa")
ver_mibici = st.sidebar.toggle("Mostrar Estaciones MiBici", value=False)
ver_talleres = st.sidebar.toggle("Mostrar Talleres Cercanos", value=False)

# --- BOTÓN DE CÁLCULO REFORZADO ---
if st.sidebar.button("🚀 Calcular Ruta Segura"):
    # Verificamos que los puntos confirmados existan en la memoria de la sesión
    pts = st.session_state.puntos_confirmados
    if pts['origen'] and pts['destino']:
        with st.spinner("Analizando entorno y riesgos..."):
            co_o, co_d = pts['origen'], pts['destino']
            
            st.session_state.clima = obtener_clima(co_o[0], co_o[1])
            st.session_state.nombres = (sel_o, sel_d)
            
            # Llamada al motor matemático
            zonas_ia = consultar_ia_riesgos(sel_o, sel_d, co_o[0], co_o[1], co_d[0], co_d[1])
            st.session_state.zonas = zonas_ia
            st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, zonas_ia, st.session_state.clima)
    else:
        st.sidebar.error("Asegúrate de que ambos destinos muestren una dirección válida en el buscador.")

# --- RENDERIZADO Y EXPORTACIÓN ---
ruta_activa = None
if st.session_state.rutas:
    # (Tu lógica original de GPX, métricas y radio botones)
    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    ruta_activa = st.session_state.rutas[perfil]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📏 Distancia", f"{ruta_activa['dist_km']:.2f} km")
    c2.metric("⏱️ Tiempo", f"{int(ruta_activa['tiempo'])} min")
    c3.metric("🛡️ Seguridad", ruta_activa['seguridad'])
else:
    st.info("👋 Selecciona origen y destino para comenzar.")

# Renderizado final usando tu lógica unificada
m = renderizar_mapa_pro(G, ruta_activa, st.session_state.zonas, ver_mibici, ver_talleres)

# Capas extra del original
folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                 attr='Esri', name='🛰️ Satélite Realista', show=False).add_to(m)
folium.LayerControl(position='topright').add_to(m)

st_folium(m, width="100%", height=550, key="mapa_final_zmg")
