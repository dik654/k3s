"""
ComfyUI API Router
이미지 생성 워크플로우, 생성 히스토리
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from io import BytesIO
import httpx
import random
import uuid

router = APIRouter(prefix="/api/comfyui", tags=["comfyui"])

# ComfyUI 서비스 URL
COMFYUI_SERVICE_URL = "http://comfyui-service.ai-workloads.svc.cluster.local:8188"

# In-memory storage for demo
_comfyui_workflows = [
    {
        "id": "txt2img_basic",
        "name": "Text to Image (Basic)",
        "description": "기본 텍스트-이미지 생성 워크플로우",
        "category": "text2img",
        "nodes": ["CheckpointLoader", "CLIPTextEncode", "KSampler", "VAEDecode", "SaveImage"]
    },
    {
        "id": "img2img",
        "name": "Image to Image",
        "description": "이미지 기반 변형 워크플로우",
        "category": "img2img",
        "nodes": ["LoadImage", "VAEEncode", "KSampler", "VAEDecode", "SaveImage"]
    },
    {
        "id": "inpainting",
        "name": "Inpainting",
        "description": "이미지 부분 수정 워크플로우",
        "category": "inpainting",
        "nodes": ["LoadImage", "LoadMask", "VAEEncode", "KSampler", "VAEDecode", "SaveImage"]
    },
    {
        "id": "video_wan22",
        "name": "Video (WAN2.2 5B)",
        "description": "이미지 to 영상 생성 워크플로우",
        "category": "video",
        "nodes": ["LoadImage", "WAN22Model", "VideoSampler", "VideoSave"]
    }
]
_comfyui_generations: List[dict] = []


class ComfyUITxt2ImgRequest(BaseModel):
    """Text to Image 생성 요청"""
    prompt: str
    negative_prompt: str = ""
    steps: int = 20
    cfg_scale: float = 7.0
    width: int = 512
    height: int = 512
    seed: int = -1


class ComfyUIImg2ImgRequest(BaseModel):
    """Image to Image 생성 요청"""
    prompt: str
    negative_prompt: str = ""
    image: str
    strength: float = 0.7
    steps: int = 20
    cfg_scale: float = 7.0
    seed: int = -1


class ComfyUIInpaintingRequest(BaseModel):
    """Inpainting 생성 요청"""
    prompt: str
    negative_prompt: str = ""
    image: str
    mask: str
    steps: int = 20
    cfg_scale: float = 7.0
    seed: int = -1


class ComfyUIVideoRequest(BaseModel):
    """Video 생성 요청"""
    prompt: str
    negative_prompt: str = ""
    start_image: str
    end_image: str
    num_frames: int = 24
    steps: int = 25
    cfg_scale: float = 7.5
    motion_scale: float = 1.0
    seed: int = -1


class ComfyUIGenerateRequest(BaseModel):
    """ComfyUI 이미지 생성 요청"""
    workflow_id: str = "txt2img_basic"
    prompt: str
    negative_prompt: str = ""
    steps: int = 20
    cfg_scale: float = 7.0
    width: int = 512
    height: int = 512
    seed: int = -1


@router.get("/status")
async def get_comfyui_status():
    """ComfyUI 서비스 상태 확인"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("comfyui-service.ai-workloads.svc.cluster.local", 8188))
        sock.close()

        if result == 0:
            return {"status": "running", "connected": True, "url": COMFYUI_SERVICE_URL, "queue_remaining": 0}
        return {"status": "stopped", "connected": False, "queue_remaining": 0}
    except:
        return {"status": "unknown", "connected": False, "queue_remaining": 0}


@router.get("/workflows")
async def get_comfyui_workflows():
    """사용 가능한 워크플로우 목록"""
    return {"workflows": _comfyui_workflows}


@router.get("/generations")
async def get_comfyui_generations():
    """생성 기록 목록"""
    return {"generations": _comfyui_generations}


@router.get("/history")
async def get_comfyui_history():
    """ComfyUI 실행 히스토리"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{COMFYUI_SERVICE_URL}/history")
            if resp.status_code == 200:
                history_data = resp.json()
                history_list = []
                for prompt_id, data in history_data.items():
                    images = []
                    if "outputs" in data:
                        for node_id, output in data["outputs"].items():
                            if "images" in output:
                                images.extend(output["images"])
                    history_list.append({
                        "id": prompt_id,
                        "status": "completed" if data.get("status", {}).get("completed", False) else "running",
                        "images": images,
                        "completed": data.get("status", {}).get("completed", False)
                    })
                return {"history": history_list}
    except:
        pass

    return {"history": []}


@router.get("/outputs")
async def get_comfyui_outputs():
    """생성된 이미지 목록"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{COMFYUI_SERVICE_URL}/history")
            if resp.status_code == 200:
                history_data = resp.json()
                outputs = []
                for prompt_id, data in history_data.items():
                    if "outputs" in data:
                        for node_id, output in data["outputs"].items():
                            if "images" in output:
                                for img in output["images"]:
                                    outputs.append({
                                        "filename": img.get("filename", ""),
                                        "subfolder": img.get("subfolder", ""),
                                        "type": img.get("type", "output"),
                                        "prompt_id": prompt_id,
                                        "url": f"/api/comfyui/view?filename={img.get('filename', '')}&type={img.get('type', 'output')}"
                                    })
                return {"outputs": outputs}
    except:
        pass

    return {"outputs": []}


@router.get("/view")
async def view_comfyui_image(
    filename: str = Query(...),
    subfolder: str = Query(""),
    type: str = Query("output")
):
    """ComfyUI 이미지 조회"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {"filename": filename, "subfolder": subfolder, "type": type}
            resp = await client.get(f"{COMFYUI_SERVICE_URL}/view", params=params)
            if resp.status_code == 200:
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("content-type", "image/png")
                )
    except:
        pass

    raise HTTPException(status_code=404, detail="Image not found")


@router.post("/generate")
async def generate_comfyui_image(request: ComfyUIGenerateRequest):
    """ComfyUI 이미지 생성 큐 추가"""
    workflow_id = request.workflow_id
    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    steps = request.steps
    cfg_scale = request.cfg_scale
    width = request.width
    height = request.height
    seed = request.seed if request.seed >= 0 else random.randint(0, 2**32)

    # ComfyUI workflow prompt 생성
    comfyui_prompt = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": cfg_scale,
                "denoise": 1,
                "latent_image": ["5", 0],
                "model": ["4", 0],
                "negative": ["7", 0],
                "positive": ["6", 0],
                "sampler_name": "euler",
                "scheduler": "normal",
                "seed": seed,
                "steps": steps
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"batch_size": 1, "height": height, "width": width}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["4", 1], "text": prompt_text}
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["4", 1], "text": negative_prompt or "ugly, blurry, low quality"}
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]}
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{COMFYUI_SERVICE_URL}/prompt",
                json={"prompt": comfyui_prompt}
            )
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id", "unknown")

                generation = {
                    "id": prompt_id,
                    "workflow_id": workflow_id,
                    "prompt": prompt_text,
                    "negative_prompt": negative_prompt,
                    "status": "queued",
                    "created_at": datetime.now().isoformat(),
                    "progress": 0,
                    "settings": {
                        "steps": steps,
                        "cfg_scale": cfg_scale,
                        "width": width,
                        "height": height,
                        "seed": seed
                    }
                }
                _comfyui_generations.append(generation)

                return {
                    "generation_id": prompt_id,
                    "status": "queued",
                    "message": "Generation queued successfully"
                }
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to queue prompt")
    except httpx.RequestError as e:
        generation_id = str(uuid.uuid4())[:8]
        generation = {
            "id": generation_id,
            "workflow_id": workflow_id,
            "prompt": prompt_text,
            "negative_prompt": negative_prompt,
            "status": "error",
            "error": f"ComfyUI service unavailable: {str(e)}",
            "created_at": datetime.now().isoformat(),
            "progress": 0
        }
        _comfyui_generations.append(generation)
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


@router.post("/txt2img")
async def generate_txt2img(request: ComfyUITxt2ImgRequest):
    """Text to Image 생성"""
    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    steps = request.steps
    cfg_scale = request.cfg_scale
    width = request.width
    height = request.height
    seed = request.seed if request.seed >= 0 else random.randint(0, 2**32)

    comfyui_prompt = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt_text}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative_prompt or "ugly, blurry, low quality"}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"batch_size": 1, "height": height, "width": width}},
        "5": {"class_type": "KSampler", "inputs": {
            "cfg": cfg_scale, "denoise": 1.0, "latent_image": ["4", 0],
            "model": ["1", 0], "negative": ["3", 0], "positive": ["2", 0],
            "sampler_name": "euler", "scheduler": "normal", "seed": seed, "steps": steps
        }},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "txt2img", "images": ["6", 0]}}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{COMFYUI_SERVICE_URL}/prompt", json={"prompt": comfyui_prompt})
            if response.status_code == 200:
                result = response.json()
                return {"generation_id": result.get("prompt_id"), "status": "queued", "message": "txt2img generation queued"}
            raise HTTPException(status_code=response.status_code, detail="Failed to queue txt2img")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


@router.post("/img2img")
async def generate_img2img(request: ComfyUIImg2ImgRequest):
    """Image to Image 생성"""
    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    image = request.image
    strength = request.strength
    steps = request.steps
    cfg_scale = request.cfg_scale
    seed = request.seed if request.seed >= 0 else random.randint(0, 2**32)

    comfyui_prompt = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image}},
        "3": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt_text}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative_prompt or "ugly, blurry"}},
        "6": {"class_type": "KSampler", "inputs": {
            "cfg": cfg_scale, "denoise": strength, "latent_image": ["3", 0],
            "model": ["1", 0], "negative": ["5", 0], "positive": ["4", 0],
            "sampler_name": "euler", "scheduler": "normal", "seed": seed, "steps": steps
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "img2img", "images": ["7", 0]}}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{COMFYUI_SERVICE_URL}/prompt", json={"prompt": comfyui_prompt})
            if response.status_code == 200:
                result = response.json()
                return {"generation_id": result.get("prompt_id"), "status": "queued", "message": "img2img generation queued"}
            raise HTTPException(status_code=response.status_code, detail="Failed to queue img2img")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


@router.post("/inpainting")
async def generate_inpainting(request: ComfyUIInpaintingRequest):
    """Inpainting 생성"""
    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    image = request.image
    mask = request.mask
    steps = request.steps
    cfg_scale = request.cfg_scale
    seed = request.seed if request.seed >= 0 else random.randint(0, 2**32)

    comfyui_prompt = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image}},
        "3": {"class_type": "LoadImage", "inputs": {"image": mask}},
        "4": {"class_type": "VAEEncodeForInpaint", "inputs": {"pixels": ["2", 0], "vae": ["1", 2], "mask": ["3", 0], "grow_mask_by": 6}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt_text}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative_prompt or "ugly, blurry"}},
        "7": {"class_type": "KSampler", "inputs": {
            "cfg": cfg_scale, "denoise": 1.0, "latent_image": ["4", 0],
            "model": ["1", 0], "negative": ["6", 0], "positive": ["5", 0],
            "sampler_name": "euler", "scheduler": "normal", "seed": seed, "steps": steps
        }},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "inpainting", "images": ["8", 0]}}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{COMFYUI_SERVICE_URL}/prompt", json={"prompt": comfyui_prompt})
            if response.status_code == 200:
                result = response.json()
                return {"generation_id": result.get("prompt_id"), "status": "queued", "message": "inpainting generation queued"}
            raise HTTPException(status_code=response.status_code, detail="Failed to queue inpainting")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


@router.post("/generate-video")
async def generate_video(request: ComfyUIVideoRequest):
    """Video 생성 (WAN2.2)"""
    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    start_image = request.start_image
    end_image = request.end_image
    num_frames = request.num_frames
    steps = request.steps
    cfg_scale = request.cfg_scale
    motion_scale = request.motion_scale
    seed = request.seed if request.seed >= 0 else random.randint(0, 2**32)

    # WAN2.2 video generation workflow (simplified)
    comfyui_prompt = {
        "1": {"class_type": "LoadImage", "inputs": {"image": start_image}},
        "2": {"class_type": "LoadImage", "inputs": {"image": end_image}},
        "3": {"class_type": "WAN22ModelLoader", "inputs": {"model_name": "wan2.2_5b.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 1], "text": prompt_text}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 1], "text": negative_prompt or ""}},
        "6": {"class_type": "WAN22Sampler", "inputs": {
            "model": ["3", 0], "positive": ["4", 0], "negative": ["5", 0],
            "start_image": ["1", 0], "end_image": ["2", 0],
            "num_frames": num_frames, "steps": steps, "cfg": cfg_scale,
            "motion_scale": motion_scale, "seed": seed
        }},
        "7": {"class_type": "SaveVideo", "inputs": {"frames": ["6", 0], "filename_prefix": "video", "fps": 24}}
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{COMFYUI_SERVICE_URL}/prompt", json={"prompt": comfyui_prompt})
            if response.status_code == 200:
                result = response.json()
                return {"generation_id": result.get("prompt_id"), "status": "queued", "message": "video generation queued"}
            raise HTTPException(status_code=response.status_code, detail="Failed to queue video generation")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


@router.delete("/generations/{generation_id}")
async def delete_generation(generation_id: str):
    """생성 기록 삭제"""
    global _comfyui_generations
    _comfyui_generations = [g for g in _comfyui_generations if g["id"] != generation_id]
    return {"success": True, "message": f"Generation {generation_id} deleted"}


@router.get("/object_info")
async def get_object_info():
    """ComfyUI 오브젝트 정보 (노드 타입 등)"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{COMFYUI_SERVICE_URL}/object_info")
            if resp.status_code == 200:
                return resp.json()
    except:
        pass

    return {"error": "ComfyUI not available", "nodes": {}}


@router.get("/models")
async def get_comfyui_models():
    """사용 가능한 모델 목록"""
    # Demo models
    return {
        "checkpoints": ["v1-5-pruned-emaonly.safetensors", "sd-v1-4.ckpt"],
        "loras": [],
        "vaes": ["vae-ft-mse-840000-ema-pruned.safetensors"],
        "mode": "demo"
    }


@router.post("/prompt")
async def queue_prompt(request: dict):
    """ComfyUI에 프롬프트 전송"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{COMFYUI_SERVICE_URL}/prompt", json=request)
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=response.status_code, detail="Failed to queue prompt")
    except httpx.RequestError as e:
        prompt_id = str(uuid.uuid4())
        return {"prompt_id": prompt_id, "mode": "simulation", "note": f"ComfyUI unavailable: {str(e)}"}


@router.get("/queue")
async def get_queue():
    """현재 큐 상태"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{COMFYUI_SERVICE_URL}/queue")
            if resp.status_code == 200:
                return resp.json()
    except:
        pass

    return {"queue_running": [], "queue_pending": []}


@router.get("/pipeline-diagram")
async def get_pipeline_diagram():
    """파이프라인 다이어그램 정보"""
    return {
        "nodes": [
            {"id": "checkpoint", "type": "CheckpointLoaderSimple", "label": "모델 로드", "x": 50, "y": 200},
            {"id": "clip_pos", "type": "CLIPTextEncode", "label": "프롬프트 인코딩", "x": 250, "y": 100},
            {"id": "clip_neg", "type": "CLIPTextEncode", "label": "네거티브 인코딩", "x": 250, "y": 300},
            {"id": "empty_latent", "type": "EmptyLatentImage", "label": "Latent 생성", "x": 250, "y": 200},
            {"id": "ksampler", "type": "KSampler", "label": "샘플링", "x": 450, "y": 200},
            {"id": "vae_decode", "type": "VAEDecode", "label": "VAE 디코드", "x": 650, "y": 200},
            {"id": "save", "type": "SaveImage", "label": "이미지 저장", "x": 850, "y": 200}
        ],
        "edges": [
            {"from": "checkpoint", "to": "clip_pos", "label": "CLIP"},
            {"from": "checkpoint", "to": "clip_neg", "label": "CLIP"},
            {"from": "checkpoint", "to": "ksampler", "label": "MODEL"},
            {"from": "checkpoint", "to": "vae_decode", "label": "VAE"},
            {"from": "clip_pos", "to": "ksampler", "label": "positive"},
            {"from": "clip_neg", "to": "ksampler", "label": "negative"},
            {"from": "empty_latent", "to": "ksampler", "label": "latent"},
            {"from": "ksampler", "to": "vae_decode", "label": "samples"},
            {"from": "vae_decode", "to": "save", "label": "images"}
        ]
    }
