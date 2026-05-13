import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS, Nominatim
from ia_motor import consultar_ia_riesgos
from navegacion import cargar_mapa, calcular_multiples_rutas
from exportador import generar_gpx
from clima import obtener_clima

st.set_page_config(page_title="Rutas Ciclistas ZMG", layout="wide")

def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except: pass

local_css("style.css")

st.title(" CICLISTA-MOVIL")

with st.spinner("Sincronizando red vial metropolitana..."):
    G = cargar_mapa()

for key in ['rutas', 'zonas', 'nombres', 'clima']:
    if key not in st.session_state: st.session_state[key] = None

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
    try:
        res_osm = Nominatim(user_agent="bici_ia_zmg").geocode(f"{query}, Jalisco", exactly_one=False, limit=3, timeout=4)
        if res_osm:
            for l in res_osm:
                partes = l.address.split(',')
                nombre_negocio = f"🏢 {partes[0].strip()}" + (f", {partes[1].strip()}" if len(partes) > 1 else "")
                if nombre_negocio not in sugerencias: sugerencias[nombre_negocio] = (l.latitude, l.longitude)
    except: pass
    return sugerencias

st.sidebar.header(" Buscador")
q_o = st.sidebar.text_input("Origen (Escribe y Enter):", "")
sug_o = obtener_sugerencias(q_o)
sel_o = st.sidebar.selectbox("Selecciona punto de partida:", list(sug_o.keys()) if sug_o else ["Sin resultados"])

q_d = st.sidebar.text_input("Destino (Escribe y Enter):", "")
sug_d = obtener_sugerencias(q_d)
sel_d = st.sidebar.selectbox("Selecciona destino:", list(sug_d.keys()) if sug_d else ["Sin resultados"])

if st.sidebar.button("Calcular Ruta Segura"):
    if "Sin resultados" not in [sel_o, sel_d]:
        co_o, co_d = sug_o[sel_o], sug_d[sel_d]
        
        with st.spinner("Consultando clima real..."):
            estado_clima = obtener_clima(co_o[0], co_o[1])
            st.session_state.clima = estado_clima
            
        with st.spinner("IA analizando peligros..."):
            zonas = consultar_ia_riesgos(sel_o, sel_d, co_o[0], co_o[1], co_d[0], co_d[1])
            
        with st.spinner("Trazando rutas con evasión de clima y riesgos..."):
            # Pasamos el estado_clima al motor matemático
            st.session_state.rutas = calcular_multiples_rutas(G, co_o, co_d, zonas, estado_clima)
            st.session_state.zonas = zonas
            st.session_state.nombres = (sel_o, sel_d)


if st.session_state.rutas:
    st.sidebar.markdown("---")
    st.sidebar.subheader(" Exportar")
    perfil_actual = list(st.session_state.rutas.keys())[1] 
    ruta_gpx = st.session_state.rutas[perfil_actual]
    coords_gpx = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in ruta_gpx['path']]
    
    st.sidebar.download_button(
        label="Descargar Ruta (GPX)",
        data=generar_gpx(coords_gpx, perfil_actual),
        file_name=f"ruta_ciclista.gpx",
        mime="application/gpx+xml",
        use_container_width=True
    )


if st.session_state.rutas:
    clima = st.session_state.clima
    if clima:
        if clima['lluvia']:
            st.warning(f"🌧️ **¡Atención! Está lloviendo en la zona ({clima['temp']}°C - {clima['descripcion']}).** El algoritmo ha modificado las rutas para evitar calles empedradas y de tierra.", icon="⚠️")
        else:
            st.success(f"☀️ **Clima actual favorable ({clima.get('temp', '--')}°C - {clima['descripcion']}).**", icon="🚴")

    perfil = st.radio("Perfil de viaje:", list(st.session_state.rutas.keys()), index=1, horizontal=True)
    r = st.session_state.rutas[perfil]
    
    c1, c2, c3 = st.columns(3)
    c1.metric(" Distancia", f"{r['dist_km']:.2f} km")
    c2.metric(" Tiempo", f"{int(r['tiempo'])} min")
    c3.metric(" Seguridad", r['seguridad'])

    coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in r['path']]
    
    m = folium.Map(location=coords[0], zoom_start=14, tiles=None)
    
    folium.TileLayer('openstreetmap', name='🗺️ Calles y Direcciones', show=True).add_to(m)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='🛰️ Satélite Realista', show=False).add_to(m)
    folium.TileLayer('cartodbpositron', name='☀️ Mapa Claro', show=False).add_to(m)
    folium.TileLayer('cartodbdark_matter', name='🌙 Modo Oscuro', show=False).add_to(m)

    for z in st.session_state.zonas:
        folium.Circle([z['lat'], z['lon']], radius=z['radio']*111000, color=None, fill=True, fill_color='red' if z['nivel']=='rojo' else 'orange', fill_opacity=0.3).add_to(m)

    folium.PolyLine(coords, color=r['color'], weight=6).add_to(m)
    folium.Marker(coords[0], popup=st.session_state.nombres[0], icon=folium.Icon(color='black', icon='play')).add_to(m)
    folium.Marker(coords[-1], popup=st.session_state.nombres[1], icon=folium.Icon(color='black', icon='flag')).add_to(m)
    folium.LayerControl(position='topright').add_to(m)
    
    st_folium(m, width="100%", height=500, key="mapa_con_ruta") # Agregamos key para evitar conflictos
    
    with st.expander("📋 Ver indicaciones paso a paso"):
        instrucciones = r.get('instrucciones', [])
        if instrucciones:
            for i, instruccion in enumerate(instrucciones):
                st.markdown(f"**{i+1}.** {instruccion}")
        else:
            st.info("No se encontraron nombres de calles para esta ruta.")

else:
    st.info("¡Bienvenido! Selecciona un origen y destino en el buscador de la izquierda para calcular tu ruta segura.")
    
    if sel_o in sug_o:
        centro_mapa = sug_o[sel_o]
        zoom_inicial = 15
    else:
        centro_mapa = [20.6767, -103.3475] # Centro GDL
        zoom_inicial = 12

    m_base = folium.Map(location=centro_mapa, zoom_start=zoom_inicial)
    folium.TileLayer('openstreetmap', name='Mapa Base').add_to(m_base)
    
    if sel_o in sug_o:
        folium.Marker(centro_mapa, popup="Punto de partida", icon=folium.Icon(color='blue', icon='info-sign')).add_to(m_base)

    st_folium(m_base, width="100%", height=500, key="mapa_inicial")