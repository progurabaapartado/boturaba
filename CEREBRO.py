import pandas as pd
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# 🔗 LINK DIRECTO DE ONEDRIVE (con &download=1)
EXCEL_URL = "https://ingeomega-my.sharepoint.com/:x:/g/personal/fcubillos_ingeomegalec_com/IQAMvcy5dkpATaxUyZWqvXf0AYtfZw7L5solrnrDD45nKaY?e=Wk7ooF&download=1"

def cargar_datos():
    df = pd.read_excel(EXCEL_URL)
    df['INSTALACION'] = df['INSTALACION'].astype(str)
    df['SERVICIO'] = df['SERVICIO'].astype(str).str.upper()
    return df

user_sessions = {}

@app.route("/bot", methods=['POST'])
def bot():
    df = cargar_datos()  # 🔄 Se actualiza en cada mensaje

    from_number = request.form.get('From')
    msg = request.form.get('Body', '').strip()
    resp = MessagingResponse()
    
    if from_number not in user_sessions:
        user_sessions[from_number] = {'estado': 'INICIO'}
    
    sesion = user_sessions[from_number]

    # 1. Inicio
    if 'HOLA' in msg.upper() or sesion['estado'] == 'INICIO':
        user_sessions[from_number] = {'estado': 'ESPERANDO_INSTALACION'}
        resp.message("👋 ¡Hola! Bienvenido al bot de Urabá.\nPor favor escribe el número de instalación.")
    
    # 2. Validar Instalación
    elif sesion['estado'] == 'ESPERANDO_INSTALACION':
        if msg in df['INSTALACION'].values:
            servicios = df[df['INSTALACION'] == msg]['SERVICIO'].unique()
            user_sessions[from_number].update({
                'estado': 'ESPERANDO_SERVICIO',
                'instalacion': msg
            })
            resp.message(f"✅ Instalación encontrada.\nServicios: {', '.join(servicios)}\n¿Cuál deseas consultar?")
        else:
            resp.message("❌ Instalación no encontrada. Intenta de nuevo.")

    # 3. Mostrar historial
    elif sesion['estado'] == 'ESPERANDO_SERVICIO':
        inst = user_sessions[from_number]['instalacion']
        servicio_input = msg.upper()
        
        subset = df[df['INSTALACION'] == inst]
        fila_filtrada = subset[subset['SERVICIO'].str.contains(servicio_input, na=False)]
        
        if not fila_filtrada.empty:
            # Iconos
            servicio_nombre = fila_filtrada.iloc[0]['SERVICIO']
            if "AGUA" in servicio_nombre:
                icono = "💧"
            elif "ENERGIA" in servicio_nombre:
                icono = "⚡"
            elif "GAS" in servicio_nombre:
                icono = "🔥"
            else:
                icono = "✅"

            respuesta = f"{icono} HISTORIAL {servicio_input}\n========================\n"
            
            for _, fila in fila_filtrada.iterrows():
                respuesta += (
                    f"📅 Mes: {fila.get('MES_FACTURACION', 'N/A')}\n"
                    f"🔢 Lectura: {fila.get('LECTURA_TOMADA', 'N/A')}\n"
                    f"👤 Lector: {fila.get('LECTOR', 'N/A')}\n"
                    f"📝 Obs: {fila.get('CAUSANL_OBS', 'N/A')}\n"
                    f"------------------------\n"
                )
            
            resp.message(respuesta)
            user_sessions[from_number] = {'estado': 'INICIO'}
        else:
            resp.message(f"❌ No encontré '{msg}'. Escríbelo como aparece en la lista.")

    return str(resp)

# ⚠️ IMPORTANTE PARA RENDER
if __name__ == "__main__":
    app.run()