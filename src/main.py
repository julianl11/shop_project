import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, File, UploadFile, Request

from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware
from models import BrownieItem
from fastapi import HTTPException
import io
import base64
import uvicorn
from typing import Optional, List, Dict
from fastapi import Form, status
from fastapi.responses import RedirectResponse
from functions import calculate_totals, format_currency
from database import init_db, AsyncSessionLocal, engine, reset_db, drop_db
import schema
from db_models import Base, Product, OrderItem
from edges import prewitt_edge_detection 
from sqlalchemy.ext.asyncio import AsyncSession

SECRET_KEY = "key"

# ----------------------------------------------------------------------
# HILFSFUNKTION: Initiales Seeding
# ----------------------------------------------------------------------

async def seed_initial_data():
    """Fügt einen initialen Produktdatensatz hinzu, um die Funktionalität zu prüfen."""
    try:
        async with AsyncSessionLocal() as db:
            # Füge einen Test-Brownie hinzu
            new_product = Product(
                name="Der erste Brownie (Auto-Seed)",
                description="Automatisch erstellter Testdatensatz nach DB-Reset.",
                base_price=9.99
            )
            # Prüfe, ob das Produkt bereits existiert (optional, da wir reset_db nutzen)
            # count_stmt = select(func.count()).select_from(Product) # Kommentar: func importen, wenn nötig
            
            db.add(new_product)
            await db.commit()
            await db.refresh(new_product)
            print(f"✅ Initialer Seed-Datensatz für Product erfolgreich hinzugefügt (ID: {new_product.id}).")
    except Exception as e:
        print(f"❌ Fehler beim Seeding der initialen Daten: {e}")

# ----------------------------------------------------------------------
# 1. FastAPI-App-Initialisierung (Lifespan-Konfiguration)
# ----------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Kontextmanager (ersetzt @app.on_event).
    Startup-Code läuft vor dem Yield, Shutdown-Code danach.
    """
    # STARTUP-CODE: Datenbank-Initialisierung
    print("Starte Datenbank-Initialisierung...")
    await init_db()
    print("Datenbank bereit.")

    print("Starte Initiales Seeding der Daten...")
    await seed_initial_data()
    print("Initiales Seeding abgeschlossen.")
    
    # Der Yield-Befehl signalisiert, dass die Anwendung bereit ist, 
    # Anfragen anzunehmen.
    yield
    
    # SHUTDOWN-CODE (falls benötigt, z.B. zum Schließen von Engines)
    # Hier nicht notwendig, da SQLAlchemy die Engine verwaltet.
    pass

# FastAPI-Initialisierung mit dem Lifespan-Manager
app = FastAPI(
    title="Brownie Shop API",
    lifespan=lifespan # ÜBERGABE DES LIFESPAN MANAGERS
)

# ----------------------------------------------------------------------
# 2. Dependency Injection: get_async_db
# ----------------------------------------------------------------------

async def get_async_db():
    """
    Erstellt eine asynchrone Datenbank-Session, stellt sie dem Endpunkt bereit
    und schließt sie nach Beendigung des Requests automatisch (try/finally).
    """
    db = AsyncSessionLocal()
    try:
        # Session an Endpunkt übergeben
        yield db 
    finally:
        # Session nach Beendigung schließen
        await db.close()

# 1. Statische Dateien (für die HTML-Datei, falls nötig)
app.mount("/data", StaticFiles(directory="data"), name="data")
templates = Jinja2Templates(directory="static/")

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
@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

@app.get("/datenschutz", response_class=HTMLResponse)
async def datenschutz(request: Request):
    return templates.TemplateResponse("datenschutz.html", {"request": request})

@app.get("/impressum", response_class=HTMLResponse)
async def impressum(request: Request):
    return templates.TemplateResponse("impressum.html", {"request": request})

# 3. API-Endpunkt für das Haupt-Frontend
@app.get("/shop", response_class=HTMLResponse)
async def shop(request: Request):
    return templates.TemplateResponse("shop.html", {"request": request})

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



# In endpoints.py
@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    """Zeigt den Inhalt des Warenkorbs an."""
    cart_items: List[Dict] = request.session.get("cart", [])
    
    if not cart_items:
        return RedirectResponse(url="/shop", status_code=303) 

    # 'calculate_totals' MUSS angepasst werden, um total_discount zu summieren!
    totals = calculate_totals(cart_items) 
    
    items_html = ""
    for item in cart_items:
        # Hier die neuen Variablen abrufen
        personalized_price = f"{item['total_personalized_price']:.2f}"
        discount = item.get("total_discount", 0.0) # Gesamt-Rabatt des Artikels
        unit_price_discounted = item.get("personalized_unit_price_after_discount", item['base_price'])
        
        # HTML für personalisierten Artikel
        description = (
            f"Größe: <strong>{item['size'].capitalize()}</strong>, "
            f"Form: <strong>{item['shape'].capitalize()}</strong>, "
            f"Füllung: <em>{item['filling'] or 'Keine'}</em>, "
            f"Toppings: <em>{item['toppings'] or 'Keine'}</em>"
        )
        
        # Rabatt-Hinweis hinzufügen
        discount_badge = ""
        if item['quantity'] >= 5:
            # Rabatt-Badge anzeigen
            discount_text = "Mengenrabatt (5%)" if item['quantity'] < 10 else "Mengenrabatt (10%)"
            discount_badge = f"<p class='discount-info'>🎉 {discount_text} angewendet!</p>"
            
            # Preisdarstellung (Alter Preis durchgestrichen)
            original_unit_price_str = f"({item['base_price']:.2f} €)"
            unit_price_info = f"<p class='unit-price-info'>Stück: <span class='original-price'>{original_unit_price_str}</span> {unit_price_discounted:.2f} €</p>"
        else:
             unit_price_info = f"<p class='unit-price-info'>Stück: {item['base_price']:.2f} €</p>"
             

        items_html += f"""
        <div class='cart-item' id='item-{item['id']}'>
            <div class='item-details'>
                <h4>{item['name']} (Art-Nr. {item['id']})</h4>
                <p class='description'>{description}</p>
                {unit_price_info}
                {discount_badge}
            </div>
            
            <form action='/cart/update/{item['id']}' method='post' class='quantity-form'>
                <input type='number' name='new_quantity' value='{item['quantity']}' min='0' class='qty-input'>
                <button type='submit' class='btn-update' title='Menge aktualisieren'>✓</button>
            </form>
            
            <div class='item-price'>
                <strong>{personalized_price} €</strong>
            </div>
            
            <form action='/cart/remove/{item['id']}' method='post' class='remove-form'>
                <button type='submit' class='btn-remove' title='Artikel löschen'>&times;</button>
            </form>
        </div>
        """
        
        # HTML für Second-Chance Brownies
        if item["second_chance_qty"] > 0:
            second_chance_price = f"{item['total_second_chance_price']:.2f}"
            second_chance_unit_price = item['base_price'] * 0.75
            
            sc_id = f"{item['id']}-sc"
            
            items_html += f"""
            <div class='cart-item second-chance' id='item-{sc_id}'>
                <div class='item-details'>
                    <h4 class='second-chance-title'>Second-Chance Brownies (-25% Rabatt!)</h4>
                    <p class='quantity'>Menge: {item['second_chance_qty']} Stück</p>
                    <p class='unit-price-info'>Stück: <span class='original-price'>({item['base_price']:.2f} €)</span> {second_chance_unit_price:.2f} €</p>
                </div>
                <div class='item-price' style='margin-left: auto;'>
                    <strong>{second_chance_price} €</strong>
                </div>
                 <form action='/cart/remove/{item['id']}' method='post' class='remove-form'>
                    <button type='submit' class='btn-remove' title='Second-Chance-Artikel löschen'>&times;</button>
                </form>
            </div>
            """
    
    # ... (Rest der `view_cart` Funktion bleibt gleich, verwendet aber `totals['total_discount']`)
    
    # Hinzufügen der Ersparnis zu den totals, falls calculate_totals dies nicht macht
    total_savings = totals.get('total_discount', 0.0) # Annahme: calculate_totals summiert dies
    
    totals['subtotal'] = format_currency(totals['subtotal'])
    totals['shipping'] = format_currency(totals['shipping'])
    totals['tax'] = format_currency(totals['tax'])
    grand_total_str = format_currency(totals['grand_total'])
    print("aoidnad", total_savings)
    
    # WICHTIG: Die Gesamtersparnis muss an das Template übergeben werden
    return templates.TemplateResponse(
        "cart.html", 
        {
            "request": request, 
            "items_html": items_html, 
            "totals": totals, 
            "grand_total_str": grand_total_str, 
            "cart_items": cart_items, 
            "len_cart_items": len([item for item in cart_items for _ in range(item['quantity'] + item.get('second_chance_qty', 0))]),
            "total_savings_str": format_currency(total_savings) # NEU: Ersparnis
        }
    )


@app.post("/cart/update/{item_id}")
async def update_cart_item(request: Request, item_id: str, new_quantity: int = Form(...)):
    """Aktualisiert die Menge eines bestimmten Artikels im Warenkorb."""
    cart_items: List[Dict] = request.session.get("cart", [])
    
    # Sicherstellen, dass die Menge nicht negativ ist
    if new_quantity < 0:
        new_quantity = 0

    item_found = False
    for item in cart_items:
        # Die Artikel-ID in der Session ist ein String (Art-Nr.)
        if item.get("id") == item_id:
            item_found = True
            
            # WICHTIG: Die Menge der personalisierten Brownies (quantity) aktualisieren
            # und die Menge der Second-Chance Brownies (second_chance_qty) auf 0 setzen, 
            # da sie nicht direkt über dieses Formular bearbeitet werden sollte.
            # Alternativ könnten Sie separate Update-Formulare erstellen, aber hier vereinfachen wir.
            item["quantity"] = new_quantity
            base_price = item.get("base_price", 0.0)
            item["total_personalized_price"] = base_price * new_quantity
            item["total_second_chance_price"] = base_price * 0.75 * item.get("second_chance_qty", 0)

            
            # Falls die Menge auf 0 gesetzt wird, entfernen wir den Artikel
            if new_quantity == 0 and item.get("second_chance_qty", 0) == 0:
                cart_items.remove(item)
                break 


            break

    request.session["cart"] = cart_items
    
    # Zurück zur Warenkorb-Ansicht leiten


    return RedirectResponse(url="/cart", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/cart/remove/{item_id}")
async def remove_cart_item(request: Request, item_id: str):
    """Entfernt einen Artikel vollständig aus dem Warenkorb."""
    cart_items: List[Dict] = request.session.get("cart", [])
    
    # Artikel aus der Liste entfernen
    initial_len = len(cart_items)
    cart_items = [item for item in cart_items if item.get("id") != item_id]
    
    # Wenn ein Second-Chance-Artikel gelöscht werden soll (separate Logik erforderlich), 
    # müsste man hier die Unterscheidung treffen. Wir gehen davon aus, 
    # dass das Löschen des Hauptartikels auch die Second-Chance-Artikel entfernt.

    request.session["cart"] = cart_items
    
    # Zurück zur Warenkorb-Ansicht leiten
    return RedirectResponse(url="/cart", status_code=status.HTTP_303_SEE_OTHER)


def get_total_items_in_cart(cart_items: List[Dict]) -> int:
    """Berechnet die Summe aus 'quantity' und 'second_chance_qty' aller Artikel."""
    total = 0
    for item in cart_items:
        total += item.get("quantity", 0)
        total += item.get("second_chance_qty", 0)
    return total

@app.get("/api/cart/total_items")
async def get_cart_total(request: Request):
    """Gibt die Gesamtzahl der Artikel im Warenkorb zurück."""
    cart_items: List[Dict] = request.session.get("cart", [])
    total_items = get_total_items_in_cart(cart_items)
    
    # Rückgabe als einfaches JSON
    return {"total_items": total_items}

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
        
        # NEUE BERECHNUNGEN hinzufügen
        item_dict["personalized_unit_price_after_discount"] = new_item.personalized_unit_price_after_discount
        item_dict["total_personalized_price"] = new_item.total_personalized_price
        item_dict["total_second_chance_price"] = new_item.total_second_chance_price
        item_dict["total_discount"] = new_item.total_discount # WICHTIG: Gesamt-Ersparnis speichern
        item_dict["base_price"] = new_item.base_price 

        request.session["cart"].append(item_dict)
        
        # Weiterleitung zur Warenkorb-Seite
        return RedirectResponse(url="/cart", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ungültige Bestelldaten: {e}")


@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Zeigt die Checkout-Seite mit Adressformular und Zusammenfassung an."""
    cart_items: List[Dict] = request.session.get("cart", [])

    if not cart_items:
        # Warenkorb leer: Nutzer zurück zur Bestellung schicken
        return RedirectResponse(url="/shop", status_code=303)

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

    totals['subtotal'] = format_currency(totals['subtotal'])
    totals['shipping'] = format_currency(totals['shipping'])
    totals['tax'] = format_currency(totals['tax'])
    totals['grand_total'] = format_currency(totals['grand_total'])

    return templates.TemplateResponse("checkout.html", {"request": request, "summary_html": summary_html, "totals": totals})


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

    return templates.TemplateResponse("confirmation.html", {"request": request, "order_text": order_text})


# ---------------------------------------------------------------------
# 5. Produkte
# ---------------------------------------------------------------------

@app.get("/api/products", response_model=List[schema.Product])
async def read_products(db: AsyncSession = Depends(get_async_db)):
    """Ruft alle Brownie-Produkte aus der Datenbank ab."""
    
    # SQLAlchemy 2.0 Syntax: select-Statement erstellen
    stmt = select(Product)
    
    # Ausführung des Statements über die asynchrone Session
    result = await db.execute(stmt)
    
    # Ergebnisse als Liste von Model-Objekten abrufen
    products = result.scalars().all()
    
    # Rückgabe (FastAPI/Pydantic serialisiert die Objekte automatisch)
    return products

@app.post("/api/products/seed", status_code=status.HTTP_201_CREATED)
async def seed_products(db: AsyncSession = Depends(get_async_db)):
    """Fügt ein Beispielprodukt zur Datenbank hinzu (Manueller Seeding-Endpunkt)."""
    
    new_product = Product(
        name="Luxus Schoko-Trüffel Brownie",
        description="Mit 70% Kakao und Fleur de Sel bestreut.",
        base_price=5.90
    )
    
    # Hinzufügen zum Session-Kontext
    db.add(new_product)
    
    # Transaktion durchführen und persistieren
    await db.commit()
    
    # Datenbankobjekt aktualisieren (optional), um PK zu erhalten
    await db.refresh(new_product) 
    
    return {"message": "Produkt erfolgreich hinzugefügt", "id": new_product.id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
