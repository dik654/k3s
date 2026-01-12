import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Image,
  RefreshCw,
  Play,
  Settings,
  Loader2,
  Download,
  Trash2,
  Eye,
  X,
  Clock,
  CheckCircle,
  AlertCircle,
  Folder,
  Grid,
  List,
  Layers,
  Cpu,
} from 'lucide-react';

const API_BASE = '/api';

interface ComfyUIStatus {
  status: 'running' | 'stopped' | 'error';
  queue_remaining: number;
  current_workflow?: string;
  gpu_memory_used?: number;
  gpu_memory_total?: number;
}

interface WorkflowTemplate {
  id: string;
  name: string;
  description?: string;
  thumbnail?: string;
  category: string;
}

interface Generation {
  id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'error' | 'queued';
  progress?: number;
  output_images?: string[];
  error?: string;
  created_at: string;
  prompt?: string;
  settings?: {
    steps: number;
    cfg_scale: number;
    width: number;
    height: number;
    seed: number;
  };
}

interface OutputImage {
  filename: string;
  subfolder: string;
  type: string;
  prompt_id: string;
  url: string;
}

interface HistoryItem {
  id: string;
  status: string;
  images: Array<{
    filename: string;
    subfolder: string;
    type: string;
  }>;
  completed: boolean;
}

interface ComfyUIPageProps {
  showToast: (message: string, type?: string) => void;
}

export function ComfyUIPage({ showToast }: ComfyUIPageProps) {
  const [status, setStatus] = useState<ComfyUIStatus | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>([]);
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [outputs, setOutputs] = useState<OutputImage[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflowType, setSelectedWorkflowType] = useState<'txt2img' | 'img2img' | 'inpainting' | 'video'>('txt2img');
  const [generating, setGenerating] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [activeTab, setActiveTab] = useState<'generate' | 'gallery' | 'history'>('generate');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Text to Image 설정
  const [txt2imgSettings, setTxt2imgSettings] = useState({
    steps: 20,
    cfg_scale: 7,
    width: 512,
    height: 512,
    seed: -1
  });

  // Image to Image 설정
  const [img2imgInput, setImg2imgInput] = useState<string>('');
  const [img2imgSettings, setImg2imgSettings] = useState({
    strength: 0.7,
    steps: 20,
    cfg_scale: 7,
    seed: -1
  });

  // Inpainting 설정
  const [inpaintingInput, setInpaintingInput] = useState<string>('');
  const [inpaintingMask, setInpaintingMask] = useState<string>('');
  const [inpaintingSettings, setInpaintingSettings] = useState({
    steps: 20,
    cfg_scale: 7,
    seed: -1
  });

  // Video 설정
  const [videoSettings, setVideoSettings] = useState({
    num_frames: 24,
    steps: 25,
    cfg_scale: 7.5,
    motion_scale: 1.0,
    seed: -1
  });
  const [startImage, setStartImage] = useState<string>('');
  const [endImage, setEndImage] = useState<string>('');

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, workflowsRes, generationsRes, outputsRes, historyRes] = await Promise.all([
        axios.get(`${API_BASE}/comfyui/status`).catch(() => ({ data: { status: 'stopped', queue_remaining: 0 } })),
        axios.get(`${API_BASE}/comfyui/workflows`).catch(() => ({ data: { workflows: [] } })),
        axios.get(`${API_BASE}/comfyui/generations`).catch(() => ({ data: { generations: [] } })),
        axios.get(`${API_BASE}/comfyui/outputs`).catch(() => ({ data: { outputs: [] } })),
        axios.get(`${API_BASE}/comfyui/history`).catch(() => ({ data: { history: [] } })),
      ]);
      setStatus(statusRes.data);
      setWorkflows(workflowsRes.data.workflows || []);
      setGenerations(generationsRes.data.generations || []);
      setOutputs(outputsRes.data.outputs || []);
      setHistory(historyRes.data.history || []);
    } catch (error) {
      console.error('ComfyUI fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      showToast('프롬프트를 입력하세요', 'error');
      return;
    }

    setGenerating(true);
    try {
      let endpoint = '';
      let payload: any = { prompt, negative_prompt: negativePrompt };

      switch (selectedWorkflowType) {
        case 'txt2img':
          if (!prompt.trim()) {
            showToast('프롬프트를 입력하세요', 'error');
            return;
          }
          endpoint = `${API_BASE}/comfyui/txt2img`;
          payload = { ...payload, ...txt2imgSettings };
          break;

        case 'img2img':
          if (!img2imgInput) {
            showToast('입력 이미지를 지정하세요', 'error');
            return;
          }
          endpoint = `${API_BASE}/comfyui/img2img`;
          payload = { ...payload, image: img2imgInput, ...img2imgSettings };
          break;

        case 'inpainting':
          if (!inpaintingInput || !inpaintingMask) {
            showToast('입력 이미지와 마스크를 지정하세요', 'error');
            return;
          }
          endpoint = `${API_BASE}/comfyui/inpainting`;
          payload = { ...payload, image: inpaintingInput, mask: inpaintingMask, ...inpaintingSettings };
          break;

        case 'video':
          if (!startImage || !endImage) {
            showToast('시작/종료 이미지를 지정하세요', 'error');
            return;
          }
          endpoint = `${API_BASE}/comfyui/generate-video`;
          payload = { ...payload, start_image: startImage, end_image: endImage, ...videoSettings };
          break;
      }

      await axios.post(endpoint, payload);
      showToast(`${selectedWorkflowType.toUpperCase()} 생성이 시작되었습니다`);
      fetchData();
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      showToast(axiosError.response?.data?.detail || '생성 실패', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const handleDeleteGeneration = async (id: string) => {
    try {
      await axios.delete(`${API_BASE}/comfyui/generations/${id}`);
      showToast('삭제되었습니다');
      fetchData();
    } catch {
      showToast('삭제 실패', 'error');
    }
  };

  const getImageUrl = (filename: string, subfolder: string = '', type: string = 'output') => {
    return `${API_BASE}/comfyui/view?filename=${encodeURIComponent(filename)}&subfolder=${encodeURIComponent(subfolder)}&type=${encodeURIComponent(type)}`;
  };

  const getInputImageUrl = (filename: string) => {
    return `${API_BASE}/comfyui/view?filename=${encodeURIComponent(filename)}&type=input`;
  };

  const renderImageSelector = (currentImage: string, setImage: (img: string) => void, label: string) => {
    const availableImages = outputs.length > 0 ? outputs : [];

    return (
      <div style={{ marginBottom: '12px' }}>
        <label>{label}</label>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
          <input
            type="text"
            value={currentImage}
            onChange={(e) => setImage(e.target.value)}
            placeholder="파일명 입력 또는 아래에서 선택"
            style={{ flex: 1 }}
          />
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => {
              if (availableImages.length > 0) {
                const randomImage = availableImages[Math.floor(Math.random() * availableImages.length)];
                setImage(randomImage.filename);
              }
            }}
          >
            임의 선택
          </button>
        </div>

        {/* Image Preview Grid */}
        {availableImages.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(80px, 1fr))',
            gap: '8px',
            maxHeight: '250px',
            overflowY: 'auto',
            padding: '8px',
            background: 'var(--bg-tertiary)',
            borderRadius: '4px'
          }}>
            {availableImages.map((img, idx) => (
              <div
                key={`${img.prompt_id}-${idx}`}
                onClick={() => setImage(img.filename)}
                style={{
                  cursor: 'pointer',
                  border: currentImage === img.filename ? '2px solid var(--color-accent-blue)' : '1px solid var(--bg-secondary)',
                  borderRadius: '4px',
                  overflow: 'hidden',
                  transition: 'all 0.2s'
                }}
                title={img.filename}
              >
                <img
                  src={getImageUrl(img.filename, img.subfolder, img.type)}
                  alt={img.filename}
                  style={{
                    width: '100%',
                    height: '80px',
                    objectFit: 'cover'
                  }}
                />
              </div>
            ))}
          </div>
        )}

        {availableImages.length === 0 && (
          <div style={{
            padding: '16px',
            background: 'var(--bg-tertiary)',
            borderRadius: '4px',
            textAlign: 'center',
            color: 'var(--text-secondary)',
            fontSize: '12px'
          }}>
            사용 가능한 이미지가 없습니다. 먼저 txt2img로 이미지를 생성하세요.
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <section className="section">
        <div className="card">
          <div className="loading-container">
            <div className="spinner large"></div>
            <p>ComfyUI 정보를 불러오는 중...</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">
          <Image size={24} /> ComfyUI 이미지/동영상 생성
        </h2>
        <div className="benchmark-actions">
          <button className="btn btn-outline" onClick={fetchData}>
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Status Card */}
      <div className="card" style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px', padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className={`vllm-status-dot ${status?.status === 'running' ? '' : 'offline'}`}></div>
            <span style={{ fontWeight: 600 }}>
              ComfyUI: {status?.status === 'running' ? '실행 중' : status?.status === 'error' ? '오류' : '중지됨'}
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-label">대기 작업</span>
            <span className="stat-value">{status?.queue_remaining || 0}</span>
          </div>
          {status?.gpu_memory_used !== undefined && (
            <div className="stat-item">
              <span className="stat-label">GPU 메모리</span>
              <span className="stat-value">
                {((status.gpu_memory_used || 0) / 1024).toFixed(1)}G / {((status.gpu_memory_total || 0) / 1024).toFixed(0)}G
              </span>
            </div>
          )}
          <div className="stat-item">
            <span className="stat-label">생성된 이미지</span>
            <span className="stat-value">{outputs.length}</span>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <button
          className={`btn ${activeTab === 'generate' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('generate')}
        >
          <Play size={16} /> 생성 (txt2img / img2img / inpainting / video)
        </button>
        <button
          className={`btn ${activeTab === 'gallery' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('gallery')}
        >
          <Layers size={16} /> 갤러리 ({outputs.length})
        </button>
        <button
          className={`btn ${activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('history')}
        >
          <Clock size={16} /> 히스토리 ({history.length})
        </button>
      </div>

      {/* Generate Tab */}
      {activeTab === 'generate' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '16px' }}>
          {/* Left: Generation UI */}
          <div>
            {/* Workflow Type Selection */}
            <div className="card" style={{ marginBottom: '16px' }}>
              <div className="card-header">
                <h3><Folder size={18} /> 워크플로우 타입 선택</h3>
              </div>
              <div style={{ padding: '16px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                  <div
                    className={`config-card ${selectedWorkflowType === 'txt2img' ? 'selected' : ''}`}
                    onClick={() => setSelectedWorkflowType('txt2img')}
                    style={{ cursor: 'pointer', padding: '12px', textAlign: 'center' }}
                  >
                    <div style={{ fontSize: 24, marginBottom: 8 }}>📝</div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>Text to Image</div>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>프롬프트로 이미지 생성</div>
                  </div>
                  <div
                    className={`config-card ${selectedWorkflowType === 'img2img' ? 'selected' : ''}`}
                    onClick={() => setSelectedWorkflowType('img2img')}
                    style={{ cursor: 'pointer', padding: '12px', textAlign: 'center' }}
                  >
                    <div style={{ fontSize: 24, marginBottom: 8 }}>🖼️</div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>Image to Image</div>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>이미지를 다른 스타일로 변환</div>
                  </div>
                  <div
                    className={`config-card ${selectedWorkflowType === 'inpainting' ? 'selected' : ''}`}
                    onClick={() => setSelectedWorkflowType('inpainting')}
                    style={{ cursor: 'pointer', padding: '12px', textAlign: 'center' }}
                  >
                    <div style={{ fontSize: 24, marginBottom: 8 }}>🎨</div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>Inpainting</div>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>선택 영역 재생성</div>
                  </div>
                  <div
                    className={`config-card ${selectedWorkflowType === 'video' ? 'selected' : ''}`}
                    onClick={() => setSelectedWorkflowType('video')}
                    style={{ cursor: 'pointer', padding: '12px', textAlign: 'center' }}
                  >
                    <div style={{ fontSize: 24, marginBottom: 8 }}>🎬</div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>Video (WAN2.2)</div>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>영상 생성</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Text to Image Settings */}
            {selectedWorkflowType === 'txt2img' && (
              <div className="card" style={{ marginBottom: '16px' }}>
                <div className="card-header">
                  <h3><Settings size={18} /> 📝 Text to Image 설정</h3>
                </div>
                <div style={{ padding: '16px' }}>
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label>프롬프트</label>
                    <textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="생성할 이미지를 설명하세요..."
                      rows={3}
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label>네거티브 프롬프트</label>
                    <textarea
                      value={negativePrompt}
                      onChange={(e) => setNegativePrompt(e.target.value)}
                      placeholder="피하고 싶은 요소..."
                      rows={2}
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                    <div className="form-group">
                      <label>Steps</label>
                      <input
                        type="number"
                        value={txt2imgSettings.steps}
                        onChange={(e) => setTxt2imgSettings({ ...txt2imgSettings, steps: parseInt(e.target.value) || 20 })}
                      />
                    </div>
                    <div className="form-group">
                      <label>CFG Scale</label>
                      <input
                        type="number"
                        step="0.5"
                        value={txt2imgSettings.cfg_scale}
                        onChange={(e) => setTxt2imgSettings({ ...txt2imgSettings, cfg_scale: parseFloat(e.target.value) || 7 })}
                      />
                    </div>
                    <div className="form-group">
                      <label>Width</label>
                      <input
                        type="number"
                        step="64"
                        value={txt2imgSettings.width}
                        onChange={(e) => setTxt2imgSettings({ ...txt2imgSettings, width: parseInt(e.target.value) || 512 })}
                      />
                    </div>
                    <div className="form-group">
                      <label>Height</label>
                      <input
                        type="number"
                        step="64"
                        value={txt2imgSettings.height}
                        onChange={(e) => setTxt2imgSettings({ ...txt2imgSettings, height: parseInt(e.target.value) || 512 })}
                      />
                    </div>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={handleGenerate}
                    disabled={generating || !prompt.trim() || status?.status !== 'running'}
                    style={{ marginTop: '16px', width: '100%' }}
                  >
                    {generating ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
                    {generating ? '생성 중...' : '이미지 생성'}
                  </button>
                </div>
              </div>
            )}

            {/* Image to Image Settings */}
            {selectedWorkflowType === 'img2img' && (
              <div className="card" style={{ marginBottom: '16px' }}>
                <div className="card-header">
                  <h3><Settings size={18} /> 🖼️ Image to Image 설정</h3>
                </div>
                <div style={{ padding: '16px' }}>
                  {renderImageSelector(img2imgInput, setImg2imgInput, '입력 이미지')}
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label>프롬프트</label>
                    <textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="변경할 스타일을 설명하세요..."
                      rows={3}
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label>네거티브 프롬프트</label>
                    <textarea
                      value={negativePrompt}
                      onChange={(e) => setNegativePrompt(e.target.value)}
                      placeholder="피하고 싶은 요소..."
                      rows={2}
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                    <div className="form-group">
                      <label>강도 (Strength)</label>
                      <input
                        type="number"
                        min="0"
                        max="1"
                        step="0.1"
                        value={img2imgSettings.strength}
                        onChange={(e) => setImg2imgSettings({ ...img2imgSettings, strength: parseFloat(e.target.value) || 0.7 })}
                      />
                      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>
                        낮을수록 원본 유지
                      </div>
                    </div>
                    <div className="form-group">
                      <label>Steps</label>
                      <input
                        type="number"
                        value={img2imgSettings.steps}
                        onChange={(e) => setImg2imgSettings({ ...img2imgSettings, steps: parseInt(e.target.value) || 20 })}
                      />
                    </div>
                    <div className="form-group">
                      <label>CFG Scale</label>
                      <input
                        type="number"
                        step="0.5"
                        value={img2imgSettings.cfg_scale}
                        onChange={(e) => setImg2imgSettings({ ...img2imgSettings, cfg_scale: parseFloat(e.target.value) || 7 })}
                      />
                    </div>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={handleGenerate}
                    disabled={generating || !img2imgInput || !prompt.trim() || status?.status !== 'running'}
                    style={{ marginTop: '16px', width: '100%' }}
                  >
                    {generating ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
                    {generating ? '생성 중...' : 'Image to Image 생성'}
                  </button>
                </div>
              </div>
            )}

            {/* Inpainting Settings */}
            {selectedWorkflowType === 'inpainting' && (
              <div className="card" style={{ marginBottom: '16px' }}>
                <div className="card-header">
                  <h3><Settings size={18} /> 🎨 Inpainting 설정</h3>
                </div>
                <div style={{ padding: '16px' }}>
                  {renderImageSelector(inpaintingInput, setInpaintingInput, '입력 이미지 (수정할 기본 이미지)')}
                  {renderImageSelector(inpaintingMask, setInpaintingMask, '마스크 이미지 (흰색=변경, 검정색=유지)')}
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label>프롬프트</label>
                    <textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="그려넣을 내용을 설명하세요..."
                      rows={3}
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label>네거티브 프롬프트</label>
                    <textarea
                      value={negativePrompt}
                      onChange={(e) => setNegativePrompt(e.target.value)}
                      placeholder="피하고 싶은 요소..."
                      rows={2}
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                    <div className="form-group">
                      <label>Steps</label>
                      <input
                        type="number"
                        value={inpaintingSettings.steps}
                        onChange={(e) => setInpaintingSettings({ ...inpaintingSettings, steps: parseInt(e.target.value) || 20 })}
                      />
                    </div>
                    <div className="form-group">
                      <label>CFG Scale</label>
                      <input
                        type="number"
                        step="0.5"
                        value={inpaintingSettings.cfg_scale}
                        onChange={(e) => setInpaintingSettings({ ...inpaintingSettings, cfg_scale: parseFloat(e.target.value) || 7 })}
                      />
                    </div>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={handleGenerate}
                    disabled={generating || !inpaintingInput || !inpaintingMask || !prompt.trim() || status?.status !== 'running'}
                    style={{ marginTop: '16px', width: '100%' }}
                  >
                    {generating ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
                    {generating ? '생성 중...' : 'Inpainting 생성'}
                  </button>
                </div>
              </div>
            )}

            {/* Video Settings */}
            {selectedWorkflowType === 'video' && (
              <div className="card" style={{ marginBottom: '16px' }}>
                <div className="card-header">
                  <h3><Settings size={18} /> 🎬 Video (WAN2.2) 설정</h3>
                </div>
                <div style={{ padding: '16px' }}>
                  {renderImageSelector(startImage, setStartImage, '🎬 시작 이미지')}
                  {renderImageSelector(endImage, setEndImage, '🎬 종료 이미지')}
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label>프롬프트</label>
                    <textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="영상의 주제와 스타일을 설명하세요..."
                      rows={3}
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label>네거티브 프롬프트</label>
                    <textarea
                      value={negativePrompt}
                      onChange={(e) => setNegativePrompt(e.target.value)}
                      placeholder="피하고 싶은 요소..."
                      rows={2}
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                    <div className="form-group">
                      <label>프레임 수</label>
                      <input
                        type="number"
                        value={videoSettings.num_frames}
                        onChange={(e) => setVideoSettings({ ...videoSettings, num_frames: parseInt(e.target.value) || 24 })}
                        min="8"
                        max="120"
                        step="8"
                      />
                      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>
                        @24fps: {(videoSettings.num_frames / 24).toFixed(1)}초
                      </div>
                    </div>
                    <div className="form-group">
                      <label>Steps</label>
                      <input
                        type="number"
                        value={videoSettings.steps}
                        onChange={(e) => setVideoSettings({ ...videoSettings, steps: parseInt(e.target.value) || 25 })}
                        min="10"
                        max="50"
                      />
                    </div>
                    <div className="form-group">
                      <label>CFG Scale</label>
                      <input
                        type="number"
                        step="0.5"
                        value={videoSettings.cfg_scale}
                        onChange={(e) => setVideoSettings({ ...videoSettings, cfg_scale: parseFloat(e.target.value) || 7.5 })}
                      />
                    </div>
                    <div className="form-group">
                      <label>Motion Scale</label>
                      <input
                        type="number"
                        step="0.1"
                        value={videoSettings.motion_scale}
                        onChange={(e) => setVideoSettings({ ...videoSettings, motion_scale: parseFloat(e.target.value) || 1.0 })}
                        min="0.5"
                        max="2.0"
                      />
                    </div>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={handleGenerate}
                    disabled={generating || !startImage || !endImage || !prompt.trim() || status?.status !== 'running'}
                    style={{ marginTop: '16px', width: '100%' }}
                  >
                    {generating ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
                    {generating ? '영상 생성 중...' : 'Video 생성'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Right: Generation History */}
          <div className="card">
            <div className="card-header">
              <h3><Clock size={18} /> 생성 기록</h3>
            </div>
            <div style={{ padding: '16px', maxHeight: '600px', overflowY: 'auto' }}>
              {generations.length === 0 ? (
                <div className="empty-state">
                  <Image size={32} color="var(--text-muted)" />
                  <p>생성 기록 없음</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {generations.map((gen) => (
                    <div key={gen.id} className="result-card" style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span className={`status-badge ${gen.status}`}>
                          {gen.status === 'completed' ? <CheckCircle size={12} /> :
                           gen.status === 'running' ? <Loader2 className="spin" size={12} /> :
                           gen.status === 'error' ? <AlertCircle size={12} /> :
                           <Clock size={12} />}
                          {gen.status === 'completed' ? '완료' :
                           gen.status === 'running' ? `진행 중 ${gen.progress || 0}%` :
                           gen.status === 'error' ? '오류' :
                           gen.status === 'queued' ? '대기' : '대기'}
                        </span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          {gen.output_images && gen.output_images.length > 0 && (
                            <button
                              className="btn-icon"
                              onClick={() => setPreviewImage(gen.output_images![0])}
                              title="미리보기"
                            >
                              <Eye size={14} />
                            </button>
                          )}
                          <button
                            className="btn-icon danger"
                            onClick={() => handleDeleteGeneration(gen.id)}
                            title="삭제"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                      {gen.prompt && (
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {gen.prompt}
                        </div>
                      )}
                      {gen.output_images && gen.output_images.length > 0 && (
                        <img
                          src={gen.output_images[0]}
                          alt="Generated"
                          style={{ width: '100%', borderRadius: 4, cursor: 'pointer' }}
                          onClick={() => setPreviewImage(gen.output_images![0])}
                        />
                      )}
                      {gen.error && (
                        <div style={{ color: 'var(--accent-red)', fontSize: 11, marginTop: 8 }}>
                          {gen.error}
                        </div>
                      )}
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 8 }}>
                        {new Date(gen.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Gallery Tab */}
      {activeTab === 'gallery' && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3><Layers size={18} /> 생성된 이미지 갤러리</h3>
            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                className={`btn btn-sm ${viewMode === 'grid' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setViewMode('grid')}
              >
                <Grid size={14} />
              </button>
              <button
                className={`btn btn-sm ${viewMode === 'list' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setViewMode('list')}
              >
                <List size={14} />
              </button>
            </div>
          </div>
          <div style={{ padding: '16px' }}>
            {outputs.length === 0 ? (
              <div className="empty-state" style={{ padding: '60px 20px' }}>
                <Image size={48} color="var(--text-muted)" />
                <h3 style={{ marginTop: 16, marginBottom: 8 }}>생성된 이미지가 없습니다</h3>
                <p style={{ color: 'var(--text-secondary)' }}>이미지를 생성하면 여기에 표시됩니다</p>
              </div>
            ) : viewMode === 'grid' ? (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                gap: '16px'
              }}>
                {outputs.map((output, idx) => (
                  <div
                    key={`${output.prompt_id}-${output.filename}-${idx}`}
                    className="gallery-item"
                    style={{
                      position: 'relative',
                      borderRadius: 8,
                      overflow: 'hidden',
                      background: 'var(--bg-tertiary)',
                      cursor: 'pointer'
                    }}
                    onClick={() => setPreviewImage(getImageUrl(output.filename, output.subfolder, output.type))}
                  >
                    <img
                      src={getImageUrl(output.filename, output.subfolder, output.type)}
                      alt={output.filename}
                      style={{
                        width: '100%',
                        height: 200,
                        objectFit: 'cover'
                      }}
                      loading="lazy"
                    />
                    <div style={{
                      position: 'absolute',
                      bottom: 0,
                      left: 0,
                      right: 0,
                      padding: '8px',
                      background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
                      color: 'white',
                      fontSize: 11
                    }}>
                      {output.filename}
                    </div>
                    <div style={{
                      position: 'absolute',
                      top: 8,
                      right: 8,
                      display: 'flex',
                      gap: '4px',
                      opacity: 0,
                      transition: 'opacity 0.2s'
                    }}
                    className="gallery-actions"
                    >
                      <a
                        href={getImageUrl(output.filename, output.subfolder, output.type)}
                        download={output.filename}
                        className="btn btn-sm btn-secondary"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Download size={12} />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {outputs.map((output, idx) => (
                  <div
                    key={`${output.prompt_id}-${output.filename}-${idx}`}
                    className="list-item"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '12px',
                      background: 'var(--bg-tertiary)',
                      borderRadius: 8,
                      cursor: 'pointer'
                    }}
                    onClick={() => setPreviewImage(getImageUrl(output.filename, output.subfolder, output.type))}
                  >
                    <img
                      src={getImageUrl(output.filename, output.subfolder, output.type)}
                      alt={output.filename}
                      style={{
                        width: 60,
                        height: 60,
                        objectFit: 'cover',
                        borderRadius: 4
                      }}
                      loading="lazy"
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{output.filename}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        Prompt ID: {output.prompt_id.slice(0, 8)}...
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={(e) => { e.stopPropagation(); setPreviewImage(getImageUrl(output.filename, output.subfolder, output.type)); }}
                      >
                        <Eye size={14} />
                      </button>
                      <a
                        href={getImageUrl(output.filename, output.subfolder, output.type)}
                        download={output.filename}
                        className="btn btn-sm btn-secondary"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Download size={14} />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="card">
          <div className="card-header">
            <h3><Clock size={18} /> 실행 히스토리</h3>
          </div>
          <div style={{ padding: '16px' }}>
            {history.length === 0 ? (
              <div className="empty-state" style={{ padding: '60px 20px' }}>
                <Cpu size={48} color="var(--text-muted)" />
                <h3 style={{ marginTop: 16, marginBottom: 8 }}>실행 기록이 없습니다</h3>
                <p style={{ color: 'var(--text-secondary)' }}>ComfyUI에서 작업을 실행하면 여기에 표시됩니다</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {history.map((item) => (
                  <div
                    key={item.id}
                    className="history-item"
                    style={{
                      padding: '16px',
                      background: 'var(--bg-tertiary)',
                      borderRadius: 8
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {item.completed ? (
                          <CheckCircle size={16} style={{ color: 'var(--color-success)' }} />
                        ) : (
                          <Loader2 size={16} className="spin" style={{ color: 'var(--color-accent-blue)' }} />
                        )}
                        <span style={{ fontWeight: 600 }}>
                          {item.completed ? '완료' : '진행 중'}
                        </span>
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        ID: {item.id.slice(0, 8)}...
                      </span>
                    </div>
                    {item.images.length > 0 && (
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
                        gap: '8px'
                      }}>
                        {item.images.map((img, idx) => (
                          <img
                            key={idx}
                            src={getImageUrl(img.filename, img.subfolder, img.type)}
                            alt={img.filename}
                            style={{
                              width: '100%',
                              height: 100,
                              objectFit: 'cover',
                              borderRadius: 4,
                              cursor: 'pointer'
                            }}
                            onClick={() => setPreviewImage(getImageUrl(img.filename, img.subfolder, img.type))}
                          />
                        ))}
                      </div>
                    )}
                    {item.images.length === 0 && (
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        이미지 출력 없음
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Image Preview Modal */}
      {previewImage && (
        <div className="modal-overlay" onClick={() => setPreviewImage(null)}>
          <div className="modal modal-xl" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '90vw' }}>
            <div className="modal-header">
              <h3>이미지 미리보기</h3>
              <button className="btn-icon" onClick={() => setPreviewImage(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body" style={{ textAlign: 'center', background: '#1a1a1a', padding: '20px' }}>
              <img src={previewImage} alt="Preview" style={{ maxWidth: '100%', maxHeight: '70vh' }} />
            </div>
            <div className="modal-footer">
              <a href={previewImage} download className="btn btn-primary">
                <Download size={16} /> 다운로드
              </a>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .gallery-item:hover .gallery-actions {
          opacity: 1 !important;
        }
        .gallery-item:hover {
          transform: scale(1.02);
          transition: transform 0.2s;
        }
      `}</style>
    </section>
  );
}

export default ComfyUIPage;
