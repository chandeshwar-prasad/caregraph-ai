import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility on Render/Supabase
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Helper to automatically create the database if it doesn't exist
def ensure_database_exists():
    try:
        # Parse the connection string to connect to 'postgres' default database first
        # Extract components: postgresql://username:password@host:port/dbname
        if "/" in DATABASE_URL:
            base_url, db_name = DATABASE_URL.rsplit('/', 1)
            # Remove any query parameters from db_name if present
            if "?" in db_name:
                db_name = db_name.split("?")[0]

            # Connect to the default 'postgres' database
            conn = psycopg2.connect(f"{base_url}/postgres")
            conn.autocommit = True
            cur = conn.cursor()

            # Check if target database exists
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cur.fetchone()

            if not exists:
                cur.execute(f"CREATE DATABASE {db_name}")
                print(f"Database '{db_name}' created successfully.")

            cur.close()
            conn.close()

        # Ensure pgvector extension on the target database
        try:
            target_conn = psycopg2.connect(DATABASE_URL)
            target_conn.autocommit = True
            target_cur = target_conn.cursor()
            target_cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            target_cur.close()
            target_conn.close()
        except Exception as ext_e:
            print(f"Note: pgvector extension setup notice: {ext_e}")
    except Exception as e:
        print(f"Warning: Could not automatically verify or create database: {e}")

# Call the helper
ensure_database_exists()

# Initialize SQLAlchemy with pool_pre_ping for cloud connection stability
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
