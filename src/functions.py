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
    """Berechnet Subtotal, Tax und Grand Total für die Warenkorb-Artikel."""
    
    total_price_personalized = sum(item["total_personalized_price"] for item in cart_items)
    total_price_second_chance = sum(item["total_second_chance_price"] for item in cart_items)
    subtotal = round(total_price_personalized + total_price_second_chance, 2)
    
    # Versandkosten hinzufügen
    subtotal_with_shipping = round(subtotal + SHIPPING_COST, 2)
    
    # Mehrwertsteuer berechnen (auf den Warenwert + Versand)
    tax = round(subtotal_with_shipping * TAX_RATE, 2)
    
    grand_total = round(subtotal_with_shipping + tax, 2)
    
    return {
        "subtotal": subtotal,
        "shipping": SHIPPING_COST,
        "tax": tax,
        "grand_total": grand_total,
    }
