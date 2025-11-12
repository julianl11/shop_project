import asyncio
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
# Die Engine ist das Gateway zur Datenbank. pool_recycle sorgt dafür,
# dass MySQL-Timeout-Probleme (Standard 8h) vermieden werden.
engine = create_async_engine(
    DATABASE_URL, 
    echo=True, # Setzen Sie dies auf True, um SQL-Befehle im Terminal zu sehen
    pool_recycle=3600 # Recycelt Verbindungen nach 1 Stunde
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

# ----------------------------------------------------------------------
# 3. Hilfsfunktion zur Erstellung und Verwaltung der Tabellen
# ----------------------------------------------------------------------

async def init_db():
    """Erstellt alle in Base deklarierten Tabellen in der Datenbank."""
    # Führt die DDL-Anweisungen aus. 'await' ist entscheidend.
    async with engine.begin() as conn:
        # Create tables that do not exist
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

# Beispiel, wie man die DB initialisieren könnte:
# async def main():
#     await init_db()
#if __name__ == "__main__":
#    asyncio.run(reset_db())