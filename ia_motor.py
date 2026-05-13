import math
import json
import google.generativeai as genai
import streamlit as st

def consultar_ia_riesgos(origen_nombre, destino_nombre, lat_o, lon_o, lat_d, lon_d):
    d_lat = lat_d - lat_o
    d_lon = lon_d - lon_o
    dist_total = math.sqrt(d_lat**2 + d_lon**2)
    
    if dist_total < 0.015:
        return [] 

    LLAVE_SECRETA = "AIzaSyBnzZBB7LSZdPxlMhs_aMT0M-iaUDhY7RY" 
    
    try:
        genai.configure(api_key=LLAVE_SECRETA)
        model = genai.GenerativeModel('gemini-pro') 
        prompt = f"""
        Como analista de IA, evalúa la ruta ciclista de '{origen_nombre}' a '{destino_nombre}'.
        Devuelve SOLO un arreglo JSON con 2 zonas de riesgo intermedias. 
        Formato: [{{"nombre": "Riesgo", "lat": {lat_o + (d_lat*0.5)}, "lon": {lon_o + (d_lon*0.5)}, "radio": 0.005, "nivel": "rojo"}}]
        """
        response = model.generate_content(prompt)
        texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
        zonas_ia = json.loads(texto_limpio)
        st.toast("✅ Google Cloud AI analizó el entorno.", icon="☁️")
        return zonas_ia
    except Exception as e:
        print(f"Error API: {e}")
        radio_base = min(0.01, dist_total * 0.10) 
        return [
            {"nombre": "Zona de Alta Precaución (Heurística)", "lat": lat_o + (d_lat * 0.5), "lon": lon_o + (d_lon * 0.5), "radio": radio_base, "nivel": "rojo"},
            {"nombre": "Congestión Vehicular", "lat": lat_o + (d_lat * 0.25), "lon": lon_o + (d_lon * 0.25), "radio": radio_base * 0.8, "nivel": "amarillo"}
        ]