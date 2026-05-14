import osmnx as ox
import streamlit as st
import requests
import time

def add_elevations_batch(G, batch_size=100):
    nodes_to_query = []
    for node, data in G.nodes(data=True):
        nodes_to_query.append({"latitude": data['y'], "longitude": data['x']})
    
    total_nodes = len(nodes_to_query)
    st.info(f"Recolectando alturas para {total_nodes} nodos. El servidor puede ser lento, se aplicará lógica de reintentos.")
    
    progress_bar = st.progress(0)
    for i in range(0, total_nodes, batch_size):
        batch = nodes_to_query[i:i + batch_size]
        url = "https://api.open-elevation.com/api/v1/lookup"
        
        exito = False
        for intento in range(3): 
            try:
                response = requests.post(url, json={"locations": batch}, timeout=15)
                response.raise_for_status() # Verifica que el servidor no mande error 500
                data = response.json()
                
                results = data['results']
                for j, res in enumerate(results):
                    node_to_update = list(G.nodes())[i + j]
                    G.nodes[node_to_update]['elevation'] = res['elevation']
                
                exito = True
                break 
                
            except Exception as e:
                time.sleep(3) 
                
        if not exito:
            st.error(f"Error definitivo en batch {i} después de 3 intentos. Skipping.")
            
        progreso = min(int((i + batch_size) / total_nodes * 100), 100)
        progress_bar.progress(progreso)
        st.write(f"Batch {i//batch_size + 1}/{total_nodes//batch_size + 1} procesado.")

    st.success("Alturas pintadas con éxito.")

st.title("Descargador de Mapa con Altimetría")
st.write("LONGORIA FLORES CESAR Y PANTOJA ARAIZA ISMAEL")

if st.button("Descargar y 'Pintar' Alturas a Mapa ZMG (Lento - Gratuito)"):
    ciudades = ["Guadalajara, Jalisco, Mexico", "Zapopan, Jalisco, Mexico", "San Pedro Tlaquepaque, Jalisco, Mexico", "Tonalá, Jalisco, Mexico"]
    with st.spinner("Descargando red ciclista de OpenStreetMap..."):
        G = ox.graph_from_place(ciudades, network_type='bike')
    
    st.success("Mapa descargado. Iniciando altimetría (Esto va a tardar muchísimo).")
    with st.spinner("'Pintando' alturas en lotes con tolerancia a fallos..."):
        add_elevations_batch(G)
        
    with st.spinner("Guardando mapa gigante..."):
        ox.save_graphml(G, filepath="mapa_zmg.graphml")
    
    st.success("¡Listo! Mapa gigante guardado como 'mapa_zmg.graphml'. Puedes usar 'app.py' ahora.")
