from typing import List, Dict
from datetime import datetime # Importieren Sie dies oben in functions.py

SECOND_CHANCE_DISCOUNT_RATE = 0.25
QUANTITY_DISCOUNT_5_RATE = 0.05
QUANTITY_DISCOUNT_10_RATE = 0.10

# NEU: Mittwochs-Rabatt
WEDNESDAY_DISCOUNT_RATE = 0.05
WEDNESDAY_WEEKDAY = 2 # Montag=0, Dienstag=1, Mittwoch=2, ...
BASE_PRODUCT_PRICE = 5.90

def calculate_totals(cart_items: List[Dict]) -> Dict:
    # ----------------------------------------------------
    # 1. PRÜFUNG DES MITTWOCHS-RABATTS
    # ----------------------------------------------------
    today = datetime.now()
    is_wednesday = (today.weekday() == WEDNESDAY_WEEKDAY)
    wednesday_discount_applied = 0.0
    
    # ----------------------------------------------------
    # 2. INITIALISIERUNG
    # ----------------------------------------------------
    subtotal_before_tax_discounted = 0.0
    total_discount = 0.0
    
    # ----------------------------------------------------
    # 3. BERECHNUNG PRO ARTIKEL
    # ----------------------------------------------------
    for item in cart_items:
        
        base_price = item.get('base_price', 5.90)
        quantity = item.get('quantity', 0)
        sc_qty = item.get('second_chance_qty', 0)
        
        original_price_personalized = base_price * quantity
        original_price_sc = base_price * sc_qty
        
        # --- A. Mengenrabatt für personalisierte Brownies ---
        unit_discount_rate = 0.0
        if quantity >= 10:
            unit_discount_rate = QUANTITY_DISCOUNT_10_RATE
        elif quantity >= 5:
            unit_discount_rate = QUANTITY_DISCOUNT_5_RATE
            
        personalized_discount = original_price_personalized * unit_discount_rate
        total_personalized_price = original_price_personalized - personalized_discount
        
        # --- B. Second-Chance Rabatt ---
        sc_discount = original_price_sc * SECOND_CHANCE_DISCOUNT_RATE
        total_second_chance_price = original_price_sc - sc_discount
        
        # --- C. Summe für den Artikel ---
        item_total_discount = personalized_discount + sc_discount
        
        # Füge die neu berechneten Preise zum Item-Dictionary hinzu
        item['total_personalized_price'] = round(total_personalized_price, 2)
        item['total_second_chance_price'] = round(total_second_chance_price, 2)
        
        # Summen aktualisieren (vor Mittwochs-Rabatt)
        subtotal_before_tax_discounted += total_personalized_price
        subtotal_before_tax_discounted += total_second_chance_price
        total_discount += item_total_discount
    
    # Runden der Subtotal vor Mittwochs-Rabatt
    subtotal = round(subtotal_before_tax_discounted, 2)

    # ----------------------------------------------------
    # 4. MITTWOCHS-RABATT (auf gesamte Zwischensumme ANWENDEN)
    # ----------------------------------------------------
    if is_wednesday:
        wednesday_discount_applied = subtotal * WEDNESDAY_DISCOUNT_RATE
        subtotal -= wednesday_discount_applied
        total_discount += wednesday_discount_applied
        subtotal = round(subtotal, 2) # Nach Rabatt neu runden
    
    total_discount = round(total_discount, 2)
    
    # ----------------------------------------------------
    # 5. GESAMTKOSTEN (VERSAND & STEUER)
    # ----------------------------------------------------
    shipping = 5.90 
    tax = round(subtotal * 0.19, 2)
    grand_total = round(subtotal + shipping + tax, 2)
    
    print(f"Gesamtrabatt: {total_discount:.2f} EUR")

    return {
        'subtotal_before_tax': subtotal, # Die Subtotal ist nun die rabattierte Subtotal
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'grand_total': grand_total,
        'total_discount': total_discount,
        'is_wednesday_discount_applied': is_wednesday, # Neu: Status des Mittwochs-Rabatts
        'wednesday_discount_amount': round(wednesday_discount_applied, 2) # Neu: Rabattbetrag
    }

def format_currency(amount: float) -> str:
    return f"{amount:.2f}".replace('.', ',')

def enrich_cart_item_prices(item: Dict) -> Dict:
    """Fügt einem Session-Warenkorbartikel alle benötigten Preis-Felder hinzu."""
    base_price = BASE_PRODUCT_PRICE
    qty = item.get("quantity", 0)
    product_id = item.get("product_id", 1) # Default to 1 (Custom)

    # 1. Basispreis setzen (wird für durchgestrichene Preise benötigt)
    item['base_price'] = base_price 
    item['product_name'] = "Wunsch-Brownie" if product_id == 1 else "Second-Chance"

    # 2. Berechnung der Preise (inkl. Rabatte)
    unit_price_after_discount = base_price
    total_discount = 0.0

    if product_id == 1:
        # Mengenrabatt-Logik für Custom Brownies
        if qty >= 10:
            unit_price_after_discount = base_price * 0.90 # 10% Rabatt
        elif qty >= 5:
            unit_price_after_discount = base_price * 0.95 # 5% Rabatt
            
        total_discount = (base_price - unit_price_after_discount) * qty

    elif product_id == 2:
        # Second-Chance Brownies (25% Rabatt)
        unit_price_after_discount = base_price * 0.75
        total_discount = (base_price - unit_price_after_discount) * qty

    # 3. Felder setzen, die von view_cart benötigt werden
    item['personalized_unit_price_after_discount'] = round(unit_price_after_discount, 2)
    item['total_item_price'] = round(unit_price_after_discount * qty, 2)
    item['total_discount'] = round(total_discount, 2)
    
    # Fügt die Second-Chance-Felder der alten Logik hinzu, damit view_cart funktioniert (auf 0 gesetzt)
    item['total_personalized_price'] = item['total_item_price']
    item['total_second_chance_price'] = 0.0

    return item

