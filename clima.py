import requests

def obtener_clima(lat, lon):
    API_KEY = "75c2242664580a230516e030046fba8e" 

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&lang=es&units=metric"
        respuesta = requests.get(url, timeout=5)
        
        respuesta.raise_for_status() 
        datos = respuesta.json()
        
        clima_id = datos['weather'][0]['id']
        llueve = clima_id < 700
        desc = datos['weather'][0]['description'].capitalize()
        temp = int(datos['main']['temp'])
        
        return {"lluvia": llueve, "descripcion": desc, "temp": temp}
    
    except Exception as e:
        return {"lluvia": False, "descripcion": f"ERROR REAL: {e}", "temp": "--"}