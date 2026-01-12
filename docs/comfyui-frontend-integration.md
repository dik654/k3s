# ComfyUI 프론트엔드 연동 가이드

## 개요

이 문서는 K3s 클러스터에 배포된 ComfyUI와 프론트엔드 애플리케이션을 연동하여 이미지 생성, 동영상 생성 등의 기능을 구현하는 방법을 설명합니다.

## 아키텍처

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend API   │────▶│    ComfyUI      │
│   (React)       │     │   (FastAPI)     │     │   (K3s Pod)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │    RustFS       │
                                               │  (S3 Storage)   │
                                               └─────────────────┘
```

## ComfyUI API 엔드포인트

ComfyUI는 WebSocket과 REST API를 제공합니다.

### 기본 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/` | GET | ComfyUI 웹 인터페이스 |
| `/prompt` | POST | 워크플로우 실행 요청 |
| `/queue` | GET | 현재 큐 상태 조회 |
| `/history` | GET | 실행 히스토리 조회 |
| `/history/{prompt_id}` | GET | 특정 작업 결과 조회 |
| `/view` | GET | 생성된 이미지 조회 |
| `/upload/image` | POST | 이미지 업로드 |
| `/ws` | WebSocket | 실시간 진행 상태 |

## 1. 이미지 생성 큐잉 시스템

### 1.1 워크플로우 JSON 구조

ComfyUI는 노드 기반 워크플로우를 JSON으로 정의합니다.

```javascript
// 기본 텍스트-투-이미지 워크플로우 예시
const text2imgWorkflow = {
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "seed": Math.floor(Math.random() * 1000000),
      "steps": 20,
      "cfg": 7,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": ["4", 0],
      "positive": ["6", 0],
      "negative": ["7", 0],
      "latent_image": ["5", 0]
    }
  },
  "4": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    }
  },
  "5": {
    "class_type": "EmptyLatentImage",
    "inputs": {
      "width": 1024,
      "height": 1024,
      "batch_size": 1
    }
  },
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "a beautiful landscape, masterpiece",
      "clip": ["4", 1]
    }
  },
  "7": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "bad quality, blurry",
      "clip": ["4", 1]
    }
  },
  "8": {
    "class_type": "VAEDecode",
    "inputs": {
      "samples": ["3", 0],
      "vae": ["4", 2]
    }
  },
  "9": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": ["8", 0]
    }
  }
};
```

### 1.2 프론트엔드 이미지 생성 요청

```javascript
// React 컴포넌트에서 이미지 생성 요청
const generateImage = async (prompt, negativePrompt, options = {}) => {
  const {
    width = 1024,
    height = 1024,
    steps = 20,
    cfg = 7,
    seed = Math.floor(Math.random() * 1000000),
    checkpoint = 'sd_xl_base_1.0.safetensors'
  } = options;

  // 워크플로우 생성
  const workflow = createText2ImgWorkflow({
    prompt,
    negativePrompt,
    width,
    height,
    steps,
    cfg,
    seed,
    checkpoint
  });

  try {
    // ComfyUI에 프롬프트 전송
    const response = await fetch('/api/comfyui/prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: workflow,
        client_id: clientId // WebSocket 연결용 클라이언트 ID
      })
    });

    const result = await response.json();
    return result.prompt_id; // 작업 추적용 ID 반환
  } catch (error) {
    console.error('이미지 생성 요청 실패:', error);
    throw error;
  }
};
```

### 1.3 큐 관리 컴포넌트

```javascript
import React, { useState, useEffect } from 'react';

const ImageQueueManager = () => {
  const [queue, setQueue] = useState({ pending: [], running: [] });
  const [history, setHistory] = useState([]);

  // 큐 상태 조회
  const fetchQueueStatus = async () => {
    const response = await fetch('/api/comfyui/queue');
    const data = await response.json();
    setQueue({
      pending: data.queue_pending || [],
      running: data.queue_running || []
    });
  };

  // 히스토리 조회
  const fetchHistory = async () => {
    const response = await fetch('/api/comfyui/history');
    const data = await response.json();
    setHistory(Object.entries(data).map(([id, info]) => ({
      id,
      ...info
    })));
  };

  // 작업 취소
  const cancelJob = async (promptId) => {
    await fetch('/api/comfyui/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delete: [promptId] })
    });
    fetchQueueStatus();
  };

  useEffect(() => {
    fetchQueueStatus();
    fetchHistory();
    const interval = setInterval(fetchQueueStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="queue-manager">
      <div className="queue-section">
        <h3>실행 중 ({queue.running.length})</h3>
        {queue.running.map(job => (
          <div key={job[1]} className="queue-item running">
            <span>ID: {job[1]}</span>
            <div className="progress-indicator" />
          </div>
        ))}
      </div>

      <div className="queue-section">
        <h3>대기 중 ({queue.pending.length})</h3>
        {queue.pending.map((job, index) => (
          <div key={job[1]} className="queue-item pending">
            <span>#{index + 1} - ID: {job[1]}</span>
            <button onClick={() => cancelJob(job[1])}>취소</button>
          </div>
        ))}
      </div>

      <div className="queue-section">
        <h3>완료된 작업</h3>
        {history.slice(0, 10).map(job => (
          <div key={job.id} className="queue-item completed">
            <span>ID: {job.id}</span>
            <span>상태: {job.status?.completed ? '완료' : '실패'}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 1.4 WebSocket을 통한 실시간 진행 상태

```javascript
const useComfyUIWebSocket = (onProgress, onComplete) => {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const clientId = useRef(crypto.randomUUID());

  useEffect(() => {
    const ws = new WebSocket(`ws://comfyui.local/ws?clientId=${clientId.current}`);

    ws.onopen = () => {
      setConnected(true);
      console.log('ComfyUI WebSocket 연결됨');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'progress':
          // 진행률 업데이트
          onProgress?.({
            promptId: message.data.prompt_id,
            node: message.data.node,
            value: message.data.value,
            max: message.data.max,
            percent: (message.data.value / message.data.max) * 100
          });
          break;

        case 'executing':
          // 노드 실행 상태
          if (message.data.node === null) {
            // 워크플로우 완료
            onComplete?.(message.data.prompt_id);
          }
          break;

        case 'executed':
          // 노드 실행 완료 (이미지 데이터 포함)
          console.log('노드 실행 완료:', message.data);
          break;

        case 'status':
          // 큐 상태 업데이트
          console.log('큐 상태:', message.data.status);
          break;
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // 재연결 로직
      setTimeout(() => {
        // 재연결 시도
      }, 3000);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [onProgress, onComplete]);

  return { connected, clientId: clientId.current };
};
```

## 2. 동영상 생성 플로우

### 2.1 AnimateDiff 워크플로우

```javascript
const createAnimateDiffWorkflow = ({
  prompt,
  negativePrompt,
  frames = 16,
  fps = 8,
  width = 512,
  height = 512,
  motionModule = 'mm_sd_v15_v2.ckpt'
}) => {
  return {
    "1": {
      "class_type": "CheckpointLoaderSimple",
      "inputs": {
        "ckpt_name": "realisticVisionV51_v51VAE.safetensors"
      }
    },
    "2": {
      "class_type": "ADE_LoadAnimateDiffModel",
      "inputs": {
        "model_name": motionModule
      }
    },
    "3": {
      "class_type": "ADE_ApplyAnimateDiffModel",
      "inputs": {
        "model": ["1", 0],
        "motion_model": ["2", 0]
      }
    },
    "4": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": prompt,
        "clip": ["1", 1]
      }
    },
    "5": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": negativePrompt,
        "clip": ["1", 1]
      }
    },
    "6": {
      "class_type": "EmptyLatentImage",
      "inputs": {
        "width": width,
        "height": height,
        "batch_size": frames
      }
    },
    "7": {
      "class_type": "KSampler",
      "inputs": {
        "seed": Math.floor(Math.random() * 1000000),
        "steps": 20,
        "cfg": 7,
        "sampler_name": "euler_ancestral",
        "scheduler": "normal",
        "denoise": 1,
        "model": ["3", 0],
        "positive": ["4", 0],
        "negative": ["5", 0],
        "latent_image": ["6", 0]
      }
    },
    "8": {
      "class_type": "VAEDecode",
      "inputs": {
        "samples": ["7", 0],
        "vae": ["1", 2]
      }
    },
    "9": {
      "class_type": "VHS_VideoCombine",
      "inputs": {
        "images": ["8", 0],
        "frame_rate": fps,
        "format": "video/h264-mp4",
        "filename_prefix": "AnimateDiff"
      }
    }
  };
};
```

### 2.2 동영상 생성 컴포넌트

```javascript
const VideoGenerator = () => {
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [videoUrl, setVideoUrl] = useState(null);
  const [settings, setSettings] = useState({
    prompt: '',
    negativePrompt: 'bad quality, blurry, static',
    frames: 16,
    fps: 8,
    width: 512,
    height: 512
  });

  const { connected, clientId } = useComfyUIWebSocket(
    // 진행률 콜백
    (progressData) => {
      setProgress(progressData.percent);
    },
    // 완료 콜백
    async (promptId) => {
      // 결과 가져오기
      const result = await fetchGeneratedVideo(promptId);
      setVideoUrl(result.videoUrl);
      setGenerating(false);
    }
  );

  const generateVideo = async () => {
    if (!connected) {
      alert('ComfyUI에 연결되지 않았습니다');
      return;
    }

    setGenerating(true);
    setProgress(0);
    setVideoUrl(null);

    const workflow = createAnimateDiffWorkflow(settings);

    try {
      const response = await fetch('/api/comfyui/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: workflow,
          client_id: clientId
        })
      });

      const { prompt_id } = await response.json();
      console.log('동영상 생성 시작:', prompt_id);
    } catch (error) {
      console.error('동영상 생성 실패:', error);
      setGenerating(false);
    }
  };

  const fetchGeneratedVideo = async (promptId) => {
    const historyResponse = await fetch(`/api/comfyui/history/${promptId}`);
    const history = await historyResponse.json();

    // 출력 파일 찾기
    const outputs = history[promptId]?.outputs;
    if (outputs) {
      for (const nodeId in outputs) {
        const nodeOutput = outputs[nodeId];
        if (nodeOutput.gifs) {
          const video = nodeOutput.gifs[0];
          return {
            videoUrl: `/api/comfyui/view?filename=${video.filename}&subfolder=${video.subfolder}&type=${video.type}`
          };
        }
      }
    }
    return { videoUrl: null };
  };

  return (
    <div className="video-generator">
      <h2>동영상 생성</h2>

      <div className="settings">
        <div className="form-group">
          <label>프롬프트</label>
          <textarea
            value={settings.prompt}
            onChange={(e) => setSettings({ ...settings, prompt: e.target.value })}
            placeholder="생성할 동영상 설명..."
          />
        </div>

        <div className="form-group">
          <label>네거티브 프롬프트</label>
          <textarea
            value={settings.negativePrompt}
            onChange={(e) => setSettings({ ...settings, negativePrompt: e.target.value })}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>프레임 수</label>
            <select
              value={settings.frames}
              onChange={(e) => setSettings({ ...settings, frames: Number(e.target.value) })}
            >
              <option value={8}>8 프레임 (~1초)</option>
              <option value={16}>16 프레임 (~2초)</option>
              <option value={24}>24 프레임 (~3초)</option>
              <option value={32}>32 프레임 (~4초)</option>
            </select>
          </div>

          <div className="form-group">
            <label>해상도</label>
            <select
              value={`${settings.width}x${settings.height}`}
              onChange={(e) => {
                const [w, h] = e.target.value.split('x').map(Number);
                setSettings({ ...settings, width: w, height: h });
              }}
            >
              <option value="512x512">512x512</option>
              <option value="512x768">512x768 (세로)</option>
              <option value="768x512">768x512 (가로)</option>
            </select>
          </div>
        </div>
      </div>

      <button
        className="generate-btn"
        onClick={generateVideo}
        disabled={generating || !settings.prompt}
      >
        {generating ? '생성 중...' : '동영상 생성'}
      </button>

      {generating && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
          <span>{progress.toFixed(1)}%</span>
        </div>
      )}

      {videoUrl && (
        <div className="result">
          <h3>생성된 동영상</h3>
          <video controls autoPlay loop>
            <source src={videoUrl} type="video/mp4" />
          </video>
          <a href={videoUrl} download className="download-btn">
            다운로드
          </a>
        </div>
      )}
    </div>
  );
};
```

## 3. 백엔드 API 프록시 설정

### 3.1 FastAPI 프록시 엔드포인트

```python
# backend/main.py에 추가

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import httpx

COMFYUI_URL = "http://comfyui-service.comfyui.svc.cluster.local:8188"

comfyui_router = APIRouter(prefix="/api/comfyui", tags=["comfyui"])

@comfyui_router.post("/prompt")
async def queue_prompt(request: dict):
    """ComfyUI에 프롬프트 전송"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COMFYUI_URL}/prompt",
            json=request,
            timeout=30.0
        )
        return response.json()

@comfyui_router.get("/queue")
async def get_queue():
    """큐 상태 조회"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{COMFYUI_URL}/queue")
        return response.json()

@comfyui_router.post("/queue")
async def modify_queue(request: dict):
    """큐 수정 (작업 취소 등)"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COMFYUI_URL}/queue",
            json=request
        )
        return response.json()

@comfyui_router.get("/history")
async def get_history():
    """히스토리 조회"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{COMFYUI_URL}/history")
        return response.json()

@comfyui_router.get("/history/{prompt_id}")
async def get_history_item(prompt_id: str):
    """특정 작업 히스토리 조회"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
        return response.json()

@comfyui_router.get("/view")
async def view_image(filename: str, subfolder: str = "", type: str = "output"):
    """생성된 이미지/동영상 조회"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{COMFYUI_URL}/view",
            params={"filename": filename, "subfolder": subfolder, "type": type}
        )
        return StreamingResponse(
            iter([response.content]),
            media_type=response.headers.get("content-type", "image/png")
        )

@comfyui_router.post("/upload/image")
async def upload_image(file: UploadFile):
    """이미지 업로드"""
    async with httpx.AsyncClient() as client:
        files = {"image": (file.filename, await file.read(), file.content_type)}
        response = await client.post(
            f"{COMFYUI_URL}/upload/image",
            files=files
        )
        return response.json()

# 메인 앱에 라우터 등록
app.include_router(comfyui_router)
```

### 3.2 WebSocket 프록시

```python
from fastapi import WebSocket
import websockets

@app.websocket("/api/comfyui/ws")
async def comfyui_websocket_proxy(websocket: WebSocket, clientId: str = None):
    """ComfyUI WebSocket 프록시"""
    await websocket.accept()

    comfyui_ws_url = f"ws://comfyui-service.comfyui.svc.cluster.local:8188/ws"
    if clientId:
        comfyui_ws_url += f"?clientId={clientId}"

    try:
        async with websockets.connect(comfyui_ws_url) as comfyui_ws:
            async def forward_to_client():
                async for message in comfyui_ws:
                    await websocket.send_text(message)

            async def forward_to_comfyui():
                while True:
                    data = await websocket.receive_text()
                    await comfyui_ws.send(data)

            await asyncio.gather(forward_to_client(), forward_to_comfyui())
    except Exception as e:
        print(f"WebSocket 프록시 오류: {e}")
    finally:
        await websocket.close()
```

## 4. RustFS 연동 (결과물 저장)

### 4.1 생성된 이미지를 S3에 저장

```javascript
const saveToStorage = async (promptId, bucketName = 'generated-images') => {
  // ComfyUI에서 결과 가져오기
  const historyResponse = await fetch(`/api/comfyui/history/${promptId}`);
  const history = await historyResponse.json();

  const outputs = history[promptId]?.outputs;
  const savedFiles = [];

  for (const nodeId in outputs) {
    const nodeOutput = outputs[nodeId];

    // 이미지 저장
    if (nodeOutput.images) {
      for (const image of nodeOutput.images) {
        const imageUrl = `/api/comfyui/view?filename=${image.filename}&subfolder=${image.subfolder}&type=${image.type}`;
        const imageResponse = await fetch(imageUrl);
        const imageBlob = await imageResponse.blob();

        // Base64로 변환
        const base64 = await blobToBase64(imageBlob);

        // RustFS에 저장
        await fetch(`/api/storage/buckets/${bucketName}/objects`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            object_name: `${promptId}/${image.filename}`,
            content: base64.split(',')[1],
            content_type: 'image/png'
          })
        });

        savedFiles.push(`${promptId}/${image.filename}`);
      }
    }

    // 동영상 저장
    if (nodeOutput.gifs) {
      for (const video of nodeOutput.gifs) {
        const videoUrl = `/api/comfyui/view?filename=${video.filename}&subfolder=${video.subfolder}&type=${video.type}`;
        const videoResponse = await fetch(videoUrl);
        const videoBlob = await videoResponse.blob();

        const base64 = await blobToBase64(videoBlob);

        await fetch(`/api/storage/buckets/${bucketName}/objects`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            object_name: `${promptId}/${video.filename}`,
            content: base64.split(',')[1],
            content_type: 'video/mp4'
          })
        });

        savedFiles.push(`${promptId}/${video.filename}`);
      }
    }
  }

  return savedFiles;
};

// Blob을 Base64로 변환하는 헬퍼 함수
const blobToBase64 = (blob) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};
```

## 5. 에러 처리 및 재시도

```javascript
const withRetry = async (fn, maxRetries = 3, delay = 1000) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      console.warn(`시도 ${i + 1} 실패, ${delay}ms 후 재시도...`);
      await new Promise(resolve => setTimeout(resolve, delay));
      delay *= 2; // 지수 백오프
    }
  }
};

// 사용 예시
const result = await withRetry(
  () => generateImage(prompt, negativePrompt),
  3,
  1000
);
```

## 6. 완성된 통합 컴포넌트 예시

```javascript
import React, { useState, useCallback } from 'react';

const ComfyUIIntegration = () => {
  const [mode, setMode] = useState('image'); // 'image' | 'video'
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('bad quality, blurry');
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState([]);

  const { connected, clientId } = useComfyUIWebSocket(
    useCallback((data) => setProgress(data.percent), []),
    useCallback(async (promptId) => {
      // 결과 가져오기 및 저장
      const savedFiles = await saveToStorage(promptId);
      setResults(prev => [...prev, { promptId, files: savedFiles }]);
      setGenerating(false);
      setProgress(0);
    }, [])
  );

  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    setGenerating(true);
    setProgress(0);

    const workflow = mode === 'image'
      ? createText2ImgWorkflow({ prompt, negativePrompt })
      : createAnimateDiffWorkflow({ prompt, negativePrompt });

    await fetch('/api/comfyui/prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: workflow, client_id: clientId })
    });
  };

  return (
    <div className="comfyui-integration">
      <div className="mode-selector">
        <button
          className={mode === 'image' ? 'active' : ''}
          onClick={() => setMode('image')}
        >
          이미지 생성
        </button>
        <button
          className={mode === 'video' ? 'active' : ''}
          onClick={() => setMode('video')}
        >
          동영상 생성
        </button>
      </div>

      <div className="input-section">
        <textarea
          placeholder="프롬프트를 입력하세요..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <textarea
          placeholder="네거티브 프롬프트..."
          value={negativePrompt}
          onChange={(e) => setNegativePrompt(e.target.value)}
        />
      </div>

      <button
        onClick={handleGenerate}
        disabled={generating || !connected || !prompt.trim()}
      >
        {generating ? `생성 중... ${progress.toFixed(0)}%` : '생성하기'}
      </button>

      {generating && (
        <div className="progress">
          <div style={{ width: `${progress}%` }} />
        </div>
      )}

      <div className="results">
        {results.map((result, index) => (
          <div key={index} className="result-item">
            <span>작업 ID: {result.promptId}</span>
            <span>저장된 파일: {result.files.length}개</span>
          </div>
        ))}
      </div>

      <div className="connection-status">
        상태: {connected ? '연결됨' : '연결 끊김'}
      </div>
    </div>
  );
};

export default ComfyUIIntegration;
```

## 참고 자료

- [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)
- [ComfyUI API 문서](https://github.com/comfyanonymous/ComfyUI/blob/master/server.py)
- [AnimateDiff ComfyUI](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved)
