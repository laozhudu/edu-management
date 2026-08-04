import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

import pytest

from edu_system.api.service_registry import service_registry
from edu_system.database import init_db_with_defaults
from test_data.loader import DataLoader


# Session-scoped fixture: initialize database and load test data once
@pytest.fixture(scope="session", autouse=True)
def init_test_database():
    """Initialize database and load standard test dataset once per test session."""
    init_db_with_defaults()
    loader = DataLoader()
    loader.load_version(version="1.0.0", scenario="test")
    # Re-initialize service registry now that DB has test data
    service_registry._initialized = False
    service_registry.initialize_from_db()
    yield
    # Cleanup if needed
