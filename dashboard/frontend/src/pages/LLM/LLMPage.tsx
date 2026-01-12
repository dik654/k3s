import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  Bot,
  RefreshCw,
  Play,
  Square,
  Settings,
  Loader2,
  Send,
  Trash2,
  Copy,
  Zap,
  Cpu,
  MemoryStick,
  Check,
  MessageSquare,
  Sparkles,
} from 'lucide-react';

const API_BASE = '/api';

interface LLMStatus {
  status: 'running' | 'stopped' | 'loading';
  model_loaded?: string;
  gpu_memory_used?: number;
  gpu_memory_total?: number;
  queue_size?: number;
}

interface LLMModel {
  id: string;
  name: string;
  size: string;
  context_length: number;
  quantization?: string;
  description?: string;
  gpu_required?: number;
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
}

interface LLMPageProps {
  showToast: (message: string, type?: string) => void;
}

// 기본 모델 목록 (API에서 불러오지 못할 경우)
const DEFAULT_MODELS: LLMModel[] = [
  // Qwen 시리즈
  { id: 'Qwen/Qwen2.5-7B-Instruct', name: 'Qwen2.5-7B-Instruct', size: '7B', context_length: 32768, description: 'Agent/Tool Use 최적화', gpu_required: 1 },
  { id: 'Qwen/Qwen2.5-14B-Instruct', name: 'Qwen2.5-14B-Instruct', size: '14B', context_length: 32768, description: '균형잡힌 성능', gpu_required: 2 },
  { id: 'Qwen/Qwen2.5-32B-Instruct', name: 'Qwen2.5-32B-Instruct', size: '32B', context_length: 32768, description: '고성능 추론', gpu_required: 4 },
  { id: 'Qwen/Qwen2.5-72B-Instruct', name: 'Qwen2.5-72B-Instruct', size: '72B', context_length: 32768, description: '최고 성능', gpu_required: 8 },
  // 한국어 특화
  { id: 'yanolja/EEVE-Korean-Instruct-10.8B-v1.0', name: 'EEVE-Korean 10.8B', size: '10.8B', context_length: 4096, description: '한국어 특화', gpu_required: 1 },
  { id: 'beomi/Llama-3-Open-Ko-8B-Instruct', name: 'Llama-3-Ko 8B', size: '8B', context_length: 8192, description: '한국어 Llama', gpu_required: 1 },
  // 코딩 특화
  { id: 'Qwen/Qwen2.5-Coder-7B-Instruct', name: 'Qwen2.5-Coder-7B', size: '7B', context_length: 32768, description: '코딩 특화', gpu_required: 1 },
  { id: 'Qwen/Qwen2.5-Coder-32B-Instruct', name: 'Qwen2.5-Coder-32B', size: '32B', context_length: 32768, description: '코딩 고성능', gpu_required: 4 },
  // 경량 모델
  { id: 'Qwen/Qwen2.5-3B-Instruct', name: 'Qwen2.5-3B-Instruct', size: '3B', context_length: 32768, description: '경량 모델', gpu_required: 1 },
  { id: 'Qwen/Qwen2.5-1.5B-Instruct', name: 'Qwen2.5-1.5B-Instruct', size: '1.5B', context_length: 32768, description: '초경량 모델', gpu_required: 1 },
  { id: 'microsoft/Phi-3-mini-4k-instruct', name: 'Phi-3-mini-4k', size: '3.8B', context_length: 4096, description: '경량 범용', gpu_required: 1 },
];

export function LLMPage({ showToast }: LLMPageProps) {
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [models, setModels] = useState<LLMModel[]>(DEFAULT_MODELS);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [generating, setGenerating] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [copied, setCopied] = useState<number | null>(null);
  const [settings, setSettings] = useState({
    temperature: 0.7,
    max_tokens: 1024,
    top_p: 0.9,
    stream: true
  });
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, modelsRes] = await Promise.all([
        axios.get(`${API_BASE}/vllm/status`).catch(() => ({ data: { status: 'stopped' } })),
        axios.get(`${API_BASE}/vllm/models`).catch(() => ({ data: { models: [] } })),
      ]);
      setStatus(statusRes.data);
      if (modelsRes.data.models && modelsRes.data.models.length > 0) {
        setModels(modelsRes.data.models);
      }
      if (statusRes.data.model_loaded) {
        setSelectedModel(statusRes.data.model_loaded);
      }
    } catch (error) {
      console.error('LLM fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || generating) return;
    if (status?.status !== 'running') {
      showToast('vLLM 서비스가 실행 중이 아닙니다. 모델을 먼저 시작해주세요.', 'error');
      return;
    }

    const userMessage: ChatMessage = { role: 'user', content: inputMessage, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setGenerating(true);
    setStreamingContent('');

    try {
      if (settings.stream) {
        // 스트리밍 요청
        const response = await fetch(`${API_BASE}/vllm/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: [...messages, userMessage].map(m => ({ role: m.role, content: m.content })),
            temperature: settings.temperature,
            max_tokens: settings.max_tokens,
            top_p: settings.top_p,
          })
        });

        if (!response.ok) {
          throw new Error('스트리밍 요청 실패');
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') continue;
                try {
                  const parsed = JSON.parse(data);
                  const content = parsed.choices?.[0]?.delta?.content || parsed.content || '';
                  if (content) {
                    fullContent += content;
                    setStreamingContent(fullContent);
                  }
                } catch {
                  // JSON 파싱 실패 - 무시
                }
              }
            }
          }
        }

        if (fullContent) {
          setMessages(prev => [...prev, { role: 'assistant', content: fullContent, timestamp: new Date() }]);
        }
        setStreamingContent('');
      } else {
        // 일반 요청
        const res = await axios.post(`${API_BASE}/vllm/chat`, {
          messages: [...messages, userMessage].map(m => ({ role: m.role, content: m.content })),
          temperature: settings.temperature,
          max_tokens: settings.max_tokens,
          top_p: settings.top_p,
        });

        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: res.data.response || res.data.choices?.[0]?.message?.content || '',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } }; message?: string };
      showToast(axiosError.response?.data?.detail || axiosError.message || '응답 생성 실패', 'error');
    } finally {
      setGenerating(false);
      setStreamingContent('');
      inputRef.current?.focus();
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setStreamingContent('');
  };

  const handleCopyMessage = (content: string, idx: number) => {
    navigator.clipboard.writeText(content);
    setCopied(idx);
    setTimeout(() => setCopied(null), 2000);
    showToast('클립보드에 복사되었습니다', 'success');
  };

  const handleStartModel = async (modelId: string) => {
    if (!modelId) return;
    setActionLoading(true);
    try {
      await axios.post(`${API_BASE}/workloads/vllm`, {
        action: 'start',
        config: { model: modelId }
      });
      showToast(`${modelId.split('/').pop()} 모델 시작 중...`, 'info');
      // 상태 업데이트를 위해 폴링
      const pollStatus = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/vllm/status`);
          if (res.data.status === 'running') {
            clearInterval(pollStatus);
            setStatus(res.data);
            setActionLoading(false);
            showToast('모델이 성공적으로 시작되었습니다', 'success');
          }
        } catch {
          // 폴링 중 에러 무시
        }
      }, 3000);

      // 최대 2분 대기
      setTimeout(() => {
        clearInterval(pollStatus);
        setActionLoading(false);
      }, 120000);
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      showToast(axiosError.response?.data?.detail || '모델 시작 실패', 'error');
      setActionLoading(false);
    }
  };

  const handleStopModel = async () => {
    setActionLoading(true);
    try {
      await axios.post(`${API_BASE}/workloads/vllm/stop`, { action: 'stop' });
      showToast('모델 중지 요청이 전송되었습니다', 'info');
      setTimeout(() => {
        fetchData();
        setActionLoading(false);
      }, 2000);
    } catch {
      showToast('모델 중지 실패', 'error');
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <section className="section">
        <div className="llm-loading">
          <Loader2 className="spin" size={48} />
          <p>LLM 서비스 정보를 불러오는 중...</p>
        </div>
      </section>
    );
  }

  const isRunning = status?.status === 'running';
  const isLoading = status?.status === 'loading' || actionLoading;

  return (
    <section className="section llm-page">
      {/* Header */}
      <div className="section-header">
        <h2 className="section-title">
          <Bot size={24} />
          vLLM 언어 모델
        </h2>
        <div className="llm-header-actions">
          <button className="btn btn-secondary btn-sm" onClick={fetchData} disabled={actionLoading}>
            <RefreshCw size={14} className={actionLoading ? 'spin' : ''} />
          </button>
          <button
            className={`btn btn-secondary btn-sm ${showSettings ? 'active' : ''}`}
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings size={14} />
            설정
          </button>
        </div>
      </div>

      {/* Status Bar */}
      <div className={`llm-status-bar ${isRunning ? 'online' : isLoading ? 'loading' : 'offline'}`}>
        <div className="llm-status-left">
          <div className="llm-status-indicator">
            <span className={`llm-dot ${isRunning ? 'online' : isLoading ? 'loading' : 'offline'}`}></span>
            <span className="llm-status-text">
              {isRunning ? '실행 중' : isLoading ? '로딩 중...' : '중지됨'}
            </span>
          </div>
          {isRunning && status?.model_loaded && (
            <>
              <div className="llm-status-divider"></div>
              <div className="llm-status-info">
                <Sparkles size={14} />
                <span>{status.model_loaded.split('/').pop()}</span>
              </div>
            </>
          )}
          {status?.gpu_memory_used !== undefined && status?.gpu_memory_total !== undefined && (
            <>
              <div className="llm-status-divider"></div>
              <div className="llm-status-info">
                <Zap size={14} />
                <span>GPU: {((status.gpu_memory_used || 0) / 1024).toFixed(1)}G / {((status.gpu_memory_total || 0) / 1024).toFixed(0)}G</span>
              </div>
            </>
          )}
        </div>
        <div className="llm-status-right">
          {isRunning ? (
            <button className="btn btn-danger btn-sm" onClick={handleStopModel} disabled={actionLoading}>
              {actionLoading ? <Loader2 size={14} className="spin" /> : <Square size={14} />}
              중지
            </button>
          ) : (
            <div className="llm-model-select-wrapper">
              <select
                className="llm-model-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={actionLoading}
              >
                <option value="">모델 선택...</option>
                {models.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.size}) {m.gpu_required ? `- ${m.gpu_required} GPU` : ''}
                  </option>
                ))}
              </select>
              <button
                className="btn btn-success btn-sm"
                onClick={() => handleStartModel(selectedModel)}
                disabled={!selectedModel || actionLoading}
              >
                {actionLoading ? <Loader2 size={14} className="spin" /> : <Play size={14} />}
                실행
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="llm-settings-panel">
          <div className="llm-settings-grid">
            <div className="llm-setting-item">
              <label>Temperature</label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={settings.temperature}
                onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
              />
              <span className="llm-setting-value">{settings.temperature}</span>
            </div>
            <div className="llm-setting-item">
              <label>Max Tokens</label>
              <input
                type="number"
                min="1"
                max="4096"
                value={settings.max_tokens}
                onChange={(e) => setSettings({ ...settings, max_tokens: parseInt(e.target.value) || 512 })}
              />
            </div>
            <div className="llm-setting-item">
              <label>Top P</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.top_p}
                onChange={(e) => setSettings({ ...settings, top_p: parseFloat(e.target.value) })}
              />
              <span className="llm-setting-value">{settings.top_p}</span>
            </div>
            <div className="llm-setting-item">
              <label>스트리밍</label>
              <label className="llm-toggle">
                <input
                  type="checkbox"
                  checked={settings.stream}
                  onChange={(e) => setSettings({ ...settings, stream: e.target.checked })}
                />
                <span className="llm-toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Chat Interface */}
      <div className="llm-chat-container">
        <div className="llm-chat-header">
          <div className="llm-chat-title">
            <MessageSquare size={18} />
            <span>채팅</span>
            {messages.length > 0 && (
              <span className="llm-chat-count">{messages.length}개 메시지</span>
            )}
          </div>
          <button className="btn btn-secondary btn-sm" onClick={handleClearChat} disabled={messages.length === 0}>
            <Trash2 size={14} />
            초기화
          </button>
        </div>

        <div className="llm-chat-messages">
          {messages.length === 0 && !streamingContent ? (
            <div className="llm-chat-empty">
              <Bot size={64} />
              <h3>대화를 시작하세요</h3>
              <p>
                {isRunning
                  ? '아래에 메시지를 입력하여 AI와 대화해보세요.'
                  : '먼저 위에서 모델을 선택하고 실행해주세요.'}
              </p>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <div key={idx} className={`llm-message ${msg.role}`}>
                  <div className="llm-message-avatar">
                    {msg.role === 'user' ? '👤' : '🤖'}
                  </div>
                  <div className="llm-message-content">
                    <div className="llm-message-header">
                      <span className="llm-message-role">
                        {msg.role === 'user' ? '사용자' : 'AI 어시스턴트'}
                      </span>
                      {msg.timestamp && (
                        <span className="llm-message-time">
                          {msg.timestamp.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                    <div className="llm-message-text">{msg.content}</div>
                    <div className="llm-message-actions">
                      <button
                        className="llm-action-btn"
                        onClick={() => handleCopyMessage(msg.content, idx)}
                        title="복사"
                      >
                        {copied === idx ? <Check size={12} /> : <Copy size={12} />}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {streamingContent && (
                <div className="llm-message assistant">
                  <div className="llm-message-avatar">🤖</div>
                  <div className="llm-message-content">
                    <div className="llm-message-header">
                      <span className="llm-message-role">AI 어시스턴트</span>
                      <span className="llm-typing-indicator">
                        <Loader2 size={12} className="spin" /> 생성 중...
                      </span>
                    </div>
                    <div className="llm-message-text">{streamingContent}</div>
                  </div>
                </div>
              )}
              {generating && !streamingContent && (
                <div className="llm-message assistant">
                  <div className="llm-message-avatar">🤖</div>
                  <div className="llm-message-content">
                    <div className="llm-typing">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        <div className="llm-chat-input">
          <input
            ref={inputRef}
            type="text"
            placeholder={isRunning ? "메시지를 입력하세요..." : "모델을 먼저 실행해주세요"}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
            disabled={generating || !isRunning}
          />
          <button
            className="llm-send-btn"
            onClick={handleSendMessage}
            disabled={generating || !inputMessage.trim() || !isRunning}
          >
            {generating ? <Loader2 size={20} className="spin" /> : <Send size={20} />}
          </button>
        </div>
      </div>

      {/* Available Models */}
      <div className="llm-models-section">
        <h3 className="llm-models-title">
          <Cpu size={18} />
          사용 가능한 모델
        </h3>
        <div className="llm-models-grid">
          {models.map((model) => (
            <div
              key={model.id}
              className={`llm-model-card ${selectedModel === model.id ? 'selected' : ''} ${status?.model_loaded === model.id ? 'active' : ''}`}
              onClick={() => {
                if (!isRunning && !actionLoading) {
                  setSelectedModel(model.id);
                }
              }}
            >
              <div className="llm-model-header">
                <span className="llm-model-name">{model.name}</span>
                {status?.model_loaded === model.id && (
                  <span className="llm-model-badge active">실행 중</span>
                )}
                {selectedModel === model.id && status?.model_loaded !== model.id && (
                  <span className="llm-model-badge selected">선택됨</span>
                )}
              </div>
              {model.description && (
                <p className="llm-model-desc">{model.description}</p>
              )}
              <div className="llm-model-specs">
                <div className="llm-spec">
                  <MemoryStick size={12} />
                  <span>{model.size}</span>
                </div>
                <div className="llm-spec">
                  <MessageSquare size={12} />
                  <span>{model.context_length?.toLocaleString()} ctx</span>
                </div>
                {model.gpu_required && (
                  <div className="llm-spec">
                    <Zap size={12} />
                    <span>{model.gpu_required} GPU</span>
                  </div>
                )}
                {model.quantization && (
                  <div className="llm-spec">
                    <Cpu size={12} />
                    <span>{model.quantization}</span>
                  </div>
                )}
              </div>
              {!isRunning && !actionLoading && (
                <button
                  className="llm-model-start-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedModel(model.id);
                    handleStartModel(model.id);
                  }}
                >
                  <Play size={14} />
                  실행
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default LLMPage;
