import osmnx as ox
import networkx as nx
import streamlit as st
import math
import os

@st.cache_resource
def cargar_mapa():
    # Usamos la ruta absoluta para evitar FileNotFoundError en Streamlit Cloud
    directorio_actual = os.path.dirname(__file__)
    ruta_mapa = os.path.join(directorio_actual, "mapa_zmg.graphml")
    return ox.load_graphml(ruta_mapa)

def calcular_multiples_rutas(G, p_origen, p_destino, zonas_calientes, clima_actual):
    # Procesamiento de pesos en el grafo
    for u, v, k, data in G.edges(data=True, keys=True):
        distancia = data.get('length', 1)
        data['peso_directo'] = distancia 
        riesgo_eq, riesgo_seg = 1.0, 1.0

        es_ciclovia = ('bicycle' in data and data['bicycle'] == 'designated') or 'cycleway' in data
        calle_tranquila = 'highway' in data and data['highway'] in ['residential', 'living_street']
        avenida = 'highway' in data and data['highway'] in ['primary', 'secondary', 'trunk']
        calle_mala = 'surface' in data and any(m in str(data['surface']).lower() for m in ['cobblestone', 'unpaved', 'dirt'])

        elev_u = G.nodes[u].get('elevation', 1550) 
        elev_v = G.nodes[v].get('elevation', 1550)
        desnivel = elev_v - elev_u
        pendiente = (desnivel / distancia) * 100 

        factor_esfuerzo = 1.0
        if pendiente > 3: 
            factor_esfuerzo = 1 + (pendiente * 0.2) 

        if es_ciclovia: riesgo_eq, riesgo_seg = 0.2, 0.05 
        elif calle_tranquila: riesgo_eq, riesgo_seg = 0.8, 0.2
        elif avenida: riesgo_eq, riesgo_seg = 5.0, 150.0

        if calle_mala:
            riesgo_eq += 4.0; riesgo_seg += 30.0 
            if clima_actual.get('lluvia', False):
                riesgo_eq += 20.0; riesgo_seg += 200.0 

        data['peso_inteligente'] = distancia * riesgo_eq * factor_esfuerzo
        data['peso_seguro'] = distancia * riesgo_seg * factor_esfuerzo

    # --- SOLUCIÓN AL IMPORTERROR ---
    # Forzamos que las coordenadas sean floats y manejamos la excepción de búsqueda
    try:
        lat_o, lon_o = float(p_origen[0]), float(p_origen[1])
        lat_d, lon_d = float(p_destino[0]), float(p_destino[1])
        
        node_o = ox.distance.nearest_nodes(G, X=lon_o, Y=lat_o)
        node_d = ox.distance.nearest_nodes(G, X=lon_d, Y=lat_d)
    except Exception as e:
        st.error(f"Error al localizar los puntos en el mapa: {e}")
        return {}

    rutas_calculadas = {}

    def guardar_ruta(nombre, peso_usado, color, descripcion, nivel_seguridad):
        try:
            camino = nx.astar_path(G, node_o, node_d, weight=peso_usado)
            dist_m = 0
            instrucciones = []
            calle_actual = ""
            dist_acumulada = 0

            for i in range(len(camino)-1):
                u, v = camino[i], camino[i+1]
                data_arista = G.get_edge_data(u, v)[0]
                dist_tramo = data_arista.get('length', 10)
                dist_m += dist_tramo
                
                nombre_calle = data_arista.get('name', 'Punto de partida')
                if isinstance(nombre_calle, list): nombre_calle = nombre_calle[0]
                
                if not calle_actual: calle_actual = nombre_calle
                
                if (nombre_calle == calle_actual) or (nombre_calle == 'camino sin nombre'):
                    dist_acumulada += dist_tramo
                else:
                    giro = "gira"
                    if i > 0:
                        prev_u = camino[i-1]
                        ang1 = math.atan2(G.nodes[u]['y'] - G.nodes[prev_u]['y'], G.nodes[u]['x'] - G.nodes[prev_u]['x'])
                        ang2 = math.atan2(G.nodes[v]['y'] - G.nodes[u]['y'], G.nodes[v]['x'] - G.nodes[u]['x'])
                        dif = (math.degrees(ang2 - ang1) + 360) % 360
                        if 30 <= dif <= 160: giro = "gira a la izquierda"
                        elif 200 <= dif <= 330: giro = "gira a la derecha"
                    
                    instrucciones.append(f"Avanza **{dist_acumulada/1000:.2f} km** por {calle_actual} y {giro} hacia **{nombre_calle}**.")
                    calle_actual = nombre_calle
                    dist_acumulada = dist_tramo

            if dist_acumulada > 0: instrucciones.append(f"Continúa **{dist_acumulada/1000:.2f} km** por {calle_actual} hasta tu destino.")

            dist_km = dist_m / 1000
            if len(camino) > 1:
                rutas_calculadas[nombre] = {
                    "path": camino, 
                    "color": color, 
                    "dist_km": dist_km, 
                    "tiempo": dist_km * 4, 
                    "desc": descripcion, 
                    "seguridad": nivel_seguridad, 
                    "instrucciones": instrucciones
                }
        except nx.NetworkXNoPath:
            pass # No se encontró ruta para este peso específico

    guardar_ruta(" Rápida", 'peso_directo', "#FF3333", "Ruta corta. Se va por avenidas principales.", "🔴 Riesgo Alto")
    guardar_ruta(" Inteligente", 'peso_inteligente', "#0078D7", "Equilibrio ideal entre distancia y calles tranquilas.", "🟡 Riesgo Moderado")
    guardar_ruta(" Segura", 'peso_seguro', "#00A86B", "Navega internamente por colonias residenciales y ciclovías.", "🟢 Muy Segura")
    
    return rutas_calculadas
