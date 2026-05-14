import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS, Nominatim
import random

# Importaciones de tus archivos locales
from navegacion import cargar_mapa, calcular_multiples_rutas, obtener_estaciones_mibici
from ia_motor import consultar_ia_riesgos
from clima import obtener_clima
from generar_mapa import renderizar_mapa_pro

st.set_page_config(page_title="Rutas Ciclistas ZMG", layout="wide")

# Inicializar memoria de sesión para que no se pierdan los puntos al recargar
if 'puntos_fijos' not in st.session_state:
    st.session_state.puntos_fijos = {"origen": None, "destino": None, "nombres": (None, None)}
if 'rutas' not in st.session_state: st.session_state.rutas = None

with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# --- BUSCADOR REFORZADO ---
def buscar_lugar(query):
    if not query or len(query) < 3: return {}
    sugerencias = {}
    rid = random.randint(1, 99) # Evita bloqueo de servidor
    try:
        # Intento 1: ArcGIS (Tu original)
        geo = ArcGIS(user_agent=f"bici_app_user_{rid}")
        res = geo.geocode(f"{query}, Jalisco, Mexico", exactly_one=False, limit=5, timeout=5)
        if res:
            for l in res:
                nombre = f"📍 {l.address.split(', Jalisco')[0].strip()}"
                sugerencias[nombre] = (l.latitude, l.longitude)
            return sugerencias
    except:
        try:
            # Intento 2: Nominatim (Respaldo)
            nom = Nominatim(user_agent=f"tester_gdl_{rid}")
            res = nom.geocode(f"{query}, Guadalajara", exactly_one=False, limit=3)
            if res:
                for l in res:
                    nombre = f"🏢 {l.address.split(',')[0].strip()}"
                    sugerencias[nombre] = (l.latitude, l.longitude)
        except: pass
    return sugerencias

# --- INTERFAZ LATERAL ---
st.sidebar.header("🔍 Buscador")
txt_o = st.sidebar.text_input("Origen (Escribe y presiona Enter):", key="in_o")
sug_o = buscar_lugar(txt_o)
sel_o = st.sidebar.selectbox("Selecciona partida:", list(sug_o.keys()) if sug_o else ["Sin resultados"], key="sb_o")

txt_d = st.sidebar.text_input("Destino (Escribe y presiona Enter):", key="in_d")
sug_d = buscar_lugar(txt_d)
sel_d = st.sidebar.selectbox("Selecciona destino:", list(sug_d.keys()) if sug_d else ["Sin resultados"], key="sb_d")

# Guardado inmediato en memoria
if sel_o in sug_o: st.session_state.puntos_fijos["origen"] = sug_o[sel_o]
if sel_d in sug_d: st.session_state.puntos_fijos["destino"] = sug_d[sel_d]

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Capas del Mapa")
ver_mibici = st.sidebar.toggle("Mostrar Estaciones MiBici", value=False)
ver_talleres = st.sidebar.toggle("Mostrar Talleres Cercanos", value=False)

if st.sidebar.button("🚀 Calcular Ruta Segura"):
    p = st.session_state.puntos_fijos
    if p["origen"] and p["destino"]:
        with st.spinner("IA Trazando ruta segura..."):
            clima = obtener_clima(p["origen"][0], p["origen"][1])
            st.session_state.rutas = calcular_multiples_rutas(G, p["origen"], p["destino"], [], clima)
            st.session_state.nombres = (sel_o, sel_d)
    else:
        st.sidebar.error("Selecciona puntos válidos de las sugerencias.")

# --- VISUALIZACIÓN ---
ruta_activa = None
if st.session_state.rutas:
    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    ruta_activa = st.session_state.rutas[perfil]
else:
    st.info("👋 Selecciona origen y destino para activar el trazado en el mapa.")

# MAPA (Siempre al final para capturar cambios)
m = renderizar_mapa_pro(G, ruta_activa, None, ver_mibici, ver_talleres)
st_folium(m, width="100%", height=550, key="mapa_final_v12")
