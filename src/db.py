import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ----------------------------------------------------------------------
# 1. Datenbank-Konfiguration
# WICHTIG: Verwenden Sie hier den aiomysql-Dialekt für Asynchronität.
# Syntax: mysql+aiomysql://<user>:<password>@<host>:<port>/<database>
# Passen Sie die Zugangsdaten entsprechend an!
# ----------------------------------------------------------------------
DATABASE_URL = "mysql+aiomysql://root:@localhost:3306/brownie_shop_db" #mysql://user:pass@hostname:port/db

# Erstellung der Engine:
engine = create_async_engine(
    DATABASE_URL, 
    echo=True, # Setzen Sie dies auf True, um SQL-Befehle im Terminal zu sehen
    pool_recycle=3600 
)

# ----------------------------------------------------------------------
# 2. Session-Factory und Basisklasse
# ----------------------------------------------------------------------

# AsyncSession-Factory: Erstellt asynchrone Datenbank-Sessions
# expire_on_commit=False verhindert das Ablaufen von Objekten nach dem Commit.
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Basisklasse für die Definition von SQLAlchemy-Modellen
class Base(DeclarativeBase):
    pass

from db_models import Product

# ----------------------------------------------------------------------
# 3. Hilfsfunktion zur Erstellung und Verwaltung der Tabellen
# ----------------------------------------------------------------------

async def init_db():
    """Erstellt alle in Base deklarierten Tabellen in der Datenbank."""
    # Führt die DDL-Anweisungen aus. 'await' ist entscheidend.
    async with engine.begin() as conn:
        # Create tables that do not exist
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def drop_db():
    """Löscht alle in Base deklarierten Tabellen aus der Datenbank."""
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)

async def reset_db():
    """Löscht und erstellt alle Tabellen neu (für einen sauberen Start)."""
    print("Starte Datenbank-RESET (Löschen aller Tabellen)...")
    await drop_db()
    print("Datenbank-RESET erfolgreich: Alle Tabellen gelöscht.")
    await init_db()

async def seed_initial_data():
    """Fügt initiale Produkte hinzu."""
    async with AsyncSessionLocal() as db:
        # Custom Brownie (ID 1)
        stmt_1 = select(Product).filter(Product.id == 1)
        res_1 = await db.execute(stmt_1)
        if not res_1.scalars().first():
            db.add(Product(id=1, name="Custom Wunsch-Brownie", description="Ihr personalisiertes Meisterwerk.", base_price=4.50))
        
        # Second-Chance Brownie (ID 2)
        stmt_2 = select(Product).filter(Product.id == 2)
        res_2 = await db.execute(stmt_2)
        if not res_2.scalars().first():
            db.add(Product(id=2, name="Second-Chance Brownie (-25%)", description="Köstliche Reste mit Rabatt.", base_price=4.50))
            
        await db.commit()
        print("✅ Initiales Seeding abgeschlossen: Produkt-IDs 1 und 2 sind bereit.")

# Beispiel, wie man die DB initialisieren könnte:
# async def main():
#     await init_db()
#if __name__ == "__main__":
#    asyncio.run(reset_db())