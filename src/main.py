import time
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from models import BrownieItem
from fastapi import HTTPException
import io
import base64
import uvicorn
from typing import Optional, List, Dict
from fastapi import Form
from fastapi.responses import RedirectResponse
from functions import calculate_totals, create_brownie_item
from edges import prewitt_edge_detection # Importiert Ihre Kantenerkennungslogik

SECRET_KEY = "key"

app = FastAPI()

# 1. Statische Dateien (für die HTML-Datei, falls nötig)
app.mount("/data", StaticFiles(directory="data"), name="data")
templates = Jinja2Templates(directory="/Users/julianlorenz/Documents/Fallstudie_website/shop_project/src/static/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="fancy_brownie_session",
    max_age=3600,
)
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

@app.post("/add_to_cart")
async def add_to_cart(
    request: Request,
    size: str = Form(...),
    shape: str = Form(...),
    filling: str = Form(None),
    toppings: str = Form(None),
    quantity: int = Form(...),
    # Achtung: Das Bild-Upload-Feld ('image') wird hier nicht direkt verarbeitet,
    # da es bereits in Ihrem JS-Code separat an /upload gesendet wird.
    # Hier speichern wir nur die Konfigurationsdaten.
    # Wir nehmen an, dass 'old-brownies-qty' im Submit mitkommt (auch wenn es außerhalb des Haupt-Forms ist)
    old_brownies_qty: Optional[int] = Form(0, alias="old_brownies_qty") 
):
    if "cart" not in request.session:
        request.session["cart"] = []

    # Erstelle den neuen Brownie-Artikel
    new_item = create_brownie_item(
        size=size,
        shape=shape,
        filling=filling,
        toppings=toppings,
        quantity=quantity,
        old_brownies_qty=old_brownies_qty if old_brownies_qty else 0 # 0, falls None/null von Form kommt
    )
    
    # Füge den Artikel zum Warenkorb hinzu
    request.session["cart"].append(new_item)

    print(f"Artikel zum Warenkorb hinzugefügt. Aktuelle Warenkorbgröße: {len(request.session['cart'])}")
    
    # 4. Weiterleitung
    # Leite den Benutzer auf die Warenkorb-Seite um (GET /cart)
    return RedirectResponse(url="/cart", status_code=303)

@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    """Zeigt den Inhalt des Warenkorbs an."""
    cart_items: List[Dict] = request.session.get("cart", [])
    
    if not cart_items:
        # Warenkorb leer? Zurück zur Bestellung leiten
        return RedirectResponse(url="/", status_code=303) 
        
    totals = calculate_totals(cart_items)
    grand_total_str = f"{totals['grand_total']:.2f}"
    
    # ... (HTML-Generierung wie zuvor) ...
    # Da der HTML-Code sehr lang ist, wird hier nur die relevante Weiterleitung beibehalten.
    # Der vollständige HTML-Code der /cart-Seite bleibt identisch zu dem in der vorherigen Antwort.
    
    items_html = ""
    for item in cart_items:
        description = (
            f"Größe: <strong>{item['size'].capitalize()}</strong>, "
            f"Form: <strong>{item['shape'].capitalize()}</strong>, "
            f"Füllung: <em>{item['filling'] or 'Keine'}</em>, "
            f"Toppings: <em>{item['toppings'] or 'Keine'}</em>"
        )
        personalized_price = f"{item['total_personalized_price']:.2f}"
        items_html += f"""
        <div class='cart-item'>
            <div class='item-details'>
                <h4>{item['name']} (Art-Nr. {item['id']})</h4>
                <p class='description'>{description}</p>
                <p class='quantity'>Menge: {item['quantity']} Stück @ {item['base_price']:.2f} €</p>
            </div>
            <div class='item-price'>
                <strong>{personalized_price} €</strong>
            </div>
        </div>
        """
        if item["second_chance_qty"] > 0:
            second_chance_price = f"{item['total_second_chance_price']:.2f}"
            second_chance_unit_price = item['base_price'] * 0.75
            items_html += f"""
            <div class='cart-item second-chance'>
                <div class='item-details'>
                    <h4 class='second-chance-title'>Second-Chance Brownies (Nachhaltigkeits-Bonus -25%)</h4>
                    <p class='quantity'>Menge: {item['second_chance_qty']} Stück @ {second_chance_unit_price:.2f} €</p>
                </div>
                <div class='item-price'>
                    <strong>{second_chance_price} €</strong>
                </div>
            </div>
            """

    # HIER IST DIE HTML-GENERIERUNG FÜR DEN WARENKORB (Code aus vorheriger Antwort)
    cart_html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ihr Warenkorb | The Fäncy Brownie Co.</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Lato:wght@300;400&display=swap');
            body {{
                font-family: 'Lato', sans-serif;
                background-color: #f7f3e8;
                color: #3e2723;
                margin: 0;
                padding: 40px 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            header {{ margin-bottom: 40px; text-align: center; }}
            h1 {{
                font-family: 'Playfair Display', serif;
                font-size: 3em;
                color: #5d4037;
                letter-spacing: 2px;
                margin-bottom: 5px;
            }}
            .tagline {{ font-style: italic; color: #8d6e63; margin-top: 0; font-size: 1.1em; }}
            .cart-summary {{
                width: 100%;
                max-width: 800px;
                background: #fff;
                padding: 30px 40px;
                border-radius: 12px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
                text-align: left;
            }}
            h2 {{
                font-family: 'Playfair Display', serif;
                color: #4e342e;
                border-bottom: 2px solid #efebe9;
                padding-bottom: 10px;
                margin-top: 0;
                margin-bottom: 20px;
            }}
            .cart-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 0;
                border-bottom: 1px dashed #efebe9;
            }}
            .cart-item:last-of-type {{ border-bottom: none; }}
            .item-details {{ flex-grow: 1; }}
            .item-details h4 {{ margin: 0 0 5px 0; color: #5d4037; font-size: 1.1em; }}
            .item-details .description {{ font-size: 0.9em; color: #8d6e63; margin: 0; }}
            .item-details .quantity {{ font-size: 0.9em; color: #3e2723; margin: 5px 0 0; font-weight: bold; }}
            .item-price {{ font-size: 1.3em; color: #4e342e; }}
            .second-chance {{ background-color: #fcf8f0; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #bcaaa4; }}
            .second-chance-title {{ color: #7a5a4c !important; font-size: 1em !important; font-weight: bold; }}
            .totals {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 2px solid #5d4037;
                text-align: right;
            }}
            .totals p {{ margin: 5px 0; font-size: 1.1em; }}
            .totals strong {{ font-size: 1.5em; color: #4e342e; }}
            .actions {{
                display: flex;
                justify-content: space-between;
                margin-top: 30px;
            }}
            .btn {{
                padding: 12px 25px;
                border-radius: 6px;
                text-decoration: none;
                font-weight: 700;
                transition: background-color 0.3s;
                font-size: 1em;
            }}
            .btn-back {{
                background-color: #bcaaa4;
                color: white;
            }}
            .btn-back:hover {{ background-color: #8d6e63; }}
            .btn-checkout {{
                background-color: #5d4037;
                color: white;
            }}
            .btn-checkout:hover {{ background-color: #4e342e; }}
            .empty-cart {{ 
                text-align: center; 
                padding: 40px; 
                font-size: 1.2em; 
                color: #8d6e63; 
            }}
            @media (max-width: 600px) {{
                .cart-summary {{ padding: 20px; }}
                .actions {{ flex-direction: column; gap: 15px; }}
                .btn {{ width: 100%; text-align: center; }}
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>Ihr Warenkorb</h1>
            <p class="tagline">Ein Schritt entfernt von Ihrem fäncigen Brownie-Glück.</p>
        </header>

        <div class="cart-summary">
            <h2>Ihre Artikel ({len(cart_items)})</h2>
            
            <div class="item-list">
                {items_html}
            </div>
            
            <div class="totals">
                <p>Zwischensumme: {totals['subtotal']:.2f} €</p>
                <p>Versandkosten: {totals['shipping']:.2f} €</p>
                <p>Geschätzte MwSt (19%): {totals['tax']:.2f} €</p>
                <h3>Gesamtsumme: <strong>{grand_total_str} €</strong></h3>
            </div>
            
            <div class="actions">
                <a href="/" class="btn btn-back">← Weiter bestellen</a>
                <a href="/checkout" class="btn btn-checkout">Zur Kasse gehen</a>
            </div>
        </div>
        
    </body>
    </html>
    """
    
    return HTMLResponse(content=cart_html_template)

@app.post("/order", response_class=RedirectResponse)
async def add_to_cart(
    request: Request,
    size: str = Form(...),
    shape: str = Form(...),
    filling: str = Form(None),
    toppings: str = Form(None),
    quantity: int = Form(1, ge=1),
    old_brownies_qty: int = Form(0, ge=0, alias="old_brownies_qty") 
):
    """Speichert den Brownie in der Session und leitet weiter."""
    
    if "cart" not in request.session:
        request.session["cart"] = []

    new_id = f"item-{len(request.session['cart']) + 1}"

    try:
        new_item = BrownieItem(
            id=new_id,
            size=size,
            shape=shape,
            filling=filling,
            toppings=toppings,
            quantity=quantity,
            second_chance_qty=old_brownies_qty
        )
        
        # Serialisierung der Pydantic-Daten in ein JSON-kompatibles Dict
        item_dict = new_item.model_dump()
        item_dict["total_personalized_price"] = new_item.total_personalized_price
        item_dict["total_second_chance_price"] = new_item.total_second_chance_price
        item_dict["base_price"] = new_item.base_price # Füge Basispreis hinzu

        request.session["cart"].append(item_dict)
        
        # Weiterleitung zur Warenkorb-Seite
        return RedirectResponse(url="/cart", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ungültige Bestelldaten: {e}")

 

    except Exception as e:
        # Fehlerbehandlung, falls Pydantic-Validierung fehlschlägt (z.B. quantity < 1)
        raise HTTPException(status_code=400, detail=f"Ungültige Bestelldaten: {e}")


@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Zeigt die Checkout-Seite mit Adressformular und Zusammenfassung an."""
    cart_items: List[Dict] = request.session.get("cart", [])

    if not cart_items:
        # Warenkorb leer: Nutzer zurück zur Bestellung schicken
        return RedirectResponse(url="/", status_code=303)

    totals = calculate_totals(cart_items)
    
    # Vereinfachte Zusammenfassung für die Checkout-Seite
    summary_html = ""
    for item in cart_items:
        qty_total = item['quantity'] + item.get('second_chance_qty', 0)
        price_total = item['total_personalized_price'] + item.get('total_second_chance_price', 0)
        
        summary_html += f"""
            <p class="summary-item">
                <span class="qty">x{qty_total}</span> 
                {item['size'].capitalize()} Brownie (Gesamtpreis: {price_total:.2f} €)
            </p>
        """

    # Checkout HTML Template
    checkout_html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Checkout | The Fäncy Brownie Co.</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Lato:wght@300;400&display=swap');
            
            body {{
                font-family: 'Lato', sans-serif;
                background-color: #f7f3e8;
                color: #3e2723;
                margin: 0;
                padding: 40px 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .checkout-container {{
                display: flex;
                width: 100%;
                max-width: 1000px;
                gap: 40px;
            }}
            header {{ margin-bottom: 40px; text-align: center; }}
            h1 {{ font-family: 'Playfair Display', serif; color: #5d4037; }}

            .form-section {{
                flex: 2;
                background: #fff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            }}

            .summary-section {{
                flex: 1;
                background: #efebe9; /* Hellbraun/Creme für die Box */
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
                height: fit-content;
                position: sticky;
                top: 40px;
            }}
            .summary-section h3 {{
                font-family: 'Playfair Display', serif;
                color: #4e342e;
                border-bottom: 2px solid #bcaaa4;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            .summary-item {{ font-size: 0.95em; display: flex; justify-content: space-between; margin: 5px 0; }}
            .summary-item .qty {{ font-weight: bold; color: #5d4037; margin-right: 10px; }}

            .total-line {{
                display: flex;
                justify-content: space-between;
                font-weight: bold;
                padding-top: 10px;
                border-top: 1px solid #bcaaa4;
                margin-top: 15px;
                font-size: 1.2em;
            }}

            /* Formular-Stile */
            .form-group label {{ display: block; margin-top: 15px; margin-bottom: 5px; font-weight: bold; color: #5d4037; }}
            .form-group input, .form-group select {{
                width: 100%;
                padding: 10px;
                border: 1px solid #bcaaa4;
                border-radius: 4px;
                box-sizing: border-box;
                background-color: #f7f3e8;
            }}

            input[type="submit"] {{
                width: 100%;
                background-color: #5d4037;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 1.2em;
                font-weight: 700;
                border-radius: 6px;
                cursor: pointer;
                transition: background-color 0.3s;
                margin-top: 30px; 
            }}
            input[type="submit"]:hover {{ background-color: #4e342e; }}

            @media (max-width: 800px) {{
                .checkout-container {{ flex-direction: column; }}
                .summary-section {{ position: static; order: -1; }}
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>Zur Kasse</h1>
            <p class="tagline">Bitte überprüfen Sie Ihre Bestellung und geben Sie Ihre Daten ein.</p>
        </header>

        <div class="checkout-container">
            
            <div class="form-section">
                <h2>Ihre Versandinformationen</h2>
                <form method="POST" action="/checkout">
                    <div class="form-group">
                        <label for="name">Vollständiger Name:</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="email">E-Mail-Adresse:</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="address">Straße und Hausnummer:</label>
                        <input type="text" id="address" name="address" required>
                    </div>
                    <div class="form-group">
                        <label for="zip">PLZ / Ort:</label>
                        <input type="text" id="zip" name="zip" required>
                    </div>
                    
                    <h2>Zahlungsmethode</h2>
                    <div class="form-group">
                        <label for="payment">Methode wählen:</label>
                        <select id="payment" name="payment_method" required>
                            <option value="card">Kreditkarte (Visa/Mastercard)</option>
                            <option value="paypal">PayPal</option>
                            <option value="transfer">Vorkasse (Überweisung)</option>
                        </select>
                    </div>

                    <input type="submit" value="Kostenpflichtig bestellen ({totals['grand_total']:.2f} €)">
                </form>
            </div>

            <div class="summary-section">
                <h3>Bestellübersicht</h3>
                <div class="summary-items-list">
                    {summary_html}
                </div>
                
                <div class="totals-breakdown" style="margin-top: 20px;">
                    <p>Zwischensumme: <span>{totals['subtotal']:.2f} €</span></p>
                    <p>Versandkosten: <span>{totals['shipping']:.2f} €</span></p>
                    <p>Geschätzte MwSt (19%): <span>{totals['tax']:.2f} €</span></p>
                </div>

                <div class="total-line">
                    <span>Gesamtbetrag</span>
                    <span>{totals['grand_total']:.2f} €</span>
                </div>
            </div>

        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=checkout_html_template)


# ---------------------------------------------------------------------
# 4. Bestellabschluss (POST /checkout)
# ---------------------------------------------------------------------

@app.post("/checkout", response_class=RedirectResponse)
async def process_checkout(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    address: str = Form(...),
    zip: str = Form(...),
    payment_method: str = Form(..., alias="payment_method")
):
    """Verarbeitet die Bestellung, leert den Warenkorb und leitet zur Bestätigung weiter."""
    
    cart_items: List[Dict] = request.session.get("cart", [])

    if not cart_items:
        # Warenkorb leer: Fehler oder Weiterleitung zur Startseite
        raise HTTPException(status_code=400, detail="Warenkorb ist leer. Bestellung nicht möglich.")

    # 1. Bestellnummer generieren und Zeitstempel erstellen (Mock)
    order_id = f"FAN-{int(time.time())}"
    totals = calculate_totals(cart_items)

    # 2. Bestellinformationen protokollieren (Mock-Datenbank-Speicherung)
    order_data = {
        "order_id": order_id,
        "customer": {"name": name, "email": email, "address": address, "zip": zip},
        "items": cart_items,
        "totals": totals,
        "payment": payment_method,
        "status": "Processing"
    }

    # In einer echten Anwendung würden Sie hier:
    # - Daten in einer Datenbank speichern.
    # - Zahlung über einen Payment-Gateway (Stripe, PayPal) abwickeln.
    # - Eine E-Mail an den Kunden senden.
    print("-" * 50)
    print(f"!!! BESTELLUNG ABGESCHLOSSEN (ID: {order_id}) !!!")
    print(f"Kunde: {email}, Name: {name}")
    print(f"Gesamtbetrag: {totals['grand_total']:.2f} €")
    print(f"Bezahlung: {payment_method}")
    print("-" * 50)


    # 3. KRITISCH: Warenkorb aus der Session entfernen!
    if "cart" in request.session:
        del request.session["cart"]
        print("Warenkorb wurde erfolgreich geleert.")
    
    # 4. Zur Bestätigungsseite weiterleiten
    # Wir übergeben die Bestellnummer in einem Query-Parameter
    return RedirectResponse(url=f"/confirmation?order_id={order_id}", status_code=303)

@app.get("/confirmation", response_class=HTMLResponse)
async def confirmation_page(request: Request, order_id: Optional[str] = None):
    """Bestätigt dem Benutzer den erfolgreichen Abschluss der Bestellung."""
    
    order_text = f"Ihre Bestellnummer lautet: <strong>{order_id}</strong>." if order_id else "Vielen Dank für Ihre Bestellung!"

    confirmation_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bestätigung | The Fäncy Brownie Co.</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Lato:wght@300;400&display=swap');
            body {{
                font-family: 'Lato', sans-serif;
                background-color: #f7f3e8;
                color: #3e2723;
                margin: 0;
                padding: 100px 20px;
                text-align: center;
            }}
            .confirmation-box {{
                width: 100%;
                max-width: 600px;
                margin: 0 auto;
                background: #fff;
                padding: 50px;
                border-radius: 12px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                border-top: 5px solid #5d4037;
            }}
            h1 {{
                font-family: 'Playfair Display', serif;
                color: #5d4037;
                font-size: 2.5em;
            }}
            p {{ font-size: 1.1em; color: #4e342e; margin-bottom: 25px; }}
            a {{ color: #8d6e63; text-decoration: none; font-weight: bold; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="confirmation-box">
            <h1>🎉 Bestellung erfolgreich!</h1>
            <p>Ihr fänciges Brownie-Meisterwerk ist in Arbeit.</p>
            <p>{order_text}</p>
            <p>Sie erhalten in Kürze eine Bestätigungs-E-Mail.</p>
            <p><a href="/">Zurück zur Startseite</a></p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=confirmation_html)



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
