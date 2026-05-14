import osmnx as ox
import networkx as nx
import streamlit as st
import math
import os
import requests

@st.cache_resource
def cargar_mapa():
    """Carga el grafo desde el archivo local .graphml."""
    directorio_actual = os.path.dirname(__file__)
    ruta_mapa = os.path.join(directorio_actual, "mapa_zmg.graphml")
    return ox.load_graphml(ruta_mapa)

def obtener_estaciones_mibici():
    """Obtiene datos de MiBici GDL en tiempo real (Bicis y Candados)."""
    try:
        # Endpoints oficiales del sistema GBFS de Guadalajara
        info_url = "https://gdl.publicbikesystem.net/ube/gbfs/v1/en/station_information.json"
        status_url = "https://gdl.publicbikesystem.net/ube/gbfs/v1/en/station_status.json"
        
        info_res = requests.get(info_url, timeout=5).json()
        status_res = requests.get(status_url, timeout=5).json()
        
        # Mapeamos disponibilidad por ID de estación
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
    except Exception:
        # Retornamos lista vacía para evitar que la app se detenga si la API falla
        return []

def calcular_multiples_rutas(G, p_origen, p_destino, zonas_calientes, clima_actual):
    """Calcula rutas basadas en pesos de distancia, seguridad y esfuerzo físico."""
    
    # 1. ACTUALIZACIÓN DE PESOS EN EL GRAFO
    for u, v, k, data in G.edges(data=True, keys=True):
        distancia = data.get('length', 1)
        riesgo_eq, riesgo_seg = 1.0, 1.0

        # Atributos de infraestructura
        es_ciclovia = ('bicycle' in data and data['bicycle'] == 'designated') or 'cycleway' in data
        calle_tranquila = 'highway' in data and data['highway'] in ['residential', 'living_street']
        avenida = 'highway' in data and data['highway'] in ['primary', 'secondary', 'trunk']
        
        # Altimetría y Esfuerzo (Pendientes)
        elev_u = G.nodes[u].get('elevation', 1550) 
        elev_v = G.nodes[v].get('elevation', 1550)
        pendiente = ((elev_v - elev_u) / distancia) * 100 

        factor_esfuerzo = 1.0 + (max(0, pendiente) * 0.2) if pendiente > 3 else 1.0

        # Lógica de Seguridad y Comodidad
        if es_ciclovia: 
            riesgo_eq, riesgo_seg = 0.2, 0.05 
        elif calle_tranquila: 
            riesgo_eq, riesgo_seg = 0.8, 0.2
        elif avenida: 
            riesgo_eq, riesgo_seg = 5.0, 150.0

        # Ajuste por Clima (Lluvia)
        if clima_actual.get('lluvia', False) and 'surface' in data:
            if any(m in str(data['surface']).lower() for m in ['cobblestone', 'unpaved', 'dirt']):
                riesgo_eq += 20.0; riesgo_seg += 200.0

        data['peso_directo'] = distancia 
        data['peso_inteligente'] = distancia * riesgo_eq * factor_esfuerzo
        data['peso_seguro'] = distancia * riesgo_seg * factor_esfuerzo

    # 2. LOCALIZACIÓN DE NODOS CERCANOS
    try:
        # Aseguramos coordenadas en formato float
        node_o = ox.distance.nearest_nodes(G, X=float(p_origen[1]), Y=float(p_origen[0]))
        node_d = ox.distance.nearest_nodes(G, X=float(p_destino[1]), Y=float(p_destino[0]))
    except Exception:
        return {}

    rutas_calculadas = {}

    # 3. GENERACIÓN DE RUTAS POR PERFIL
    def guardar_ruta(nombre, peso_usado, color, descripcion, nivel_seguridad):
        try:
            camino = nx.astar_path(G, node_o, node_d, weight=peso_usado)
            # Calculamos la distancia total real
            dist_m = sum(ox.utils_graph.get_route_edge_attributes(G, camino, 'length'))
            
            rutas_calculadas[nombre] = {
                "path": camino, 
                "color": color, 
                "dist_km": dist_m / 1000, 
                "tiempo": (dist_m / 1000) * 4, # Estimado a 15km/h
                "desc": descripcion, 
                "seguridad": nivel_seguridad
            }
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

    guardar_ruta(" Rápida", 'peso_directo', "#FF3333", "Ruta más corta por vías principales.", "🔴 Riesgo Alto")
    guardar_ruta(" Inteligente", 'peso_inteligente', "#0078D7", "Equilibrio entre distancia y seguridad.", "🟡 Riesgo Moderado")
    guardar_ruta(" Segura", 'peso_seguro', "#00A86B", "Prioriza ciclovías y calles internas.", "🟢 Muy Segura")
    
    return rutas_calculadas
