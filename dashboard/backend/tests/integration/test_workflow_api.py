"""
Integration tests for workflow CRUD API
"""
import pytest
from unittest.mock import patch


class TestWorkflowAPI:
    """Tests for /api/workflows endpoints"""

    def test_create_workflow(self, client, sample_workflow):
        """Test creating a new workflow"""
        response = client.post("/api/workflows", json=sample_workflow)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "workflow" in data
        assert data["workflow"]["name"] == sample_workflow["name"]
        assert "id" in data["workflow"]
        assert "createdAt" in data["workflow"]

    def test_create_workflow_minimal(self, client):
        """Test creating workflow with minimal data"""
        response = client.post("/api/workflows", json={"name": "Minimal Workflow"})
        assert response.status_code == 200

        data = response.json()
        assert data["workflow"]["name"] == "Minimal Workflow"
        assert data["workflow"]["nodes"] == []
        assert data["workflow"]["connections"] == []

    def test_create_workflow_missing_name(self, client):
        """Test creating workflow without name fails"""
        response = client.post("/api/workflows", json={})
        assert response.status_code == 422  # Validation error

    def test_list_workflows_empty(self, client):
        """Test listing workflows when empty"""
        response = client.get("/api/workflows")
        assert response.status_code == 200

        data = response.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)

    def test_list_workflows_with_data(self, client, sample_workflow):
        """Test listing workflows with data"""
        # Create workflow first
        client.post("/api/workflows", json=sample_workflow)

        response = client.get("/api/workflows")
        assert response.status_code == 200

        data = response.json()
        assert len(data["workflows"]) >= 1
        assert data["workflows"][0]["name"] == sample_workflow["name"]
        assert "nodeCount" in data["workflows"][0]

    def test_get_workflow(self, client, sample_workflow):
        """Test getting a specific workflow"""
        # Create workflow first
        create_response = client.post("/api/workflows", json=sample_workflow)
        workflow_id = create_response.json()["workflow"]["id"]

        response = client.get(f"/api/workflows/{workflow_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["workflow"]["id"] == workflow_id
        assert data["workflow"]["name"] == sample_workflow["name"]
        assert len(data["workflow"]["nodes"]) == len(sample_workflow["nodes"])

    def test_get_workflow_not_found(self, client):
        """Test getting non-existent workflow"""
        response = client.get("/api/workflows/non-existent-id")
        assert response.status_code == 404

    def test_update_workflow(self, client, sample_workflow):
        """Test updating a workflow"""
        # Create workflow first
        create_response = client.post("/api/workflows", json=sample_workflow)
        workflow_id = create_response.json()["workflow"]["id"]

        # Update workflow
        update_data = {"name": "Updated Workflow", "description": "Updated description"}
        response = client.put(f"/api/workflows/{workflow_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["workflow"]["name"] == "Updated Workflow"
        assert data["workflow"]["description"] == "Updated description"
        # Nodes should remain unchanged
        assert len(data["workflow"]["nodes"]) == len(sample_workflow["nodes"])

    def test_update_workflow_partial(self, client, sample_workflow):
        """Test partial workflow update"""
        # Create workflow first
        create_response = client.post("/api/workflows", json=sample_workflow)
        workflow_id = create_response.json()["workflow"]["id"]

        # Update only name
        response = client.put(f"/api/workflows/{workflow_id}", json={"name": "New Name"})
        assert response.status_code == 200

        data = response.json()
        assert data["workflow"]["name"] == "New Name"
        # Description should remain unchanged
        assert data["workflow"]["description"] == sample_workflow["description"]

    def test_update_workflow_not_found(self, client):
        """Test updating non-existent workflow"""
        response = client.put("/api/workflows/non-existent-id", json={"name": "Test"})
        assert response.status_code == 404

    def test_delete_workflow(self, client, sample_workflow):
        """Test deleting a workflow"""
        # Create workflow first
        create_response = client.post("/api/workflows", json=sample_workflow)
        workflow_id = create_response.json()["workflow"]["id"]

        # Delete workflow
        response = client.delete(f"/api/workflows/{workflow_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted
        get_response = client.get(f"/api/workflows/{workflow_id}")
        assert get_response.status_code == 404

    def test_delete_workflow_not_found(self, client):
        """Test deleting non-existent workflow"""
        response = client.delete("/api/workflows/non-existent-id")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestWorkflowAPIAsync:
    """Async tests for workflow API"""

    async def test_workflow_crud_async(self, async_client, sample_workflow):
        """Test complete CRUD cycle with async client"""
        # Create
        create_response = await async_client.post("/api/workflows", json=sample_workflow)
        assert create_response.status_code == 200
        workflow_id = create_response.json()["workflow"]["id"]

        # Read
        get_response = await async_client.get(f"/api/workflows/{workflow_id}")
        assert get_response.status_code == 200

        # Update
        update_response = await async_client.put(
            f"/api/workflows/{workflow_id}",
            json={"name": "Async Updated"}
        )
        assert update_response.status_code == 200

        # Delete
        delete_response = await async_client.delete(f"/api/workflows/{workflow_id}")
        assert delete_response.status_code == 200
