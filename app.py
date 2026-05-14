
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS, Nominatim
import random
import time

# Importaciones de tus otros archivos
from navegacion import cargar_mapa, calcular_multiples_rutas, obtener_estaciones_mibici
from ia_motor import consultar_ia_riesgos
from clima import obtener_clima
from generar_mapa import renderizar_mapa_pro

st.set_page_config(page_title="Rutas Ciclistas ZMG", layout="wide")

# 1. MEMORIA DE SESIÓN REFORZADA
if 'puntos' not in st.session_state:
    st.session_state.puntos = {"origen": None, "destino": None, "nombres": (None, None)}
if 'rutas' not in st.session_state: st.session_state.rutas = None

with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

# 2. BUSCADOR MULTI-SERVIDOR (Si falla uno, entra el otro)
def buscar_ubicacion(query):
    if not query or len(query) < 3: return {}
    sugerencias = {}
    
    # Generamos un ID aleatorio para evitar bloqueos por IP/Agente
    random_id = random.randint(1000, 9999)
    
    # INTENTO 1: ArcGIS
    try:
        arcgis = ArcGIS(user_agent=f"bici_app_zmg_{random_id}")
        res = arcgis.geocode(f"{query}, Jalisco, Mexico", exactly_one=False, limit=5, timeout=5)
        if res:
            for l in res:
                nombre = f"📍 {l.address.split(', Jalisco')[0].strip()}"
                sugerencias[nombre] = (l.latitude, l.longitude)
            return sugerencias
    except: pass

    # INTENTO 2: Nominatim (Si falla ArcGIS)
    try:
        nominatim = Nominatim(user_agent=f"bici_tester_{random_id}")
        res = nominatim.geocode(f"{query}, Guadalajara", exactly_one=False, limit=3, timeout=5)
        if res:
            for l in res:
                nombre = f"🏢 {l.address.split(',')[0].strip()}"
                sugerencias[nombre] = (l.latitude, l.longitude)
    except: pass
    
    return sugerencias

# --- INTERFAZ LATERAL ---
st.sidebar.header("🔍 Buscador")

# ORIGEN
txt_o = st.sidebar.text_input("Origen (ej. Akron):", key="txt_o")
sug_o = buscar_ubicacion(txt_o)
sel_o = st.sidebar.selectbox("Selecciona partida:", list(sug_o.keys()) if sug_o else ["Escribe para buscar..."], key="sb_o")

# DESTINO
txt_d = st.sidebar.text_input("Destino (ej. CUTonalá):", key="txt_d")
sug_d = buscar_ubicacion(txt_d)
sel_d = st.sidebar.selectbox("Selecciona destino:", list(sug_d.keys()) if sug_d else ["Escribe para buscar..."], key="sb_d")

# GUARDADO DE SEGURIDAD
if sel_o in sug_o:
    st.session_state.puntos["origen"] = sug_o[sel_o]
    st.session_state.puntos["nombres"] = (sel_o, st.session_state.puntos["nombres"][1])
if sel_d in sug_d:
    st.session_state.puntos["destino"] = sug_d[sel_d]
    st.session_state.puntos["nombres"] = (st.session_state.puntos["nombres"][0], sel_d)

st.sidebar.markdown("---")
ver_mibici = st.sidebar.toggle("Mostrar Estaciones MiBici", value=False)
ver_talleres = st.sidebar.toggle("Mostrar Talleres Cercanos", value=False)

# --- BOTÓN DE CÁLCULO ---
if st.sidebar.button("🚀 Calcular Ruta Segura"):
    p = st.session_state.puntos
    if p["origen"] and p["destino"]:
        with st.spinner("Trazando ruta en el mapa..."):
            co_o, co_d = p["origen"], p["destino"]
            clima = obtener_clima(co_o[0], co_o[1])
            # Forzamos el cálculo de rutas
            st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, [], clima)
    else:
        st.sidebar.error("⚠️ Debes seleccionar una ubicación de la lista antes de calcular.")

# --- RENDERIZADO ---
ruta_actual = None
if st.session_state.rutas:
    perfil = st.radio("Perfil:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    ruta_actual = st.session_state.rutas[perfil]
    st.success(f"Ruta encontrada: {ruta_actual['dist_km']:.2f} km")
else:
    st.info("👋 Selecciona origen y destino para activar el trazado.")

# MAPA FINAL
m = renderizar_mapa_pro(G, ruta_actual, None, ver_mibici, ver_talleres)
st_folium(m, width="100%", height=550, key="mapa_final_v10")
