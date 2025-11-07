from pydantic import BaseModel, Field
from typing import Optional, List

class BrownieItem(BaseModel):
    """Definiert die Struktur eines bestellten personalisierten Brownies."""
    id: str = Field(..., description="Eindeutige ID für den Warenkorb-Artikel.")
    name: str = "Personalisierter Brownie"
    size: str
    shape: str
    filling: Optional[str] = None
    toppings: Optional[str] = None
    quantity: int = Field(ge=1)
    # Neu: Hinzufügen der Second-Chance-Menge
    second_chance_qty: int = Field(default=0, ge=0) 
    
    base_price: float = 5.90 # Beispielpreis pro personalisiertem Brownie
    
    @property
    def total_personalized_price(self) -> float:
        """Berechnet den Gesamtpreis für die personalisierten Brownies."""
        return round(self.base_price * self.quantity, 2)
    
    @property
    def total_second_chance_price(self) -> float:
        """Berechnet den Gesamtpreis für die Second-Chance-Brownies (25% Rabatt)."""
        second_chance_price = self.base_price * 0.75 # 25% Rabatt
        return round(second_chance_price * self.second_chance_qty, 2)

SHIPPING_COST = 4.90
TAX_RATE = 0.19 # 19% Mehrwertsteuer