from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import io
import base64
from edges import prewitt_edge_detection # Importiert Ihre Kantenerkennungslogik

app = FastAPI()

# 1. Statische Dateien (für die HTML-Datei, falls nötig)
app.mount("/data", StaticFiles(directory="data"), name="data")

templates = Jinja2Templates(directory="/Users/julianlorenz/Documents/Fallstudie_website/shop_project/src/static/")

# 3. API-Endpunkt für das Haupt-Frontend
@app.get("/", response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 4. API-Endpunkt für den Upload und die Verarbeitung
@app.post("/upload")
async def process_image(request: Request, file: UploadFile = File(...)):
    # 1. Bild-Daten lesen
    image_bytes = await file.read()
    
    # 2. Kantenerkennung durch edges.py aktivieren
    image_file_like = io.BytesIO(image_bytes)
    image_file_like.seek(0)
    edges_image = prewitt_edge_detection(image_file_like.read())
    
    # 3. Bild als Bytes (PNG-Format) im Speicher speichern
    img_byte_arr = io.BytesIO()
    edges_image.save(img_byte_arr, format='PNG')
    #img_byte_arr.seek(0)
    encoded_img = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
    image_src = f"data:image/png;base64,{encoded_img}"
    # 4. Bild-Bytes als StreamingResponse zurückgeben
    return JSONResponse(content={"processed_image_src": image_src})

    return templates.TemplateResponse("result.html", {
            "request": request,
            "processed_image_src": image_src # Übergeben Sie den Base64-String
    })