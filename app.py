import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS, Nominatim
from ia_motor import consultar_ia_riesgos
from navegacion import cargar_mapa, calcular_multiples_rutas, obtener_estaciones_mibici
from exportador import generar_gpx
from clima import obtener_clima
from generar_mapa import renderizar_mapa_pro # Usaremos la lógica de renderizado pro

# 1. Configuración de página
st.set_page_config(page_title="Rutas Ciclistas ZMG", layout="wide")

def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except: pass

local_css("style.css")

st.title("🚴 CICLISTA-MOVIL")

# 2. Inicialización de session_state y Mapa
with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# Inicialización de todas las llaves necesarias
for key in ['rutas', 'zonas', 'nombres', 'clima', 'coord_o', 'coord_d']:
    if key not in st.session_state: st.session_state[key] = None

# --- Lógica de Sugerencias Robusta ---
@st.cache_data(ttl=3600)
def obtener_sugerencias(query):
    if not query or len(query) < 3: return {}
    sugerencias = {}
    try:
        res_arc = ArcGIS(user_agent="bici_ia_gdl_pro_v3").geocode(f"{query}, Jalisco, Mexico", exactly_one=False, limit=5, timeout=4)
        if res_arc:
            for l in res_arc:
                clave = f"📍 {l.address.replace(', Jalisco', '').replace(', MEX', '').replace(', Mexico', '').strip()}"
                if clave not in sugerencias: sugerencias[clave] = (l.latitude, l.longitude)
    except: pass
    return sugerencias

# --- Interfaz Lateral ---
st.sidebar.header("🔍 Buscador")
q_o = st.sidebar.text_input("Origen (Escribe y Enter):", "", key="txt_origen")
sug_o = obtener_sugerencias(q_o)
sel_o = st.sidebar.selectbox("Selecciona punto de partida:", list(sug_o.keys()) if sug_o else ["Sin resultados"], key="sb_origen")

q_d = st.sidebar.text_input("Destino (Escribe y Enter):", "", key="txt_destino")
sug_d = obtener_sugerencias(q_d)
sel_d = st.sidebar.selectbox("Selecciona destino:", list(sug_d.keys()) if sug_d else ["Sin resultados"], key="sb_destino")

# Guardar coordenadas en estado para evitar pérdida en recarga
if sel_o in sug_o: st.session_state.coord_o = sug_o[sel_o]
if sel_d in sug_d: st.session_state.coord_d = sug_d[sel_d]

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Capas del Mapa")
ver_mibici = st.sidebar.toggle("Mostrar Estaciones MiBici", value=False)
ver_talleres = st.sidebar.toggle("Mostrar Talleres Cercanos", value=False)

if st.sidebar.button("🚀 Calcular Ruta Segura"):
    if st.session_state.coord_o and st.session_state.coord_d:
        co_o, co_d = st.session_state.coord_o, st.session_state.coord_d
        
        with st.spinner("Consultando clima real..."):
            st.session_state.clima = obtener_clima(co_o[0], co_o[1])
            
        with st.spinner("IA analizando peligros..."):
            zonas = consultar_ia_riesgos(sel_o, sel_d, co_o[0], co_o[1], co_d[0], co_d[1])
            st.session_state.zonas = zonas
            
        with st.spinner("Trazando rutas seguras..."):
            st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, zonas, st.session_state.clima)
            st.session_state.nombres = (sel_o, sel_d)
    else:
        st.sidebar.error("Selecciona puntos válidos de la lista.")

# --- Sección de Exportación (Solo si hay ruta) ---
if st.session_state.rutas:
    st.sidebar.markdown("---")
    st.sidebar.subheader("💾 Exportar")
    perfil_export = list(st.session_state.rutas.keys())[1] # Inteligente por defecto
    ruta_data = st.session_state.rutas[perfil_export]
    coords_gpx = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in ruta_data['path']]
    
    st.sidebar.download_button(
        label="Descargar Ruta (GPX)",
        data=generar_gpx(coords_gpx, perfil_export),
        file_name=f"ruta_ciclista.gpx",
        mime="application/gpx+xml",
        use_container_width=True
    )

# --- Visualización Principal ---
ruta_activa = None

if st.session_state.rutas:
    clima = st.session_state.clima
    if clima:
        if clima['lluvia']:
            st.warning(f"🌧️ **Atención:** Lluvia detectada ({clima['temp']}°C). Rutas ajustadas para evitar fango/empedrado.")
        else:
            st.success(f"☀️ **Clima favorable:** {clima['descripcion']} | {clima.get('temp', '--')}°C.")

    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    ruta_activa = st.session_state.rutas[perfil]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📏 Distancia", f"{ruta_activa['dist_km']:.2f} km")
    c2.metric("⏱️ Tiempo", f"{int(ruta_activa['tiempo'])} min")
    c3.metric("🛡️ Seguridad", ruta_activa['seguridad'])
else:
    st.info("👋 Selecciona origen y destino para comenzar o activa las capas de MiBici/Talleres.")

# --- RENDERIZADO DEL MAPA ---
# Usamos la lógica de renderizar_mapa_pro pero integrada para soportar las capas originales
m = renderizar_mapa_pro(G, ruta_activa, st.session_state.zonas, ver_mibici, ver_talleres)

# Añadimos las capas extra que tenías en el original
folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                 attr='Esri', name='🛰️ Satélite Realista', show=False).add_to(m)
folium.TileLayer('cartodbdark_matter', name='🌙 Modo Oscuro', show=False).add_to(m)
folium.LayerControl(position='topright').add_to(m)

# Mostrar el mapa
st_folium(m, width="100%", height=550, key="mapa_ciclista_pro")

# --- Indicaciones Paso a Paso ---
if ruta_activa:
    with st.expander("📋 Ver indicaciones paso a paso"):
        instrucciones = ruta_activa.get('instrucciones', [])
        if instrucciones:
            for i, instruccion in enumerate(instrucciones):
                st.markdown(f"**{i+1}.** {instruccion}")
        else:
            st.info("No se encontraron nombres de calles detallados.")
