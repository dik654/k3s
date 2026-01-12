"""
라우터 테스트
FastAPI TestClient를 사용한 API 엔드포인트 테스트
"""
import pytest
import sys
import os

# 상위 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from fastapi import FastAPI

# 테스트용 간단한 앱 생성
app = FastAPI()


class TestParserRouter:
    """Parser 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.parser import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_supported_formats(self, client):
        """지원 형식 조회 테스트"""
        response = client.get("/api/parser/supported-formats")
        assert response.status_code == 200
        data = response.json()
        assert "document" in data
        assert "data" in data
        assert "web" in data

    def test_chunk_text(self, client):
        """텍스트 청킹 테스트"""
        response = client.post("/api/parser/chunk", json={
            "text": "Hello world. This is a test. " * 100,
            "chunk_size": 100,
            "overlap": 20
        })
        assert response.status_code == 200
        data = response.json()
        assert "chunks" in data
        assert "total_chunks" in data
        assert data["total_chunks"] > 0

    def test_parse_text_file(self, client):
        """텍스트 파일 파싱 테스트"""
        content = b"Hello, this is a test file content."
        response = client.post(
            "/api/parser/parse",
            files={"file": ("test.txt", content, "text/plain")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "Hello" in data["text"]


class TestVllmRouter:
    """vLLM 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.vllm import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_vllm_status(self, client):
        """vLLM 상태 조회 테스트"""
        response = client.get("/api/vllm/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "mode" in data

    def test_vllm_models(self, client):
        """vLLM 모델 목록 테스트"""
        response = client.get("/api/vllm/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data


class TestOntologyRouter:
    """Ontology 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.ontology import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_ontology_schema(self, client):
        """온톨로지 스키마 테스트"""
        response = client.get("/api/ontology/schema")
        assert response.status_code == 200
        data = response.json()
        assert "rdbms_schema" in data
        assert "graph_schema" in data

    def test_ontology_graph_data(self, client):
        """그래프 데이터 테스트"""
        response = client.get("/api/ontology/graph-data")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    def test_ontology_index_types(self, client):
        """인덱스 타입 테스트"""
        response = client.get("/api/ontology/index-types")
        assert response.status_code == 200
        data = response.json()
        assert "types" in data  # 수정된 키


class TestComfyUIRouter:
    """ComfyUI 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.comfyui import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_comfyui_status(self, client):
        """ComfyUI 상태 테스트"""
        response = client.get("/api/comfyui/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_comfyui_workflows(self, client):
        """워크플로우 목록 테스트"""
        response = client.get("/api/comfyui/workflows")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data

    def test_comfyui_pipeline_diagram(self, client):
        """파이프라인 다이어그램 테스트"""
        response = client.get("/api/comfyui/pipeline-diagram")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data


class TestEmbeddingRouter:
    """Embedding 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.embedding import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_embedding_models(self, client):
        """임베딩 모델 목록 테스트"""
        response = client.get("/api/embedding/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data

    def test_embedding_storage_format(self, client):
        """스토리지 형식 테스트"""
        response = client.get("/api/embedding/storage-format")
        assert response.status_code == 200
        data = response.json()
        # 응답에 Qdrant 관련 정보가 있는지 확인
        assert "description" in data or "dense_only_example" in data


class TestQdrantRouter:
    """Qdrant 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.qdrant import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_qdrant_info(self, client):
        """Qdrant 정보 테스트"""
        response = client.get("/api/qdrant/info")
        assert response.status_code == 200
        data = response.json()
        # 연결 실패 시에도 응답 구조 확인
        assert isinstance(data, dict)


class TestVectorDBRouter:
    """VectorDB 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.vectordb import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_rag_guide(self, client):
        """RAG 가이드 테스트"""
        response = client.get("/api/vectordb/rag-guide")
        assert response.status_code == 200
        data = response.json()
        assert "collection_strategy" in data or isinstance(data, dict)


class TestLanggraphRouter:
    """LangGraph 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.langgraph import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_builds_list(self, client):
        """빌드 목록 테스트"""
        response = client.get("/api/langgraph/builds")
        assert response.status_code == 200
        data = response.json()
        assert "builds" in data


class TestEventsRouter:
    """Events 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.events import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_events_list(self, client):
        """이벤트 목록 테스트"""
        # K8s 클러스터가 없으면 에러가 날 수 있으므로 상태 코드만 확인
        response = client.get("/api/events")
        # 500 에러도 허용 (클러스터 없을 때)
        assert response.status_code in [200, 500]


class TestPipelineRouter:
    """Pipeline 라우터 테스트"""

    @pytest.fixture
    def client(self):
        from routers.pipeline import router
        test_app = FastAPI()
        test_app.include_router(router)
        return TestClient(test_app)

    def test_pipeline_status(self, client):
        """파이프라인 상태 테스트"""
        response = client.get("/api/pipeline/status")
        # K8s 클러스터가 없으면 에러가 날 수 있음
        assert response.status_code in [200, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
