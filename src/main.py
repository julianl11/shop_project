from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import io
from edges import prewitt_edge_detection # Importiert Ihre Kantenerkennungslogik

app = FastAPI()

# 1. Statische Dateien (für die HTML-Datei, falls nötig)
# Erstellt einen Ordner 'static' und legt dort Ihre index.html ab.
# app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. HTML-Frontend (als String oder in einem Template)
# Wir definieren die HTML direkt hier für Einfachheit.
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Lokale Kantenerkennung</title>
</head>
<body>
    <h1>Bild-Upload zur Kantenerkennung (Prewitt)</h1>
    
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*">
        <input type="submit" value="Kanten erkennen">
    </form>
    
    <img id="result-image" style="margin-top: 50px; max-width: 30%;">
    
    <script>
        // JavaScript, um das Formular asynchron zu senden und das Bild anzuzeigen
        document.querySelector('form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // Konvertiert die empfangenen Bild-Bytes in eine URL und zeigt sie an
                const blob = await response.blob();
                const imageUrl = URL.createObjectURL(blob);
                document.getElementById('result-image').src = imageUrl;
            } else {
                alert('Fehler bei der Bildverarbeitung.');
            }
        });
    </script>
</body>
</html>
"""

# 3. API-Endpunkt für das Haupt-Frontend
@app.get("/", response_class=HTMLResponse)
async def main():
    return HTML_CONTENT

# 4. API-Endpunkt für den Upload und die Verarbeitung
@app.post("/upload")
async def process_image(file: UploadFile = File(...)):
    # 1. Bild-Daten lesen
    image_bytes = await file.read()
    
    # 2. Kantenerkennung durch edges.py aktivieren
    edges_image = prewitt_edge_detection(image_bytes)
    
    # 3. Bild als Bytes (PNG-Format) im Speicher speichern
    img_byte_arr = io.BytesIO()
    edges_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    # 4. Bild-Bytes als StreamingResponse zurückgeben
    return StreamingResponse(img_byte_arr, media_type="image/png")