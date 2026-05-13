import xml.etree.ElementTree as ET
from io import BytesIO

def generar_gpx(ruta_coords, nombre_ruta):
    """
    Convierte una lista de coordenadas (lat, lon) en un archivo GPX.
    """
    gpx = ET.Element("gpx", version="1.1", creator="Bici IA ZMG")
    
    trk = ET.SubElement(gpx, "trk")
    name = ET.SubElement(trk, "name")
    name.text = f"Ruta Bici IA: {nombre_ruta}"
    trkseg = ET.SubElement(trk, "trkseg")

    for lat, lon in ruta_coords:
        ET.SubElement(trkseg, "trkpt", lat=str(lat), lon=str(lon))

    xml_str = ET.tostring(gpx, encoding="utf-8", method="xml")
    
    b_io = BytesIO()
    b_io.write(xml_str)
    b_io.seek(0)
    
    return b_io