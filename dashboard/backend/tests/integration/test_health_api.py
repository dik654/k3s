"""
Integration tests for health check API
"""
import pytest
from unittest.mock import MagicMock, patch


class TestHealthAPI:
    """Tests for /api/health endpoints"""

    def test_health_check(self, client):
        """Test basic health check"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_k8s_health_connected(self, client, mock_k8s_clients):
        """Test K8s health check when connected"""
        mock_k8s_clients["core_v1"].list_namespace.return_value = MagicMock()

        response = client.get("/api/k8s/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"

    def test_k8s_health_disconnected(self, client):
        """Test K8s health check when disconnected"""
        with patch("routers.health.get_k8s_clients") as mock:
            mock.side_effect = Exception("Connection failed")

            response = client.get("/api/k8s/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "disconnected"
            assert "error" in data


@pytest.mark.asyncio
class TestHealthAPIAsync:
    """Async tests for health API"""

    async def test_health_check_async(self, async_client):
        """Test health check with async client"""
        response = await async_client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
