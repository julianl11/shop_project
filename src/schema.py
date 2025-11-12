from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional

# ----------------------------------------------------------------------
# Basisklasse für Pydantic
# ----------------------------------------------------------------------

class ProductBase(BaseModel):
    """Gemeinsame Attribute für das Produkt."""
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    base_price: Decimal # Entspricht Decimal(10, 2) in SQLAlchemy


class Product(ProductBase):
    """Schema, das zur Rückgabe von Daten aus der Datenbank verwendet wird."""
    # Fügen Sie alle notwendigen Felder hinzu, auch die, die von der DB generiert werden
    id: int

    # WICHTIG: Erlaubt Pydantic, die Daten direkt aus dem SQLAlchemy ORM-Objekt
    # statt aus einem Dict zu lesen (z.B. bei der Rückgabe von Endpunkten).
    class Config:
        from_attributes = True