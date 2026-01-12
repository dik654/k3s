"""
RAGflow API Router
RAG 파이프라인 관리 및 지식 베이스 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx

router = APIRouter(prefix="/api/ragflow", tags=["ragflow"])

# RAGflow 서비스 URL
RAGFLOW_URL = "http://ragflow.ai-workloads.svc.cluster.local:9380"
RAGFLOW_WEB_URL = "http://ragflow.ai-workloads.svc.cluster.local:80"

# 데모 모드 플래그
_ragflow_demo_mode = True


class KnowledgeBaseCreate(BaseModel):
    """지식 베이스 생성 요청"""
    name: str
    description: Optional[str] = ""
    embedding_model: str = "BAAI/bge-m3"
    parser_config: Optional[Dict[str, Any]] = None


class DocumentUpload(BaseModel):
    """문서 업로드 요청"""
    kb_id: str
    file_path: str
    chunk_method: str = "naive"


class ChatRequest(BaseModel):
    """RAG 채팅 요청"""
    kb_ids: List[str]
    question: str
    top_k: int = 5
    similarity_threshold: float = 0.5


async def check_ragflow_connection():
    """RAGflow 연결 상태 확인"""
    global _ragflow_demo_mode
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{RAGFLOW_URL}/v1/health")
            if resp.status_code == 200:
                _ragflow_demo_mode = False
                return True
    except:
        pass
    _ragflow_demo_mode = True
    return False


@router.get("/status")
async def get_ragflow_status():
    """RAGflow 서비스 상태 조회"""
    await check_ragflow_connection()

    if not _ragflow_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{RAGFLOW_URL}/v1/health")
                return {
                    "status": "connected",
                    "mode": "production",
                    "api_url": RAGFLOW_URL,
                    "web_url": RAGFLOW_WEB_URL,
                    "health": resp.json() if resp.status_code == 200 else None
                }
        except Exception as e:
            pass

    return {
        "status": "demo",
        "mode": "demo",
        "message": "RAGflow 서비스가 실행되지 않음. 데모 모드로 동작합니다.",
        "external_access": {
            "web_ui": "http://<NODE_IP>:30081",
            "api": "http://<NODE_IP>:30380",
            "ingress_web": "http://ragflow.local",
            "ingress_api": "http://ragflow-api.local"
        },
        "deployment_command": "kubectl apply -f manifests/17-ragflow.yaml"
    }


@router.get("/info")
async def get_ragflow_info():
    """RAGflow 시스템 정보"""
    await check_ragflow_connection()

    return {
        "name": "RAGflow",
        "description": "Open-source RAG Engine for Knowledge Base Management",
        "version": "latest",
        "mode": "production" if not _ragflow_demo_mode else "demo",
        "features": [
            "문서 파싱 (PDF, Word, Excel, PPT, 이미지, 웹 페이지)",
            "지능형 청킹 (Template-based chunking)",
            "Multi-recall 검색 (Vector + Keyword + Graph)",
            "LLM 통합 (OpenAI, vLLM, Ollama 등)",
            "지식 베이스 관리",
            "대화형 RAG 인터페이스"
        ],
        "services": {
            "api": {
                "internal": "http://ragflow.ai-workloads.svc.cluster.local:9380",
                "external_nodeport": "http://<NODE_IP>:30380",
                "ingress": "http://ragflow-api.local"
            },
            "web": {
                "internal": "http://ragflow.ai-workloads.svc.cluster.local:80",
                "external_nodeport": "http://<NODE_IP>:30081",
                "ingress": "http://ragflow.local"
            }
        },
        "dependencies": {
            "mysql": "ragflow-mysql (메타데이터 저장)",
            "redis": "ragflow-redis (캐시)",
            "elasticsearch": "ragflow-elasticsearch (검색 인덱스)",
            "minio": "minio-service (오브젝트 스토리지)"
        }
    }


@router.get("/knowledge-bases")
async def list_knowledge_bases():
    """지식 베이스 목록 조회"""
    await check_ragflow_connection()

    if not _ragflow_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{RAGFLOW_URL}/v1/kb/list")
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass

    # 데모 데이터
    return {
        "knowledge_bases": [
            {
                "id": "demo-kb-1",
                "name": "기술 문서",
                "description": "API 문서, 시스템 설계 가이드",
                "doc_count": 15,
                "chunk_count": 420,
                "embedding_model": "BAAI/bge-m3",
                "status": "ready",
                "created_at": "2024-01-15T10:00:00Z"
            },
            {
                "id": "demo-kb-2",
                "name": "FAQ 데이터",
                "description": "자주 묻는 질문 및 답변",
                "doc_count": 50,
                "chunk_count": 230,
                "embedding_model": "BAAI/bge-m3",
                "status": "ready",
                "created_at": "2024-01-20T14:30:00Z"
            }
        ],
        "total": 2,
        "mode": "demo"
    }


@router.post("/knowledge-bases")
async def create_knowledge_base(request: KnowledgeBaseCreate):
    """새 지식 베이스 생성"""
    await check_ragflow_connection()

    if not _ragflow_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{RAGFLOW_URL}/v1/kb/create",
                    json={
                        "name": request.name,
                        "description": request.description,
                        "embedding_model": request.embedding_model,
                        "parser_config": request.parser_config
                    }
                )
                if resp.status_code in [200, 201]:
                    return resp.json()
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except:
            pass

    return {
        "success": True,
        "message": f"지식 베이스 '{request.name}' 생성됨 (데모 모드)",
        "kb_id": "demo-new-kb",
        "mode": "demo"
    }


@router.get("/knowledge-bases/{kb_id}")
async def get_knowledge_base(kb_id: str):
    """지식 베이스 상세 정보"""
    await check_ragflow_connection()

    if not _ragflow_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{RAGFLOW_URL}/v1/kb/{kb_id}")
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass

    return {
        "id": kb_id,
        "name": "데모 지식 베이스",
        "description": "데모용 지식 베이스입니다",
        "doc_count": 10,
        "chunk_count": 250,
        "embedding_model": "BAAI/bge-m3",
        "parser_config": {
            "chunk_method": "naive",
            "chunk_size": 500,
            "chunk_overlap": 50
        },
        "status": "ready",
        "mode": "demo"
    }


@router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """지식 베이스 삭제"""
    await check_ragflow_connection()

    if not _ragflow_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(f"{RAGFLOW_URL}/v1/kb/{kb_id}")
                if resp.status_code == 200:
                    return {"success": True, "message": f"지식 베이스 '{kb_id}' 삭제됨"}
        except:
            pass

    return {
        "success": True,
        "message": f"지식 베이스 '{kb_id}' 삭제됨 (데모 모드)",
        "mode": "demo"
    }


@router.get("/knowledge-bases/{kb_id}/documents")
async def list_documents(kb_id: str):
    """지식 베이스의 문서 목록"""
    await check_ragflow_connection()

    if not _ragflow_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{RAGFLOW_URL}/v1/kb/{kb_id}/documents")
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass

    return {
        "documents": [
            {
                "id": "doc-1",
                "name": "API_Guide.pdf",
                "type": "pdf",
                "size": 2048576,
                "chunk_count": 45,
                "status": "indexed",
                "created_at": "2024-01-15T10:30:00Z"
            },
            {
                "id": "doc-2",
                "name": "System_Design.docx",
                "type": "docx",
                "size": 512000,
                "chunk_count": 28,
                "status": "indexed",
                "created_at": "2024-01-16T09:00:00Z"
            }
        ],
        "total": 2,
        "kb_id": kb_id,
        "mode": "demo"
    }


@router.post("/chat")
async def rag_chat(request: ChatRequest):
    """RAG 기반 대화"""
    await check_ragflow_connection()

    if not _ragflow_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{RAGFLOW_URL}/v1/chat/completion",
                    json={
                        "kb_ids": request.kb_ids,
                        "question": request.question,
                        "top_k": request.top_k,
                        "similarity_threshold": request.similarity_threshold
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass

    return {
        "answer": f"[데모 응답] '{request.question}'에 대한 답변입니다. 실제 RAGflow 서비스가 연결되면 지식 베이스 기반의 정확한 답변을 제공합니다.",
        "sources": [
            {
                "doc_id": "doc-1",
                "doc_name": "API_Guide.pdf",
                "chunk_id": "chunk-15",
                "content": "관련 문서 내용 미리보기...",
                "score": 0.85
            }
        ],
        "tokens_used": 0,
        "mode": "demo"
    }


@router.get("/models")
async def list_available_models():
    """사용 가능한 LLM 모델 목록"""
    await check_ragflow_connection()

    if not _ragflow_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{RAGFLOW_URL}/v1/models")
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass

    return {
        "models": [
            {
                "id": "vllm-local",
                "name": "vLLM (Local)",
                "type": "chat",
                "provider": "vLLM",
                "endpoint": "http://vllm.ai-workloads.svc.cluster.local:8000",
                "available": True
            },
            {
                "id": "openai-gpt4",
                "name": "GPT-4",
                "type": "chat",
                "provider": "OpenAI",
                "available": False,
                "note": "API 키 필요"
            }
        ],
        "embedding_models": [
            {
                "id": "bge-m3",
                "name": "BGE-M3",
                "dimension": 1024,
                "provider": "BAAI"
            },
            {
                "id": "bge-small",
                "name": "BGE-Small-EN",
                "dimension": 384,
                "provider": "BAAI"
            }
        ],
        "mode": "demo"
    }


@router.get("/parser-methods")
async def get_parser_methods():
    """지원하는 파서 방식 목록"""
    return {
        "methods": [
            {
                "id": "naive",
                "name": "Naive",
                "description": "간단한 텍스트 분할, 빠른 처리"
            },
            {
                "id": "recursive",
                "name": "Recursive",
                "description": "재귀적 문자 기반 분할"
            },
            {
                "id": "qa",
                "name": "Q&A",
                "description": "질문-답변 쌍 추출"
            },
            {
                "id": "table",
                "name": "Table",
                "description": "테이블 구조 보존"
            },
            {
                "id": "paper",
                "name": "Paper",
                "description": "학술 논문 구조 파싱"
            },
            {
                "id": "book",
                "name": "Book",
                "description": "책/장문 문서 파싱"
            },
            {
                "id": "laws",
                "name": "Laws",
                "description": "법률 문서 구조 파싱"
            }
        ],
        "default": "naive"
    }


@router.get("/external-urls")
async def get_external_urls():
    """외부 접속 URL 정보"""
    try:
        import subprocess
        # 노드 IP 조회 시도
        result = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "jsonpath={.items[0].status.addresses[?(@.type=='InternalIP')].address}"],
            capture_output=True, text=True, timeout=5
        )
        node_ip = result.stdout.strip() if result.returncode == 0 else "<NODE_IP>"
    except:
        node_ip = "<NODE_IP>"

    return {
        "ragflow": {
            "name": "RAGflow",
            "description": "RAG 파이프라인 및 지식 베이스 관리",
            "urls": {
                "web_ui": {
                    "nodeport": f"http://{node_ip}:30081",
                    "ingress": "http://ragflow.local",
                    "description": "RAGflow 웹 인터페이스"
                },
                "api": {
                    "nodeport": f"http://{node_ip}:30380",
                    "ingress": "http://ragflow-api.local",
                    "description": "RAGflow REST API"
                },
                "internal": {
                    "api": "http://ragflow.ai-workloads.svc.cluster.local:9380",
                    "web": "http://ragflow.ai-workloads.svc.cluster.local:80"
                }
            }
        },
        "setup_instructions": {
            "step1": "매니페스트 적용: kubectl apply -f manifests/17-ragflow.yaml",
            "step2": "상태 확인: kubectl get pods -n ai-workloads | grep ragflow",
            "step3": f"웹 UI 접속: http://{node_ip}:30081",
            "step4": "기본 계정: admin / admin (첫 로그인 후 변경 필요)"
        },
        "ingress_setup": {
            "description": "Ingress 사용 시 /etc/hosts에 다음 추가",
            "entries": [
                f"{node_ip} ragflow.local",
                f"{node_ip} ragflow-api.local"
            ]
        }
    }
