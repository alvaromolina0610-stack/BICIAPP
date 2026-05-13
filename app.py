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

# 2. Inicialización de session_state mejorada
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

st.title("🚴 CICLISTA-MOVIL")

# Carga del mapa con caché de recurso
with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# --- Lógica de Sugerencias Mejorada ---
@st.cache_data(ttl=3600)
def obtener_sugerencias(query):
    if not query or len(query) < 3: return {}
    sugerencias = {}
    
    # Intento 1: ArcGIS (Más rápido y preciso para direcciones en México)
    try:
        # Cambiamos el user_agent para evitar bloqueos
        res_arc = ArcGIS(user_agent="ciclista_movil_zmg_v2").geocode(
            f"{query}, Jalisco, Mexico", 
            exactly_one=False, 
            limit=5, 
            timeout=5
        )
        if res_arc:
            for l in res_arc:
                clave = f"📍 {l.address.split(', Jalisco')[0].strip()}"
                if clave not in sugerencias: sugerencias[clave] = (l.latitude, l.longitude)
    except: pass

    # Intento 2: Nominatim (Respaldo si ArcGIS no encuentra puntos específicos)
    if len(sugerencias) < 2:
        try:
            res_osm = Nominatim(user_agent="ciclista_movil_backup").geocode(
                f"{query}, Guadalajara", 
                exactly_one=False, 
                limit=3, 
                timeout=5
            )
            if res_osm:
                for l in res_osm:
                    nombre = f"🏢 {l.address.split(',')[0].strip()}"
                    if nombre not in sugerencias: sugerencias[nombre] = (l.latitude, l.longitude)
        except: pass
        
    return sugerencias

# --- Interfaz Lateral ---
st.sidebar.header("🔍 Buscador")
q_o = st.sidebar.text_input("Origen (Escribe y presiona Enter):", "")
sug_o = obtener_sugerencias(q_o)
sel_o = st.sidebar.selectbox("Selecciona partida:", list(sug_o.keys()) if sug_o else ["Sin resultados"])

q_d = st.sidebar.text_input("Destino (Escribe y presiona Enter):", "")
sug_d = obtener_sugerencias(q_d)
sel_d = st.sidebar.selectbox("Selecciona destino:", list(sug_d.keys()) if sug_d else ["Sin resultados"])

if st.sidebar.button("🚀 Calcular Ruta Segura"):
    if sel_o in sug_o and sel_d in sug_d:
        co_o, co_d = sug_o[sel_o], sug_d[sel_d]
        
        with st.spinner("Analizando entorno y riesgos..."):
            # Obtenemos clima y riesgos
            estado_clima = obtener_clima(co_o[0], co_o[1])
            zonas = consultar_ia_riesgos(sel_o, sel_d, co_o[0], co_o[1], co_d[0], co_d[1])
            
            # Guardamos todo en session_state para persistencia
            st.session_state.clima = estado_clima
            st.session_state.zonas = zonas
            st.session_state.nombres = (sel_o, sel_d)
            st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, zonas, estado_clima)
    else:
        st.sidebar.error("Asegúrate de seleccionar puntos válidos de las listas.")

# --- Visualización Principal ---
if st.session_state.rutas:
    # Información del clima
    clima = st.session_state.clima
    if clima:
        if clima.get('lluvia'):
            st.warning(f"⚠️ **Atención:** Lluvia detectada ({clima['temp']}°C). Se priorizan rutas con mejor drenaje.")
        else:
            st.info(f"🌤️ **Clima:** {clima.get('descripcion', 'Despejado')} | {clima.get('temp', '--')}°C")
    
    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    r = st.session_state.rutas[perfil]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📏 Distancia", f"{r['dist_km']:.2f} km")
    c2.metric("⏱️ Tiempo est.", f"{int(r['tiempo'])} min")
    c3.metric("🛡️ Seguridad", r['seguridad'])

    # Mapa con la ruta trazada
    coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in r['path']]
    m = folium.Map(location=coords[0], zoom_start=14)
    folium.TileLayer('openstreetmap').add_to(m)
    
    # Dibujar zonas de riesgo detectadas por IA
    if st.session_state.zonas:
        for z in st.session_state.zonas:
            folium.Circle(
                [z['lat'], z['lon']], 
                radius=z['radio']*1000, 
                color='red', 
                fill=True, 
                fill_opacity=0.2
            ).add_to(m)

    folium.PolyLine(coords, color=r['color'], weight=6, opacity=0.8).add_to(m)
    folium.Marker(coords[0], popup=st.session_state.nombres[0], icon=folium.Icon(color='green', icon='play')).add_to(m)
    folium.Marker(coords[-1], popup=st.session_state.nombres[1], icon=folium.Icon(color='red', icon='flag')).add_to(m)
    
    st_folium(m, width="100%", height=550, key="mapa_con_ruta")

else:
    # Mapa Base (Vista previa dinámica antes de calcular)
    st.info("👋 ¡Bienvenido! Selecciona un origen y destino en el buscador lateral para comenzar.")
    
    # Centrado inteligente del mapa base
    if sel_o in sug_o and sel_d in sug_d:
        centro = [(sug_o[sel_o][0] + sug_d[sel_d][0])/2, (sug_o[sel_o][1] + sug_d[sel_d][1])/2]
        zoom = 12
    elif sel_o in sug_o:
        centro = sug_o[sel_o]
        zoom = 15
    else:
        centro = [20.6767, -103.3475] # Guadalajara Centro
        zoom = 12
    
    m_base = folium.Map(location=centro, zoom_start=zoom)
    if sel_o in sug_o:
        folium.Marker(sug_o[sel_o], popup="Origen", icon=folium.Icon(color='blue')).add_to(m_base)
    if sel_d in sug_d:
        folium.Marker(sug_d[sel_d], popup="Destino", icon=folium.Icon(color='red')).add_to(m_base)
        
    st_folium(m_base, width="100%", height=550, key="mapa_inicial")
