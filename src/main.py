import asyncio
import time
from contextlib import asynccontextmanager
import uuid
from fastapi import Depends, FastAPI, File, UploadFile, Request

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware
from models import BrownieItem, SHIPPING_COST, TAX_RATE
from fastapi import HTTPException
import io
import base64
import uvicorn
from typing import Optional, List, Dict
from fastapi import Form, status
from fastapi.responses import RedirectResponse
from functions import calculate_totals, format_currency, enrich_cart_item_prices
from db import init_db, AsyncSessionLocal, engine, reset_db, drop_db, seed_initial_data
import schema
from db_models import Customer, Order, Product, OrderItem
from edges import prewitt_edge_detection 
from sqlalchemy.ext.asyncio import AsyncSession

SECRET_KEY = "key"

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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )

# ----------------------------------------------------------------------
# ENDPUNKTE
# ----------------------------------------------------------------------

@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

@app.get("/datenschutz", response_class=HTMLResponse)
async def datenschutz(request: Request):
    return templates.TemplateResponse("datenschutz.html", {"request": request})

@app.get("/impressum", response_class=HTMLResponse)
async def impressum(request: Request):
    return templates.TemplateResponse("impressum.html", {"request": request})

@app.get("/shop", response_class=HTMLResponse)
async def shop(request: Request):
    return templates.TemplateResponse("shop.html", {"request": request})

@app.post("/upload")
async def process_image(request: Request, file: UploadFile = File(...)):
    image_bytes = await file.read()
    image_file_like = io.BytesIO(image_bytes)
    image_file_like.seek(0)
    edges_image = prewitt_edge_detection(image_file_like.read())
    img_byte_arr = io.BytesIO()
    edges_image.save(img_byte_arr, format='PNG')
    encoded_img = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
    image_src = f"data:image/png;base64,{encoded_img}"
    return JSONResponse(content={"processed_image_src": image_src})


@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    """Zeigt den Inhalt des Warenkorbs an."""
    cart_items: List[Dict] = request.session.get("cart", [])
    
    if not cart_items:
        return RedirectResponse(url="/shop", status_code=303) 

    # WICHTIG: Warenkorb-Items mit Preisen anreichern
    cart_items = [enrich_cart_item_prices(item) for item in cart_items]
    
    totals = calculate_totals(cart_items) 
    total_savings = totals.get('total_discount', 0.0)
    
    items_html = ""
    total_items_count = 0

    for item in cart_items:
        # Hier die korrigierten Variablen abrufen
        item_id = item.get("session_item_id")
        quantity = item.get('quantity', 0)
        total_items_count += quantity

        personalized_price = f"{item['total_item_price']:.2f}"
        discount_amount = item.get("total_discount", 0.0) 
        unit_price_discounted = item.get("personalized_unit_price_after_discount", item['base_price'])
        
        # Beschreibung und Rabatt-Badge
        is_sc = item['product_id'] == 2
        is_qty_discount = item['product_id'] == 1 and discount_amount > 0.01

        if is_sc:
            description = "Restposten, Form & Füllung zufällig"
            discount_badge = "<p class='discount-info'>🎉 **25% Rabatt** angewendet!</p>"
            unit_price_info = f"<p class='unit-price-info'>Stück: <span class='original-price'>({item['base_price']:.2f} €)</span> {unit_price_discounted:.2f} €</p>"
            title_class = "second-chance-title"
            title_text = "Second-Chance Brownies"
        else:
            description = (
                f"Größe: <strong>{item['size'].capitalize()}</strong>, "
                f"Form: <strong>{item['shape'].capitalize()}</strong>, "
                f"Füllung: <em>{item['filling'] or 'Keine'}</em>, "
                f"Toppings: <em>{item['toppings'] or 'Keine'}</em>"
            )
            discount_badge = ""
            if is_qty_discount:
                 discount_text = "Mengenrabatt (5%)" if unit_price_discounted > item['base_price'] * 0.91 else "Mengenrabatt (10%)"
                 discount_badge = f"<p class='discount-info'>🎉 {discount_text} angewendet!</p>"
                 original_unit_price_str = f"({item['base_price']:.2f} €)"
                 unit_price_info = f"<p class='unit-price-info'>Stück: <span class='original-price'>{original_unit_price_str}</span> {unit_price_discounted:.2f} €</p>"
            else:
                 unit_price_info = f"<p class='unit-price-info'>Stück: {item['base_price']:.2f} €</p>"
            title_class = ""
            title_text = item['product_name']


        items_html += f"""
        <div class='cart-item' id='item-{item_id}'>
            <div class='item-details'>
                <h4 class='{title_class}'>{title_text}</h4>
                <p class='description'>{description}</p>
                {unit_price_info}
                {discount_badge}
            </div>
            
            <form action='/cart/update/{item_id}' method='post' class='quantity-form'>
                <input type='hidden' name='product_id' value='{item['product_id']}'>
                <input type='number' name='new_quantity' value='{quantity}' min='0' class='qty-input'>
                <button type='submit' class='btn-update' title='Menge aktualisieren'>✓</button>
            </form>
            
            <div class='item-price'>
                <strong>{personalized_price} €</strong>
            </div>
            
            <form action='/cart/remove/{item_id}' method='post' class='remove-form'>
                <button type='submit' class='btn-remove' title='Artikel löschen'>&times;</button>
            </form>
        </div>
        """
        
    totals['subtotal'] = format_currency(totals['subtotal'])
    totals['shipping'] = format_currency(totals['shipping'])
    totals['tax'] = format_currency(totals['tax'])
    grand_total_str = format_currency(totals['grand_total'])
    
    return templates.TemplateResponse(
        "cart.html", 
        {
            "request": request, 
            "items_html": items_html, 
            "totals": totals, 
            "grand_total_str": grand_total_str, 
            "cart_items": cart_items, 
            "len_cart_items": total_items_count, # Korrekte Zählung aller Einzelstücke
            "total_savings_str": format_currency(total_savings)
        }
    )


@app.post("/cart/update/{session_item_id}")
async def update_cart_item(
    request: Request, 
    session_item_id: str, 
    new_quantity: int = Form(...),
):
    """Aktualisiert die Menge eines bestimmten Artikels im Warenkorb."""
    cart_items: List[Dict] = request.session.get("cart", [])
    
    if new_quantity < 0:
        new_quantity = 0

    item_found = False
    for item in cart_items:
        if item.get("session_item_id") == session_item_id:
            item_found = True
            item["quantity"] = new_quantity
            
            # Falls die Menge auf 0 gesetzt wird, entfernen wir den Artikel
            if new_quantity == 0:
                cart_items.remove(item)
                break 

            break

    request.session["cart"] = cart_items
    
    return RedirectResponse(url="/cart", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/cart/remove/{session_item_id}")
async def remove_cart_item(request: Request, session_item_id: str):
    """Entfernt einen Artikel vollständig aus dem Warenkorb."""
    cart_items: List[Dict] = request.session.get("cart", [])
    
    cart_items = [item for item in cart_items if item.get("session_item_id") != session_item_id]
    
    request.session["cart"] = cart_items
    
    return RedirectResponse(url="/cart", status_code=status.HTTP_303_SEE_OTHER)


def get_total_items_in_cart(cart_items: List[Dict]) -> int:
    """Berechnet die Summe aus 'quantity' aller Artikel."""
    return sum(item.get("quantity", 0) for item in cart_items)

@app.get("/api/cart/total_items")
async def get_cart_total(request: Request):
    """Gibt die Gesamtzahl der Artikel im Warenkorb zurück."""
    cart_items: List[Dict] = request.session.get("cart", [])
    total_items = get_total_items_in_cart(cart_items)
    
    return {"total_items": total_items}

@app.post("/order", response_class=RedirectResponse)
async def add_to_cart(
    request: Request,
    size: str = Form(...),
    shape: str = Form(...),
    filling: Optional[str] = Form(None),
    toppings: Optional[str] = Form(None),
    quantity: int = Form(1, ge=1),
    old_brownies_qty: int = Form(0, ge=0, alias="old_brownies_qty") 
):
    """Speichert den Custom Brownie (product_id=1) und optional Second-Chance (product_id=2) in der Session und leitet weiter."""
    
    if "cart" not in request.session:
        request.session["cart"] = []
    
    cart: List[Dict] = request.session["cart"]
    
    # 1. Hauptprodukt (Custom Brownie)
    if quantity > 0:
        cart.append({
            "session_item_id": str(uuid.uuid4()), 
            "product_id": 1, 
            "quantity": quantity,
            "size": size,
            "shape": shape,
            "filling": filling,
            "toppings": toppings,
        })

    # 2. Second-Chance Brownie (Separater Artikel)
    if old_brownies_qty > 0:
        cart.append({
            "session_item_id": str(uuid.uuid4()), 
            "product_id": 2, 
            "quantity": old_brownies_qty,
            "size": "Restposten",
            "shape": "Zufällig",
            "filling": "N/A",
            "toppings": "N/A",
        })
        
    request.session["cart"] = cart
    
    return RedirectResponse(url="/cart", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Zeigt die Checkout-Seite mit Adressformular und Zusammenfassung an."""
    cart_items: List[Dict] = request.session.get("cart", [])

    if not cart_items:
        return RedirectResponse(url="/shop", status_code=303)
    
    # WICHTIG: Warenkorb-Items mit Preisen anreichern
    cart_items = [enrich_cart_item_prices(item) for item in cart_items]


    totals = calculate_totals(cart_items)
    # Vereinfachte Zusammenfassung für die Checkout-Seite
    summary_html = ""
    for item in cart_items:
        qty_total = item['quantity']
        price_total = item['total_item_price']
        
        details = ""
        if item['product_id'] == 1:
             details = f"({item['size'].capitalize()}, {item['shape'].capitalize()})"

        summary_html += f"""
            <p class="summary-item">
                <span class="qty">x{qty_total}</span> 
                {item['product_name']} {details} (Gesamtpreis: {price_total:.2f} €)
            </p>
        """

    totals_formatted = {k: format_currency(v) for k, v in totals.items()}

    return templates.TemplateResponse("checkout.html", {"request": request, "summary_html": summary_html, "totals": totals_formatted})


@app.post("/checkout", response_class=RedirectResponse)
async def process_checkout(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    name: str = Form(...),
    email: str = Form(...),
    address: str = Form(...),
    zip_code: str = Form(..., alias="zip"),
    payment_method: str = Form(..., alias="payment_method")
):
    """Verarbeitet die Bestellung, speichert alle Daten in der DB und leert den Warenkorb."""
    
    cart_items: List[Dict] = request.session.get("cart", [])

    if not cart_items:
        raise HTTPException(status_code=400, detail="Warenkorb ist leer. Bestellung nicht möglich.")
    
    # 1. Warenkorb-Items mit aktuellen Preisen anreichern
    cart_items = [enrich_cart_item_prices(item) for item in cart_items]
    
    total_amount_db = 0.0
    products_map: Dict[int, Product] = {}
    
    try:
        # 2. KUNDEN-LOGIK
        customer_result = await db.execute(select(Customer).filter(Customer.email == email))
        customer = customer_result.scalars().first()

        if not customer:
            customer = Customer(
                name=name,
                email=email,
                address=f"{address}, {zip_code}", 
            )
            db.add(customer)

        # 3. PRODUKTE ABRUFEN (Für die eigentlichen DB-Preise, obwohl die Session-Preise bereits korrekt sind)
        product_ids = list(set([item["product_id"] for item in cart_items])) # Nur eindeutige IDs
        
        products_result = await db.execute(
            select(Product).filter(Product.id.in_(product_ids))
        )
        for product in products_result.scalars().all():
            products_map[product.id] = product

        # 4. PREISBERECHNUNG (Basierend auf den angereicherten Session-Preisen)
        for item in cart_items:
            # item['total_item_price'] enthält bereits den korrekten Gesamtpreis
            total_amount_db += item['total_item_price']

        # Hinzufügen von Versand und Steuern
        subtotal = total_amount_db
        tax = subtotal * TAX_RATE
        total_amount_db = subtotal + SHIPPING_COST + tax
        total_amount_db = round(total_amount_db, 2)

        # 5. BESTELLUNG (Order) ANLEGEN
        new_order = Order(
            customer=customer, 
            total_amount=total_amount_db, 
            status="Processing"
        )
        db.add(new_order)
        await db.flush() 

        order_id = new_order.id 

        # 6. BESTELLPOSITIONEN (Order Items) ANLEGEN
        for item in cart_items:
            new_item = OrderItem(
                order_id=order_id, 
                product_id=item["product_id"],
                quantity=item.get("quantity", 1),
                
                # Personalisierungsfelder aus dem Session-Item
                size=item.get("size"), 
                shape=item.get("shape"), 
                filling=item.get("filling"), 
                toppings=item.get("toppings") 
            )
            db.add(new_item)
            
        # 7. COMMIT
        await db.commit() 
        print(f"*** Bestelltransaktion {order_id} erfolgreich abgeschlossen. ***")

        # 8. WARENKORB LEEREN und WEITERLEITEN
        del request.session["cart"]
        return RedirectResponse(url=f"/confirmation?order_id={order_id}", status_code=status.HTTP_303_SEE_OTHER)

    except HTTPException:
        await db.rollback() 
        raise
    except Exception as e:
        await db.rollback() 
        print(f"UNERWARTETER Fehler beim Checkout: {e}")
        raise HTTPException(status_code=500, detail="Ein interner Fehler ist während des Bestellvorgangs aufgetreten.")

@app.get("/confirmation", response_class=HTMLResponse)
async def confirmation_page(request: Request, order_id: Optional[str] = None):
    """Bestätigt dem Benutzer den erfolgreichen Abschluss der Bestellung."""
    
    order_text = f"Ihre Bestellnummer lautet: <strong>{order_id}</strong>." if order_id else "Vielen Dank für Ihre Bestellung!"

    return templates.TemplateResponse("confirmation.html", {"request": request, "order_text": order_text})


if __name__ == "__main__":
    uvicorn.run("shop_backend:app", host="0.0.0.0", port=8000, reload=True)