import folium
from navegacion import obtener_estaciones_mibici

def renderizar_mapa_pro(G, ruta_activa, zonas, mostrar_mibici, mostrar_talleres):
    # Centrado dinámico
    if ruta_activa and 'path' in ruta_activa:
        centro = [G.nodes[ruta_activa['path'][0]]['y'], G.nodes[ruta_activa['path'][0]]['x']]
        zoom = 14
    else:
        centro = [20.6767, -103.3475]
        zoom = 12

    m = folium.Map(location=centro, zoom_start=zoom)
    folium.TileLayer('openstreetmap').add_to(m)

    # 1. Capa de MiBici
    if mostrar_mibici:
        estaciones = obtener_estaciones_mibici()
        for est in estaciones:
            # Color según disponibilidad: Azul (hay bicis), Rojo (vacía)
            color_m = 'blue' if est['bicis'] > 0 else 'red'
            folium.Marker(
                [est['lat'], est['lon']],
                popup=f"<b>{est['nombre']}</b><br>🚲 Bicis: {est['bicis']}<br>🔒 Libres: {est['candados']}",
                icon=folium.Icon(color=color_m, icon='bicycle', prefix='fa')
            ).add_to(m)

    # 2. Capa de Talleres
    if mostrar_talleres:
        talleres = [
            {"nombre": "Taller Ciclo-Vías", "coords": [20.674, -103.359]},
            {"nombre": "Bici-Reparación Tonalá", "coords": [20.624, -103.242]},
            {"nombre": "Taller El Rayo (Zapopan)", "coords": [20.720, -103.390]}
        ]
        for t in talleres:
            folium.Marker(
                t['coords'], popup=t['nombre'],
                icon=folium.Icon(color='orange', icon='wrench', prefix='fa')
            ).add_to(m)

    # 3. Dibujar Ruta
    if ruta_activa and 'path' in ruta_activa:
        coords_ruta = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in ruta_activa['path']]
        folium.PolyLine(coords_ruta, color=ruta_activa['color'], weight=6).add_to(m)
        folium.Marker(coords_ruta[0], icon=folium.Icon(color='green', icon='play')).add_to(m)
        folium.Marker(coords_ruta[-1], icon=folium.Icon(color='red', icon='flag')).add_to(m)

    return m
