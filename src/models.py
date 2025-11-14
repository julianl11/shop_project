from pydantic import BaseModel, Field
from typing import Optional, List

class BrownieItem(BaseModel):
    """Definiert die Struktur eines bestellten personalisierten Brownies."""
    # ... (Attribute bleiben unverändert)
    id: str = Field(..., description="Eindeutige ID für den Warenkorb-Artikel.")
    name: str = "Personalisierter Brownie"
    size: str
    shape: str
    filling: Optional[str] = None
    toppings: Optional[str] = None
    quantity: int = Field(ge=1)
    second_chance_qty: int = Field(default=0, ge=0) 
    
    base_price: float = 5.90
    
    @property
    def personalized_unit_price_after_discount(self) -> float:
        """Ermittelt den rabattierten Stückpreis für die personalisierten Brownies."""
        if self.quantity >= 10:
            return self.base_price * 0.90 # 10% Rabatt
        elif self.quantity >= 5:
            return self.base_price * 0.95 # 5% Rabatt
        else:
            return self.base_price # Kein Rabatt
            
    @property
    def total_personalized_price(self) -> float:
        """Berechnet den rabattierten Gesamtpreis für die personalisierten Brownies."""
        return round(self.personalized_unit_price_after_discount * self.quantity, 2)
    
    @property
    def total_discount(self) -> float:
        """Berechnet die gesamte Ersparnis nur für die personalisierten Brownies."""
        original_price = self.base_price * self.quantity
        discounted_price = self.total_personalized_price
        
        # Berücksichtige auch den Rabatt für Second-Chance Brownies
        second_chance_original_price = self.base_price * self.second_chance_qty
        second_chance_discount = second_chance_original_price * 0.25 
        
        # Gesamt-Ersparnis (Mengenrabatt + Second-Chance Rabatt)
        return round(
            (original_price - discounted_price) + second_chance_discount, 
            2
        )
        
    @property
    def total_second_chance_price(self) -> float:
        """Berechnet den Gesamtpreis für die Second-Chance-Brownies (25% Rabatt)."""
        second_chance_price = self.base_price * 0.75 # 25% Rabatt
        return round(second_chance_price * self.second_chance_qty, 2)


SHIPPING_COST = 4.90
TAX_RATE = 0.19 # 19% Mehrwertsteuer