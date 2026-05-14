import osmnx as ox
import networkx as nx
import streamlit as st
import math
import os
import requests  # Nueva dependencia para MiBici

@st.cache_resource
def cargar_mapa():
    directorio_actual = os.path.dirname(__file__)
    ruta_mapa = os.path.join(directorio_actual, "mapa_zmg.graphml")
    return ox.load_graphml(ruta_mapa)

def obtener_estaciones_mibici():
    """Obtiene datos de MiBici GDL en tiempo real (Bicis y Candados)."""
    try:
        info_url = "https://gdl.publicbikesystem.net/ube/gbfs/v1/en/station_information.json"
        status_url = "https://gdl.publicbikesystem.net/ube/gbfs/v1/en/station_status.json"
        
        info_res = requests.get(info_url, timeout=5).json()
        status_res = requests.get(status_url, timeout=5).json()
        
        status_dict = {s['station_id']: s for s in status_res['data']['stations']}
        
        estaciones = []
        for s in info_res['data']['stations']:
            s_id = s['station_id']
            estaciones.append({
                'nombre': s['name'],
                'lat': s['lat'],
                'lon': s['lon'],
                'bicis': status_dict.get(s_id, {}).get('num_bikes_available', 0),
                'candados': status_dict.get(s_id, {}).get('num_docks_available', 0)
            })
        return estaciones
    except:
        return []

def calcular_multiples_rutas(G, p_origen, p_destino, zonas_calientes, clima_actual):
    # --- Mantenemos toda tu lógica de pesos (esfuerzo, ciclovía, riesgo) ---
    for u, v, k, data in G.edges(data=True, keys=True):
        distancia = data.get('length', 1)
        data['peso_directo'] = distancia 
        riesgo_eq, riesgo_seg = 1.0, 1.0
        # ... (Tu código de procesamiento de pesos sigue igual)
        
        # Simplificación para el ejemplo, pero aquí va tu bloque de if/else original
        data['peso_inteligente'] = distancia * riesgo_eq
        data['peso_seguro'] = distancia * riesgo_seg

    try:
        lat_o, lon_o = float(p_origen[0]), float(p_origen[1])
        lat_d, lon_d = float(p_destino[0]), float(p_destino[1])
        node_o = ox.distance.nearest_nodes(G, X=lon_o, Y=lat_o)
        node_d = ox.distance.nearest_nodes(G, X=lon_d, Y=lat_d)
    except:
        return {}

    rutas_calculadas = {}

    def guardar_ruta(nombre, peso_usado, color, descripcion, nivel_seguridad):
        try:
            camino = nx.astar_path(G, node_o, node_d, weight=peso_usado)
            dist_m = sum(ox.utils_graph.get_route_edge_attributes(G, camino, 'length'))
            rutas_calculadas[nombre] = {
                "path": camino, "color": color, "dist_km": dist_m/1000, 
                "tiempo": (dist_m/1000)*4, "desc": descripcion, 
                "seguridad": nivel_seguridad
            }
        except: pass

    guardar_ruta(" Rápida", 'peso_directo', "#FF3333", "Ruta corta.", "🔴 Riesgo Alto")
    guardar_ruta(" Inteligente", 'peso_inteligente', "#0078D7", "Equilibrio.", "🟡 Riesgo Moderado")
    guardar_ruta(" Segura", 'peso_seguro', "#00A86B", "Ciclovías.", "🟢 Muy Segura")
    
    return rutas_calculadas
