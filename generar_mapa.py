import folium
from navegacion import obtener_estaciones_mibici

def renderizar_mapa_pro(G, ruta_activa, zonas, mostrar_mibici, mostrar_talleres):
    # Centrar mapa en el inicio de la ruta
    coords_ruta = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in ruta_activa['path']]
    m = folium.Map(location=coords_ruta[0], zoom_start=14)
    folium.TileLayer('openstreetmap').add_to(m)

    # 1. Capa de MiBici
    if mostrar_mibici:
        estaciones = obtener_estaciones_mibici()
        for est in estaciones:
            color_m = 'blue' if est['bicis'] > 0 else 'lightgray'
            folium.Marker(
                [est['lat'], est['lon']],
                popup=f"<b>{est['nombre']}</b><br>🚲 Bicis: {est['bicis']}<br>🔒 Libres: {est['candados']}",
                icon=folium.Icon(color=color_m, icon='bicycle', prefix='fa')
            ).add_to(m)

    # 2. Capa de Talleres (Ejemplos fijos en ZMG)
    if mostrar_talleres:
        talleres = [
            {"nombre": "Taller Ciclo-Vías", "coords": [20.674, -103.359]},
            {"nombre": "Bici-Reparación Tonalá", "coords": [20.624, -103.242]},
            {"nombre": "Taller El Rayo (Zapopan)", "coords": [20.720, -103.390]}
        ]
        for t in talleres:
            folium.Marker(
                t['coords'],
                popup=t['nombre'],
                icon=folium.Icon(color='orange', icon='wrench', prefix='fa')
            ).add_to(m)

    # 3. Dibujar Ruta y Zonas de Riesgo
    folium.PolyLine(coords_ruta, color=ruta_activa['color'], weight=6).add_to(m)
    
    if zonas:
        for z in zonas:
            folium.Circle([z['lat'], z['lon']], radius=z['radio']*1000, color='red', fill=True, fill_opacity=0.2).add_to(m)

    return m
