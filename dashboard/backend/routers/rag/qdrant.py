"""
Qdrant Vector Database API
컬렉션, 벡터 관리
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/qdrant", tags=["qdrant"])

# Qdrant 서비스 URL
QDRANT_URL = "http://qdrant.ai-workloads.svc.cluster.local:6333"

# In-memory storage for demo mode
_qdrant_collections: Dict[str, Dict[str, Any]] = {}
_qdrant_demo_mode = True


async def check_qdrant_connection():
    """Check if Qdrant is available"""
    global _qdrant_demo_mode
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{QDRANT_URL}/collections")
            if resp.status_code == 200:
                _qdrant_demo_mode = False
                return True
    except:
        pass
    _qdrant_demo_mode = True
    return False


@router.get("/info")
async def get_qdrant_info():
    """Get Qdrant server info"""
    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{QDRANT_URL}/collections")
                data = resp.json()
                collections = data.get("result", {}).get("collections", [])
                total_vectors = 0
                for col in collections:
                    col_resp = await client.get(f"{QDRANT_URL}/collections/{col['name']}")
                    col_data = col_resp.json()
                    total_vectors += col_data.get("result", {}).get("vectors_count", 0)

                return {
                    "version": "1.7.0",
                    "collections_count": len(collections),
                    "total_vectors": total_vectors,
                    "mode": "connected"
                }
        except Exception as e:
            pass

    # Demo mode
    return {
        "version": "1.7.0 (demo)",
        "collections_count": len(_qdrant_collections),
        "total_vectors": sum(c.get("vectors_count", 0) for c in _qdrant_collections.values()),
        "mode": "demo"
    }


@router.get("/collections")
async def get_qdrant_collections():
    """Get all collections"""
    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{QDRANT_URL}/collections")
                data = resp.json()
                collections = []
                for col in data.get("result", {}).get("collections", []):
                    col_resp = await client.get(f"{QDRANT_URL}/collections/{col['name']}")
                    col_data = col_resp.json().get("result", {})
                    collections.append({
                        "name": col["name"],
                        "vectors_count": col_data.get("vectors_count", 0),
                        "points_count": col_data.get("points_count", 0),
                        "status": col_data.get("status", "green"),
                        "config": col_data.get("config", {})
                    })
                return {"collections": collections}
        except:
            pass

    # Demo mode
    return {
        "collections": [
            {
                "name": name,
                "vectors_count": data.get("vectors_count", 0),
                "points_count": data.get("points_count", 0),
                "status": "green",
                "config": data.get("config", {})
            }
            for name, data in _qdrant_collections.items()
        ]
    }


@router.post("/collections")
async def create_qdrant_collection(request: dict):
    """Create a new collection"""
    name = request.get("name")
    vector_size = request.get("vector_size", 1536)
    distance = request.get("distance", "Cosine")

    if not name:
        raise HTTPException(status_code=400, detail="Collection name is required")

    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.put(
                    f"{QDRANT_URL}/collections/{name}",
                    json={
                        "vectors": {
                            "size": vector_size,
                            "distance": distance
                        }
                    }
                )
                if resp.status_code in [200, 201]:
                    return {"success": True, "message": f"Collection '{name}' created"}
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except:
            pass

    # Demo mode
    if name in _qdrant_collections:
        raise HTTPException(status_code=400, detail=f"Collection '{name}' already exists")

    _qdrant_collections[name] = {
        "vectors_count": 0,
        "points_count": 0,
        "config": {
            "params": {
                "vectors": {
                    "size": vector_size,
                    "distance": distance
                }
            }
        }
    }
    return {"success": True, "message": f"Collection '{name}' created (demo mode)"}


@router.delete("/collections/{name}")
async def delete_qdrant_collection(name: str):
    """Delete a collection"""
    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(f"{QDRANT_URL}/collections/{name}")
                if resp.status_code == 200:
                    return {"success": True, "message": f"Collection '{name}' deleted"}
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except:
            pass

    # Demo mode
    if name not in _qdrant_collections:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")

    del _qdrant_collections[name]
    return {"success": True, "message": f"Collection '{name}' deleted (demo mode)"}


@router.post("/search")
async def search_qdrant(request: dict):
    """Search vectors in a collection"""
    collection = request.get("collection")
    query_vector = request.get("vector")
    limit = request.get("limit", 10)

    if not collection:
        raise HTTPException(status_code=400, detail="Collection name is required")

    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{QDRANT_URL}/collections/{collection}/points/search",
                    json={
                        "vector": query_vector,
                        "limit": limit,
                        "with_payload": True
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except:
            pass

    # Demo mode - return empty results
    return {
        "result": [],
        "status": "ok",
        "time": 0.001,
        "mode": "demo"
    }
