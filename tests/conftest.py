import os
import pytest

# Force SQLite and Mock LLM mode for automated unit tests
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["GROQ_API_KEY"] = ""

from app.database import engine

# Clean up any leftover database file from previous interrupted runs
if os.path.exists("test.db"):
    try:
        os.remove("test.db")
    except Exception:
        pass

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    # Dispose the engine to close all connections in the pool
    engine.dispose()
    # Clean up the test database file after all tests finish
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except Exception as e:
            print(f"Warning: Could not remove test database file: {e}")

