"""
Pytest configuration and fixtures
"""
import os
import sys
import pytest
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport


# ============================================
# App Fixtures
# ============================================

@pytest.fixture(scope="session")
def app():
    """Create FastAPI app for testing"""
    from main import app as fastapi_app
    return fastapi_app


@pytest.fixture
def client(app) -> Generator:
    """Synchronous test client"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client(app) -> AsyncGenerator:
    """Asynchronous test client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================
# Mock Fixtures
# ============================================

@pytest.fixture
def mock_k8s_clients():
    """Mock Kubernetes clients"""
    with patch("core.kubernetes.get_k8s_clients") as mock:
        core_v1 = MagicMock()
        apps_v1 = MagicMock()
        custom_api = MagicMock()
        mock.return_value = (core_v1, apps_v1, custom_api)
        yield {
            "core_v1": core_v1,
            "apps_v1": apps_v1,
            "custom_api": custom_api,
            "mock": mock
        }


@pytest.fixture
def mock_minio_client():
    """Mock MinIO client"""
    with patch("services.minio.MinioService.get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


# ============================================
# Data Fixtures
# ============================================

@pytest.fixture
def sample_workflow():
    """Sample workflow data"""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "nodes": [
            {
                "id": "node-1",
                "type": "llm_agent",
                "name": "LLM Agent",
                "position": {"x": 100, "y": 100},
                "parameters": {"model": "gpt-4"}
            },
            {
                "id": "node-2",
                "type": "output",
                "name": "Output",
                "position": {"x": 300, "y": 100},
                "parameters": {}
            }
        ],
        "connections": [
            {
                "id": "edge-1",
                "source": "node-1",
                "sourceHandle": "output",
                "target": "node-2",
                "targetHandle": "input"
            }
        ]
    }


@pytest.fixture
def sample_benchmark_config():
    """Sample benchmark configuration"""
    return {
        "name": "Test Benchmark",
        "model": "facebook/opt-125m",
        "max_tokens": 100,
        "temperature": 0.7,
        "num_requests": 5,
        "concurrent_requests": 1,
        "test_prompts": ["Hello, world!"]
    }


# ============================================
# Cleanup Fixtures
# ============================================

@pytest.fixture(autouse=True)
def cleanup_test_workflows(tmp_path):
    """Clean up test workflows after each test"""
    import shutil
    from core.config import settings

    # Use temp directory for tests
    original_dir = settings.WORKFLOWS_DIR
    test_dir = str(tmp_path / "workflows")
    os.makedirs(test_dir, exist_ok=True)
    settings.WORKFLOWS_DIR = test_dir

    yield

    # Restore original
    settings.WORKFLOWS_DIR = original_dir
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
