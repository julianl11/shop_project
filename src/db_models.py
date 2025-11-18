from sqlalchemy import String, Float, ForeignKey, DateTime, Float # Füge Float hinzu, aber nutze Decimal für Währung
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from datetime import datetime
import db

class Customer(db.Base):
    """Datenbank-Modell für einen Kunden."""
    __tablename__ = "customers"
    c_id: Mapped[int] = mapped_column("Kunden_ID", primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    orders: Mapped[List["Order"]] = relationship(back_populates="customer")

class Product(db.Base):
    """Datenbank-Modell für einen Brownie-Produkttyp."""
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    base_price: Mapped[Float] = mapped_column(Float(10, 2))
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="product")

class Order(db.Base):
    """Datenbank-Modell für eine Bestellung."""
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column("Bestell_ID", primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column("Kunden_ID", ForeignKey("customers.Kunden_ID"))
    total_amount: Mapped[Float] = mapped_column("Gesamtsumme", Float(10, 2))
    order_date: Mapped[datetime] = mapped_column("Bestelldatum", DateTime(), default=datetime.now())
    status: Mapped[str] = mapped_column("Status", String(50))
    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order")

class OrderItem(db.Base):
    """Modell für eine Bestellposition mit Personalisierung."""
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.Bestell_ID"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    # second_chance_qty wird nicht mehr benötigt, da SC ein separater OrderItem ist
    
    filling: Mapped[Optional[str]] = mapped_column(String(50))
    toppings: Mapped[Optional[str]] = mapped_column(String(100))
    size: Mapped[Optional[str]] = mapped_column(String(50))
    shape: Mapped[Optional[str]] = mapped_column(String(50))

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")