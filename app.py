import os
from openai import OpenAI
import uuid
from flask import Flask, render_template, request, send_from_directory
from openai import OpenAI
from PyPDF2 import PdfReader

app = Flask(__name__)

# 1. CONFIGURACIÓN INICIAL
# El sistema buscará la clave en las 'variables de entorno' del servidor
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Carpetas necesarias para el funcionamiento
UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/procesar', methods=['POST'])
def procesar():
    if 'archivo' not in request.files:
        return "No se encontró el archivo", 400
    
    file = request.files['archivo']
    if file.filename == '':
        return "Nombre de archivo vacío", 400

    if file:
        try:
            # 2. GUARDAR PDF TEMPORALMENTE
            id_sesion = str(uuid.uuid4())[:8]
            pdf_path = os.path.join(UPLOAD_FOLDER, f"{id_sesion}_{file.filename}")
            file.save(pdf_path)
            
            print(f"--- Procesando: {file.filename} ---")

            # 3. EXTRACCIÓN DE TEXTO
            reader = PdfReader(pdf_path)
            texto_bruto = "".join([pagina.extract_text() for pagina in reader.pages])
            
            if not texto_bruto.strip():
                return "El PDF parece estar vacío o ser una imagen (no contiene texto extraíble).", 400

            # 4. ADAPTACIÓN PEDAGÓGICA NEAE (GPT-4o)
            print("🧠 Adaptando texto con GPT-4o...")
            adaptacion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "Eres experto en Pedagogía Terapéutica y DUA. "
                            "Simplifica el texto para un alumno con dificultades de lectura: "
                            "usa frases cortas, lenguaje sencillo, elimina ruidos de edición "
                            "y organiza con marcadores de orden."
                        )
                    },
                    {"role": "user", "content": texto_bruto}
                ]
            )
            texto_listo = adaptacion.choices[0].message.content

            # 5. GENERACIÓN DE AUDIO (TTS)
            print("🎙️ Generando audio neuronal...")
            nombre_audio = f"audio_{id_sesion}.mp3"
            audio_path = os.path.join(STATIC_FOLDER, nombre_audio)
            
            audio_res = client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=texto_listo
            )
            audio_res.stream_to_file(audio_path)

            print(f"✨ Proceso finalizado: {nombre_audio}")
            
            # Devolvemos la ruta relativa para que el index.html la use en el botón
            return f"/static/{nombre_audio}"

        except Exception as e:
            print(f"❌ Error crítico: {str(e)}")
            return f"Error en el servidor: {str(e)}", 500

# Ruta para que Flask permita acceder a los archivos generados en 'static'
@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

if __name__ == '__main__':
    # Ejecución en local puerto 5000
    app.run(debug=True, port=5000)