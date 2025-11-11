from typing import Dict, List
from models import SHIPPING_COST, TAX_RATE
#from main import app


def create_brownie_item(
    size: str, 
    shape: str, 
    filling: str, 
    toppings: str, 
    quantity: int,
    old_brownies_qty: int = 0
) -> Dict:
    """Erstellt ein Brownie-Objekt für den Warenkorb."""
    return {
        "id": f"item-{len(app.state.cart.get('items', [])) + 1}", # Einfache, temporäre ID
        "name": "Personalisierter Brownie",
        "size": size,
        "shape": shape,
        "filling": filling,
        "toppings": toppings,
        "quantity": quantity,
        "price": 5.90, # Beispielpreis
        "total_price": round(5.90 * quantity, 2),
        "second_chance_qty": old_brownies_qty # Hinzufügen der Second-Chance-Option
    }


def calculate_totals(cart_items: List[Dict]) -> Dict:
    """Berechnet die Gesamtsummen des Warenkorbs (Zwischensumme, Versand, MwSt.)."""
    subtotal = 0.0
    for item in cart_items:
        # HIER MUSS die Neuberechnung des Einzelpreises stattfinden, 
        # da der Artikelpreis in der Session vor dem Aufruf von view_cart veraltet sein kann.
        
        # 1. Neuberechnung des personalisierten Brownie-Preises
        item['total_personalized_price'] = item.get('base_price', 0.0) * item.get('quantity', 0)
        
        # 2. Neuberechnung des Second-Chance-Brownie-Preises (-25%)
        # Angenommen 0.75 ist der Rabattfaktor
        item['total_second_chance_price'] = item.get('base_price', 0.0) * 0.75 * item.get('second_chance_qty', 0)
        
        # Zur Gesamtsumme hinzufügen
        subtotal += item['total_personalized_price'] + item['total_second_chance_price']
        
    shipping = 5.00 if subtotal < 50 and subtotal > 0 else 0.00
    tax_rate = 0.19 
    tax = (subtotal + shipping) * tax_rate
    grand_total = subtotal + shipping + tax
    
    return {
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "grand_total": grand_total
    }

def format_currency(amount: float) -> str:
    return f"{amount:.2f}".replace('.', ',')
