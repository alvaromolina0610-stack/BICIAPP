import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS, Nominatim
from ia_motor import consultar_ia_riesgos
from navegacion import cargar_mapa, calcular_multiples_rutas, obtener_estaciones_mibici
from exportador import generar_gpx
from clima import obtener_clima
from generar_mapa import renderizar_mapa_pro

# 1. Configuración de página
st.set_page_config(page_title="Rutas Ciclistas ZMG", layout="wide")

# 2. Inicialización de session_state
if 'rutas' not in st.session_state: st.session_state.rutas = None
if 'zonas' not in st.session_state: st.session_state.zonas = None
if 'nombres' not in st.session_state: st.session_state.nombres = None
if 'clima' not in st.session_state: st.session_state.clima = None
# Estados para las coordenadas seleccionadas
if 'coord_o' not in st.session_state: st.session_state.coord_o = None
if 'coord_d' not in st.session_state: st.session_state.coord_d = None

st.title("🚴 CICLISTA-MOVIL")

with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# --- Lógica de Sugerencias Mejorada ---
@st.cache_data(ttl=3600)
def obtener_sugerencias(query):
    if not query or len(query) < 3: return {}
    sugerencias = {}
    try:
        # Cambiamos el user_agent por uno único para evitar bloqueos
        geolocator = ArcGIS(user_agent="ciclista_movil_zmg_alvaro_v3")
        res = geolocator.geocode(f"{query}, Jalisco, Mexico", exactly_one=False, limit=5, timeout=5)
        if res:
            for l in res:
                # Acortamos el nombre para que quepa bien en el selectbox
                clave = f"📍 {l.address.split(', Jalisco')[0].strip()}"
                sugerencias[clave] = (l.latitude, l.longitude)
    except:
        # Fallback a Nominatim si ArcGIS falla
        try:
            nom = Nominatim(user_agent="ciclista_movil_backup_zmg")
            res_nom = nom.geocode(f"{query}, Guadalajara", exactly_one=False, limit=3)
            if res_nom:
                for l in res_nom:
                    clave = f"🏢 {l.address.split(',')[0].strip()}"
                    sugerencias[clave] = (l.latitude, l.longitude)
        except: pass
    return sugerencias

# --- Interfaz Lateral ---
st.sidebar.header("🔍 Buscador")

# Entrada de Origen
q_o = st.sidebar.text_input("Origen (ej: Akron):", key="txt_origen")
sug_o = obtener_sugerencias(q_o)
opciones_o = list(sug_o.keys()) if sug_o else ["Escribe para buscar..."]
sel_o = st.sidebar.selectbox("Confirma punto de partida:", opciones_o, key="sel_origen")

# Entrada de Destino
q_d = st.sidebar.text_input("Destino (ej: CUTonalá):", key="txt_destino")
sug_d = obtener_sugerencias(q_d)
opciones_d = list(sug_d.keys()) if sug_d else ["Escribe para buscar..."]
sel_d = st.sidebar.selectbox("Confirma punto de destino:", opciones_d, key="sel_destino")

# Actualizar coordenadas en el estado global
if sel_o in sug_o: st.session_state.coord_o = sug_o[sel_o]
if sel_d in sug_d: st.session_state.coord_d = sug_d[sel_d]

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Capas del Mapa")
ver_mibici = st.sidebar.toggle("Mostrar Estaciones MiBici", value=False)
ver_talleres = st.sidebar.toggle("Mostrar Talleres Cercanos", value=False)

# --- Botón de Cálculo ---
if st.sidebar.button("🚀 Calcular Ruta Segura"):
    if st.session_state.coord_o and st.session_state.coord_d:
        with st.spinner("Analizando entorno y riesgos..."):
            co_o = st.session_state.coord_o
            co_d = st.session_state.coord_d
            
            st.session_state.clima = obtener_clima(co_o[0], co_o[1])
            st.session_state.nombres = (sel_o, sel_d)
            # Pasamos las coordenadas guardadas
            st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, [], st.session_state.clima)
    else:
        st.sidebar.error("Por favor, selecciona puntos válidos de las listas sugeridas.")

# --- Renderizado Principal ---
ruta_activa = None
if st.session_state.rutas:
    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    ruta_activa = st.session_state.rutas[perfil]
    
    # Mostrar métricas si hay ruta
    c1, c2 = st.columns(2)
    c1.metric("📏 Distancia", f"{ruta_activa['dist_km']:.2f} km")
    c2.metric("🛡️ Seguridad", ruta_activa['seguridad'])
else:
    st.info("👋 ¡Bienvenido! Ingresa origen y destino en el buscador o activa las capas de MiBici.")

# Renderizado del mapa (procura que renderizar_mapa_pro maneje ruta_activa=None)
m = renderizar_mapa_pro(G, ruta_activa, st.session_state.zonas, ver_mibici, ver_talleres)
st_folium(m, width="100%", height=550, key="mapa_principal")
