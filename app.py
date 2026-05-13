# ... (Todo tu código anterior se mantiene igual hasta llegar al bloque 'else' final)

if st.session_state.rutas:
    # --- MANTENER ESTA SECCIÓN IGUAL (Visualización de la ruta calculada) ---
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
    
    for z in st.session_state.zonas:
        folium.Circle([z['lat'], z['lon']], radius=z['radio']*111000, color=None, fill=True, fill_color='red' if z['nivel']=='rojo' else 'orange', fill_opacity=0.3).add_to(m)

    folium.PolyLine(coords, color=r['color'], weight=6).add_to(m)
    folium.Marker(coords[0], popup=st.session_state.nombres[0], icon=folium.Icon(color='black', icon='play')).add_to(m)
    folium.Marker(coords[-1], popup=st.session_state.nombres[1], icon=folium.Icon(color='black', icon='flag')).add_to(m)
    folium.LayerControl(position='topright').add_to(m)
    
    st_folium(m, width="100%", height=500, key="mapa_con_ruta")
    
    with st.expander("📋 Ver indicaciones paso a paso"):
        instrucciones = r.get('instrucciones', [])
        if instrucciones:
            for i, instruccion in enumerate(instrucciones):
                st.markdown(f"**{i+1}.** {instruccion}")
        else:
            st.info("No se encontraron nombres de calles para esta ruta.")

else:
    # --- BLOQUE ELSE MODIFICADO PARA MOSTRAR AMBOS MARCADORES ---
    st.info("¡Bienvenido! Selecciona un origen y destino en el buscador de la izquierda para calcular tu ruta segura.")
    
    # 1. Lógica inteligente para centrar el mapa
    if sel_o in sug_o and sel_d in sug_d:
        # Si ambos existen, centramos en el punto medio
        centro_mapa = [(sug_o[sel_o][0] + sug_d[sel_d][0])/2, (sug_o[sel_o][1] + sug_d[sel_d][1])/2]
        zoom_inicial = 12
    elif sel_o in sug_o:
        centro_mapa = sug_o[sel_o]
        zoom_inicial = 15
    elif sel_d in sug_d:
        centro_mapa = sug_d[sel_d]
        zoom_inicial = 15
    else:
        centro_mapa = [20.6767, -103.3475] # Centro GDL
        zoom_inicial = 12

    m_base = folium.Map(location=centro_mapa, zoom_start=zoom_inicial)
    folium.TileLayer('openstreetmap', name='Mapa Base').add_to(m_base)
    
    # 2. Agregar marcador de Origen (Azul)
    if sel_o in sug_o:
        folium.Marker(
            sug_o[sel_o], 
            popup="Punto de partida", 
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m_base)

    # 3. Agregar marcador de Destino (Rojo)
    if sel_d in sug_d:
        folium.Marker(
            sug_d[sel_d], 
            popup="Destino seleccionado", 
            icon=folium.Icon(color='red', icon='map-marker')
        ).add_to(m_base)

    st_folium(m_base, width="100%", height=500, key="mapa_inicial")
