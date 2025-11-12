from sqlalchemy import String, Float, ForeignKey, DateTime, Float # Füge Float hinzu, aber nutze Decimal für Währung
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import datetime
from database import Base # Import der Basisklasse

# ----------------------------------------------------------------------
# 1. Klasse: Customer (Kunde)
# ----------------------------------------------------------------------
class Customer(Base):
    """Datenbank-Modell für einen Kunden (UML: Kunde)."""
    __tablename__ = "customers"

    # Primärschlüssel (UML: Kunden_ID). Python-Attribut: c_id, DB-Spalte: Kunden_ID
    c_id: Mapped[int] = mapped_column("Kunden_ID", primary_key=True, index=True)
    
    # Attribute
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    
    # Relationship zu Bestellungen
    # FIX: Lambda-Funktion, um die Auflösung von 'Order' (weiter unten definiert) zu verzögern.
    orders: Mapped[list["Order"]] = relationship(
        lambda: Order, back_populates="customer"
    )

# ----------------------------------------------------------------------
# 2. Klasse: Order (Bestellung)
# ----------------------------------------------------------------------
class Order(Base):
    """Datenbank-Modell für eine Bestellung (UML: Bestellung)."""
    __tablename__ = "orders"

    # Primärschlüssel (UML: Bestell_ID)
    id: Mapped[int] = mapped_column("Bestell_ID", primary_key=True, index=True)
    
    # Foreign Key zu Customer
    customer_id: Mapped[int] = mapped_column("Kunden_ID", ForeignKey("customers.Kunden_ID"))
    
    # Attribute
    total_amount: Mapped[Float] = mapped_column("Gesamtsumme", Float(10, 2)) # Float für Währung
    order_date: Mapped[datetime] = mapped_column("Bestelldatum", DateTime(), default=datetime.utcnow)
    status: Mapped[str] = mapped_column("Status", String(50))
    
    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="orders")
    
    # FIX: Lambda-Funktion, um die Auflösung von 'OrderItem' (weiter unten definiert) zu verzögern.
    items: Mapped[list["OrderItem"]] = relationship(
        lambda: OrderItem, back_populates="order"
    )


# ----------------------------------------------------------------------
# 3. Klasse: Product (Brownie)
# ----------------------------------------------------------------------
class Product(Base):
    """Datenbank-Modell für einen Brownie-Produkttyp (UML: Produkt)."""
    __tablename__ = "products"

    # Primärschlüssel
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Textfelder
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500))

    # Preis (Float ist ideal für Währung)
    base_price: Mapped[Float] = mapped_column(Float(10, 2))

    # FIX: Lambda-Funktion, um die Auflösung von 'OrderItem' (weiter unten definiert) zu verzögern.
    order_items: Mapped[list["OrderItem"]] = relationship(
        lambda: OrderItem, back_populates="product"
    )


# ----------------------------------------------------------------------
# 4. Assoziationsklasse: OrderItem (Bestellposition)
# ----------------------------------------------------------------------
class OrderItem(Base):
    """Modell für eine Bestellposition mit Personalisierung (UML: Bestellposition)."""
    __tablename__ = "order_items"

    # Primärschlüssel
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Fremdschlüssel zur Bestellungs-Tabelle
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.Bestell_ID"))
    
    # Fremdschlüssel zur Produkt-Tabelle
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    
    # Mengenangaben
    quantity: Mapped[int] = mapped_column(default=1)
    second_chance_qty: Mapped[int] = mapped_column(default=0)
    
    # Personalisierungs-Attribute
    filling: Mapped[Optional[str]] = mapped_column(String(50))
    toppings: Mapped[Optional[str]] = mapped_column(String(100))
    # ... weitere Attribute aus UML: Größe, Form, Bild_Metadaten/Pfad

    # Relationships (Diese Referenzen sind "rückwärts" und sollten nun funktionieren)
    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")