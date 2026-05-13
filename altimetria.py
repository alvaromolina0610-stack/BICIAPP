import requests

def obtener_elevacion(coords_list):
    """
    Recibe una lista de (lat, lon) y devuelve sus alturas en metros.
    """
    try:
        locations = [{"latitude": lat, "longitude": lon} for lat, lon in coords_list]
        url = "https://api.open-elevation.com/api/v1/lookup"
        response = requests.post(url, json={"locations": locations}, timeout=5)
        data = response.json()
        return [res['elevation'] for res in data['results']]
    except:
        return [0] * len(coords_list)