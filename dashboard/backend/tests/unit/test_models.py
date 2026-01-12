"""
Unit tests for Pydantic models
"""
import pytest
from pydantic import ValidationError

from models.workflow import WorkflowCreate, WorkflowUpdate
from models.cluster import WorkloadAction, NodeInfo, NodeJoinInfo
from models.storage import BucketCreate, ObjectUpload, LifecycleRule
from models.benchmark import BenchmarkConfig, BenchmarkRun


class TestWorkflowModels:
    """Tests for workflow models"""

    def test_workflow_create_valid(self):
        """Test valid workflow creation"""
        data = WorkflowCreate(
            name="Test Workflow",
            description="A test workflow",
            nodes=[{"id": "1", "type": "test"}],
            connections=[]
        )
        assert data.name == "Test Workflow"
        assert data.description == "A test workflow"
        assert len(data.nodes) == 1

    def test_workflow_create_minimal(self):
        """Test workflow with minimal data"""
        data = WorkflowCreate(name="Minimal")
        assert data.name == "Minimal"
        assert data.description == ""
        assert data.nodes == []
        assert data.connections == []

    def test_workflow_create_missing_name(self):
        """Test workflow creation fails without name"""
        with pytest.raises(ValidationError):
            WorkflowCreate()

    def test_workflow_update_partial(self):
        """Test partial workflow update"""
        data = WorkflowUpdate(name="Updated Name")
        assert data.name == "Updated Name"
        assert data.description is None
        assert data.nodes is None

    def test_workflow_update_empty(self):
        """Test empty workflow update is valid"""
        data = WorkflowUpdate()
        assert data.name is None
        assert data.description is None


class TestClusterModels:
    """Tests for cluster models"""

    def test_workload_action_valid(self):
        """Test valid workload action"""
        action = WorkloadAction(action="scale", replicas=3)
        assert action.action == "scale"
        assert action.replicas == 3

    def test_workload_action_defaults(self):
        """Test workload action defaults"""
        action = WorkloadAction(action="start")
        assert action.replicas == 1
        assert action.storage_size_gb is None

    def test_node_info_complete(self):
        """Test complete node info"""
        node = NodeInfo(
            name="node-1",
            status="Ready",
            roles=["master", "worker"],
            cpu_capacity="8",
            cpu_used="2",
            memory_capacity="16Gi",
            memory_used="4Gi",
            gpu_count=2,
            gpu_type="NVIDIA RTX 4090"
        )
        assert node.name == "node-1"
        assert "master" in node.roles
        assert node.gpu_count == 2

    def test_node_join_info_defaults(self):
        """Test node join info defaults"""
        join = NodeJoinInfo(node_ip="192.168.1.100")
        assert join.node_ip == "192.168.1.100"
        assert join.role == "worker"
        assert join.node_name is None


class TestStorageModels:
    """Tests for storage models"""

    def test_bucket_create(self):
        """Test bucket creation"""
        bucket = BucketCreate(name="test-bucket")
        assert bucket.name == "test-bucket"

    def test_object_upload(self):
        """Test object upload model"""
        upload = ObjectUpload(
            object_name="test.txt",
            content="SGVsbG8gV29ybGQ=",  # base64 "Hello World"
            content_type="text/plain"
        )
        assert upload.object_name == "test.txt"
        assert upload.content_type == "text/plain"

    def test_lifecycle_rule(self):
        """Test lifecycle rule"""
        rule = LifecycleRule(
            rule_id="delete-old",
            prefix="logs/",
            expiration_days=30
        )
        assert rule.rule_id == "delete-old"
        assert rule.enabled is True
        assert rule.expiration_days == 30


class TestBenchmarkModels:
    """Tests for benchmark models"""

    def test_benchmark_config_defaults(self):
        """Test benchmark config defaults"""
        config = BenchmarkConfig(name="Test")
        assert config.name == "Test"
        assert config.model == "facebook/opt-125m"
        assert config.max_tokens == 100
        assert config.temperature == 0.7
        assert len(config.test_prompts) == 5

    def test_benchmark_config_custom(self):
        """Test custom benchmark config"""
        config = BenchmarkConfig(
            name="Custom",
            model="meta-llama/Llama-2-7b",
            max_tokens=256,
            concurrent_requests=4
        )
        assert config.model == "meta-llama/Llama-2-7b"
        assert config.max_tokens == 256
        assert config.concurrent_requests == 4

    def test_benchmark_run(self):
        """Test benchmark run"""
        run = BenchmarkRun(config_id="config-123")
        assert run.config_id == "config-123"
        assert run.custom_prompts is None
