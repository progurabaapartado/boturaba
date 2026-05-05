import pandas as pd
import os
import shutil
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Rutas: el archivo original se mantiene, la copia se lee sin bloqueos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGINAL = os.path.join(BASE_DIR, 'Base_Datos_Lecturas.xlsx')
TEMP_FILE = os.path.join(BASE_DIR, 'temp_db.xlsx')

def cargar_datos():
    # Copiamos a temp_db.xlsx para que OneDrive no bloquee el acceso
    shutil.copy2(ORIGINAL, TEMP_FILE)
    df = pd.read_excel(TEMP_FILE)
    df['INSTALACION'] = df['INSTALACION'].astype(str)
    df['SERVICIO'] = df['SERVICIO'].astype(str).str.upper()
    return df

# Carga inicial
df = cargar_datos()
print("Base de datos cargada correctamente.")

user_sessions = {}

@app.route("/bot", methods=['POST'])
def bot():
    from_number = request.form.get('From')
    msg = request.form.get('Body', '').strip()
    resp = MessagingResponse()
    
    if from_number not in user_sessions:
        user_sessions[from_number] = {'estado': 'INICIO'}
    
    sesion = user_sessions[from_number]

    # 1. Inicio
    if 'HOLA' in msg.upper() or sesion['estado'] == 'INICIO':
        user_sessions[from_number] = {'estado': 'ESPERANDO_INSTALACION'}
        resp.message("👋 ¡Hola Bienvenido al bot de Uraba! Por favor, escribe el número de instalación.")
    
    # 2. Validar Instalación
    elif sesion['estado'] == 'ESPERANDO_INSTALACION':
        if msg in df['INSTALACION'].values:
            servicios = df[df['INSTALACION'] == msg]['SERVICIO'].unique()
            user_sessions[from_number].update({'estado': 'ESPERANDO_SERVICIO', 'instalacion': msg})
            resp.message(f"✅ Instalación encontrada. Servicios: {', '.join(servicios)}. ¿Qué servicio deseas consultar?")
        else:
            resp.message("❌ Instalación no encontrada. Intenta de nuevo.")

    # 3. Mostrar Detalle (con iconos, historial y LECTOR)
    elif sesion['estado'] == 'ESPERANDO_SERVICIO':
        inst = user_sessions[from_number]['instalacion']
        servicio_input = msg.upper() 
        
        subset = df[df['INSTALACION'] == inst]
        fila_filtrada = subset[subset['SERVICIO'].str.contains(servicio_input, na=False)]
        
        if not fila_filtrada.empty:
            # Seleccionar icono según el servicio
            if "AGUA" in fila_filtrada.iloc[0]['SERVICIO']: icono = "💧"
            elif "ENERGIA" in fila_filtrada.iloc[0]['SERVICIO']: icono = "⚡"
            elif "GAS" in fila_filtrada.iloc[0]['SERVICIO']: icono = "🔥"
            else: icono = "✅"

            respuesta = f"{icono} HISTORIAL {servicio_input}\n==========================\n"
            
            # Recorrer TODAS las filas del servicio encontrado
            for _, fila in fila_filtrada.iterrows():
                respuesta += (f"📅 Mes: {fila.get('MES_FACTURACION', 'N/A')}\n"
                              f"🔢 Lectura: {fila.get('LECTURA_TOMADA', 'N/A')}\n"
                              f"👤 Lector: {fila.get('LECTOR', 'N/A')}\n"
                              f"📝 Obs: {fila.get('CAUSANL_OBS', 'N/A')}\n"
                              f"--------------------------\n")
            
            resp.message(respuesta)
            user_sessions[from_number] = {'estado': 'INICIO'}
        else:
            resp.message(f"❌ No encontré '{msg}'. Intenta escribirlo tal como aparece en la lista.")

    return str(resp)

if __name__ == "__main__":
    app.run(port=5000)