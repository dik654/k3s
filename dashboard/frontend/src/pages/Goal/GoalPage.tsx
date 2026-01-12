import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Target,
  Server,
  Cloud,
  Cpu,
  HardDrive,
  Database,
  Users,
  Calendar,
  CheckCircle,
  Circle,
  ArrowRight,
  Code,
  Layers,
  Shield,
  Zap,
  Monitor,
  GitBranch
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

interface ClusterSummary {
  nodes?: {
    total: number;
  };
}

interface GpuStatus {
  total: number;
}

interface GpuInfo {
  name: string;
  memory_total: number;
  memory_used: number;
}

interface GpuDetailed {
  gpus?: GpuInfo[];
}

interface ServiceCard {
  id: string;
  icon: string;
  title: string;
  subtitle: string;
  features: string[];
  target: string;
  className: string;
}

interface TeamRole {
  icon: string;
  title: string;
  tasks: string[];
  techStack: string[];
}

interface RoadmapPhase {
  phase: string;
  title: string;
  status: 'current' | 'next' | 'future';
  items: { label: string; done: boolean }[];
}

export function GoalPage() {
  const [clusterSummary, setClusterSummary] = useState<ClusterSummary | null>(null);
  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null);
  const [gpuDetailed, setGpuDetailed] = useState<GpuDetailed | null>(null);

  useEffect(() => {
    fetchClusterData();
  }, []);

  const fetchClusterData = async () => {
    try {
      const [summaryRes, gpuRes, gpuDetailRes] = await Promise.all([
        axios.get(`${API_BASE}/cluster/summary`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/gpu/status`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/gpu/detailed`).catch(() => ({ data: null }))
      ]);

      setClusterSummary(summaryRes.data);
      setGpuStatus(gpuRes.data);
      setGpuDetailed(gpuDetailRes.data);
    } catch (error) {
      console.error('Failed to fetch cluster data:', error);
    }
  };

  const serviceCards: ServiceCard[] = [
    {
      id: 'cluster',
      icon: '☸️',
      title: 'Cluster Resource',
      subtitle: 'K8s 네임스페이스 할당',
      features: [
        'CPU/Memory 동적 스케일링',
        'GPU 할당 (vGPU 지원)',
        'Storage 자동 프로비저닝',
        '네임스페이스 격리'
      ],
      target: 'ML 개발팀, 데이터 사이언티스트',
      className: 'cluster'
    },
    {
      id: 'baremetal',
      icon: '🖥️',
      title: 'Bare Metal',
      subtitle: '전용 GPU 서버 대여',
      features: [
        '전용 GPU 할당 (A100/H100)',
        'Root 권한 제공',
        '커스텀 환경 구성',
        '고성능 NVMe SSD'
      ],
      target: '대규모 모델 학습, 연구팀',
      className: 'baremetal'
    },
    {
      id: 'api',
      icon: '🔌',
      title: 'API Service',
      subtitle: 'AI 모델 API 제공',
      features: [
        'LLM Inference API',
        'Embedding API',
        'Image Generation API',
        '사용량 기반 과금'
      ],
      target: '앱 개발자, 스타트업',
      className: 'api'
    }
  ];

  const teamRoles: TeamRole[] = [
    {
      icon: '🎨',
      title: 'Frontend',
      tasks: ['User Portal 개발', 'Dashboard UI/UX', 'API Documentation'],
      techStack: ['React', 'Next.js', 'TailwindCSS']
    },
    {
      icon: '⚙️',
      title: 'Backend',
      tasks: ['Resource Manager API', 'Billing Logic', 'Auth Integration'],
      techStack: ['FastAPI', 'Go', 'PostgreSQL']
    },
    {
      icon: '☸️',
      title: 'Infrastructure',
      tasks: ['K8s Cluster 운영', 'GPU Scheduling', 'Storage 관리'],
      techStack: ['K3s', 'Longhorn', 'Traefik']
    },
    {
      icon: '🤖',
      title: 'ML/AI',
      tasks: ['모델 최적화', 'vLLM 운영', 'Fine-tuning Pipeline'],
      techStack: ['vLLM', 'PyTorch', 'Qdrant']
    }
  ];

  const roadmapPhases: RoadmapPhase[] = [
    {
      phase: 'Phase 1',
      title: 'Foundation',
      status: 'current',
      items: [
        { label: 'K3s 클러스터 구축', done: true },
        { label: 'Longhorn Storage 연동', done: true },
        { label: 'GPU 노드 설정', done: true },
        { label: '기본 모니터링 대시보드', done: true },
        { label: 'vLLM 배포', done: true }
      ]
    },
    {
      phase: 'Phase 2',
      title: 'Platform Services',
      status: 'next',
      items: [
        { label: 'Resource Manager API 개발', done: false },
        { label: '사용자 인증 시스템 (Keycloak)', done: false },
        { label: '네임스페이스 자동 프로비저닝', done: false },
        { label: '기본 과금 시스템', done: false },
        { label: 'User Portal MVP', done: false }
      ]
    },
    {
      phase: 'Phase 3',
      title: 'Advanced Features',
      status: 'future',
      items: [
        { label: 'Bare Metal Provisioning', done: false },
        { label: 'Multi-tenant 완전 격리', done: false },
        { label: '자동 스케일링', done: false },
        { label: 'SLA 모니터링', done: false },
        { label: '결제 시스템 연동', done: false }
      ]
    },
    {
      phase: 'Phase 4',
      title: 'Scale & Optimize',
      status: 'future',
      items: [
        { label: 'Multi-Cluster 연합', done: false },
        { label: '글로벌 엣지 노드', done: false },
        { label: 'AI 기반 리소스 최적화', done: false },
        { label: 'Marketplace 오픈', done: false },
        { label: 'Enterprise 기능', done: false }
      ]
    }
  ];

  const architectureLayers = [
    {
      label: 'Frontend (사용자 인터페이스)',
      className: 'frontend-layer',
      components: [
        { icon: '🌐', name: 'Web Dashboard', tech: 'React + Vite' },
        { icon: '📱', name: 'User Portal', tech: 'Next.js' },
        { icon: '📊', name: 'Admin Console', tech: 'Grafana' }
      ]
    },
    {
      label: 'API Gateway (인증/라우팅)',
      className: 'gateway-layer',
      components: [
        { icon: '🚪', name: 'Traefik Ingress', tech: 'L7 Load Balancer', highlight: true },
        { icon: '🔐', name: 'Auth Service', tech: 'Keycloak / OAuth2' },
        { icon: '📈', name: 'Rate Limiter', tech: 'Redis' }
      ]
    },
    {
      label: 'Backend Services (비즈니스 로직)',
      className: 'backend-layer',
      components: [
        { icon: '⚙️', name: 'Resource Manager', tech: 'Python FastAPI', desc: '리소스 할당/관리' },
        { icon: '📋', name: 'Billing Service', tech: 'Go + PostgreSQL', desc: '사용량 계산/과금' },
        { icon: '🔔', name: 'Notification', tech: 'Node.js', desc: '알림/메시징' },
        { icon: '📝', name: 'Audit Logger', tech: 'ELK Stack', desc: '감사 로그' }
      ]
    },
    {
      label: 'Infrastructure Control (인프라 제어)',
      className: 'infra-layer',
      components: [
        { icon: '☸️', name: 'K8s Operator', tech: 'Custom Controller', desc: '네임스페이스/Pod 관리' },
        { icon: '🖥️', name: 'Bare Metal Provisioner', tech: 'Ansible + IPMI', desc: '서버 프로비저닝' },
        { icon: '🎮', name: 'GPU Scheduler', tech: 'NVIDIA MPS/MIG', desc: 'GPU 할당 최적화' }
      ]
    },
    {
      label: 'Physical Infrastructure (물리 인프라)',
      className: 'physical-layer',
      components: [
        { icon: '🖧', name: 'K3s Cluster', tech: '3 Masters + N Workers' },
        { icon: '💾', name: 'Longhorn Storage', tech: 'Distributed Block' },
        { icon: '🎮', name: 'GPU Nodes', tech: 'NVIDIA A100/RTX' },
        { icon: '🗄️', name: 'Object Storage', tech: 'MinIO S3' }
      ]
    }
  ];

  const dataFlowScenarios = [
    {
      title: '📦 Scenario 1: 클러스터 리소스 할당',
      steps: [
        { num: 1, title: '사용자 요청', desc: 'Web UI에서 리소스 요청 (CPU 4, Memory 8Gi, GPU 1)' },
        { num: 2, title: '인증 & 권한 확인', desc: 'Keycloak JWT 검증, RBAC 권한 체크' },
        { num: 3, title: '리소스 가용성 확인', desc: 'K8s API로 노드 리소스 조회' },
        { num: 4, title: '네임스페이스 생성', desc: 'ResourceQuota, LimitRange 적용' },
        { num: 5, title: '접근 정보 제공', desc: 'kubeconfig, Dashboard URL 발급' }
      ]
    },
    {
      title: '🔌 Scenario 2: API 서비스 호출',
      steps: [
        { num: 1, title: 'API 요청', desc: 'POST /v1/chat/completions (API Key 포함)' },
        { num: 2, title: 'Rate Limiting', desc: 'Redis에서 사용량 체크 (100 req/min)' },
        { num: 3, title: '모델 라우팅', desc: '요청 모델에 따라 vLLM 인스턴스로 전달' },
        { num: 4, title: 'Inference 실행', desc: 'GPU에서 모델 추론 수행' },
        { num: 5, title: '사용량 기록', desc: 'Token 수 계산, Billing DB 기록' }
      ]
    }
  ];

  const apiExamples = [
    {
      title: '리소스 할당 요청',
      code: `POST /api/v1/resources/allocate
{
  "type": "kubernetes",
  "resources": {
    "cpu": "4",
    "memory": "8Gi",
    "gpu": 1,
    "storage": "50Gi"
  },
  "duration": "30d",
  "project_name": "my-ml-project"
}

Response:
{
  "namespace": "user-12345-my-ml-project",
  "kubeconfig": "base64...",
  "dashboard_url": "https://dashboard.example.com/ns/...",
  "expires_at": "2026-02-08T00:00:00Z"
}`
    },
    {
      title: 'LLM API 호출',
      code: `POST /api/v1/chat/completions
Authorization: Bearer sk-xxx...
{
  "model": "llama-3.1-8b",
  "messages": [
    {"role": "user", "content": "안녕하세요"}
  ],
  "max_tokens": 100
}

Response:
{
  "id": "chatcmpl-xxx",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "안녕하세요! 무엇을 도와드릴까요?"
    }
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}`
    }
  ];

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Service Architecture Goal</h2>
        <span className="section-subtitle">클러스터 리소스 할당 및 API 서비스 제공 플랫폼</span>
      </div>

      {/* Vision Statement */}
      <div className="goal-vision">
        <div className="vision-icon">🎯</div>
        <h3>최종 목표</h3>
        <p>
          <strong>AI 인프라 통합 플랫폼</strong>으로서 사용자에게 Kubernetes 클러스터 리소스를
          동적으로 할당하거나, 베어메탈 GPU 서버를 직접 대여하고,
          완성된 AI 모델을 API 형태로 제공하는 원스톱 서비스
        </p>
      </div>

      {/* Service Modes */}
      <div className="goal-services">
        <h3>🛠️ 제공 서비스 유형</h3>
        <div className="service-cards">
          {serviceCards.map((service) => (
            <div key={service.id} className={`service-card ${service.className}`}>
              <div className="service-icon">{service.icon}</div>
              <h4>{service.title}</h4>
              <p className="service-desc">{service.subtitle}</p>
              <ul className="service-features">
                {service.features.map((feature, idx) => (
                  <li key={idx}>{feature}</li>
                ))}
              </ul>
              <div className="service-use-case">
                <span className="label">적합 대상</span>
                <span>{service.target}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Architecture Diagram */}
      <div className="goal-architecture">
        <h3>🏗️ 전체 시스템 아키텍처</h3>

        <div className="architecture-diagram-full">
          {architectureLayers.map((layer, idx) => (
            <div key={idx}>
              <div className={`arch-layer ${layer.className}`}>
                <div className="layer-label">{layer.label}</div>
                <div className="layer-content">
                  {layer.components.map((comp, compIdx) => (
                    <div
                      key={compIdx}
                      className={`arch-component ${comp.highlight ? 'highlight' : ''}`}
                    >
                      <div className="comp-icon">{comp.icon}</div>
                      <div className="comp-name">{comp.name}</div>
                      <div className="comp-tech">{comp.tech}</div>
                      {comp.desc && <div className="comp-desc">{comp.desc}</div>}
                    </div>
                  ))}
                </div>
              </div>
              {idx < architectureLayers.length - 1 && (
                <div className="arch-arrow-down">▼</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Data Flow */}
      <div className="goal-dataflow">
        <h3>🔄 데이터 흐름</h3>
        <div className="dataflow-scenarios">
          {dataFlowScenarios.map((scenario, idx) => (
            <div key={idx} className="dataflow-scenario">
              <h4>{scenario.title}</h4>
              <div className="flow-steps">
                {scenario.steps.map((step, stepIdx) => (
                  <div key={stepIdx} className="flow-step-wrapper">
                    <div className="flow-step">
                      <div className="step-num">{step.num}</div>
                      <div className="step-content">
                        <strong>{step.title}</strong>
                        <span>{step.desc}</span>
                      </div>
                    </div>
                    {stepIdx < scenario.steps.length - 1 && (
                      <div className="flow-arrow">→</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Team Roles */}
      <div className="goal-team">
        <h3>👥 팀 역할 및 담당 영역</h3>
        <div className="team-grid">
          {teamRoles.map((role, idx) => (
            <div key={idx} className="team-role">
              <div className="role-icon">{role.icon}</div>
              <h4>{role.title}</h4>
              <ul>
                {role.tasks.map((task, taskIdx) => (
                  <li key={taskIdx}>{task}</li>
                ))}
              </ul>
              <div className="tech-stack">
                {role.techStack.map((tech, techIdx) => (
                  <span key={techIdx}>{tech}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Implementation Roadmap */}
      <div className="goal-roadmap">
        <h3>📅 구현 로드맵</h3>
        <div className="roadmap-timeline">
          {roadmapPhases.map((phase, idx) => (
            <div key={idx} className={`roadmap-phase ${phase.status}`}>
              <div className="phase-header">
                <span className="phase-badge">{phase.phase}</span>
                <span className="phase-status">
                  {phase.status === 'current' ? '현재' : phase.status === 'next' ? '다음' : '계획'}
                </span>
              </div>
              <h4>{phase.title}</h4>
              <ul>
                {phase.items.map((item, itemIdx) => (
                  <li key={itemIdx} className={item.done ? 'done' : ''}>
                    {item.done ? <CheckCircle size={14} /> : <Circle size={14} />}
                    {item.label}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Current Status */}
      <div className="goal-current-status">
        <h3>📊 현재 인프라 현황</h3>
        <div className="status-grid">
          <div className="status-card">
            <div className="status-icon running">✓</div>
            <h4>K3s Cluster</h4>
            <div className="status-detail">
              <div className="detail-row">
                <span>Master Nodes</span>
                <span className="value">{clusterSummary?.nodes?.total || 1}</span>
              </div>
              <div className="detail-row">
                <span>Version</span>
                <span className="value">v1.31.x</span>
              </div>
              <div className="detail-row">
                <span>Status</span>
                <span className="value running">운영중</span>
              </div>
            </div>
          </div>

          <div className="status-card">
            <div className="status-icon running">✓</div>
            <h4>GPU Resources</h4>
            <div className="status-detail">
              <div className="detail-row">
                <span>총 GPU</span>
                <span className="value">{gpuDetailed?.gpus?.length || gpuStatus?.total || 0}개</span>
              </div>
              <div className="detail-row">
                <span>모델</span>
                <span className="value">{gpuDetailed?.gpus?.[0]?.name || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span>할당</span>
                <span className="value">vLLM, ComfyUI</span>
              </div>
            </div>
          </div>

          <div className="status-card">
            <div className="status-icon running">✓</div>
            <h4>Storage</h4>
            <div className="status-detail">
              <div className="detail-row">
                <span>Type</span>
                <span className="value">Longhorn</span>
              </div>
              <div className="detail-row">
                <span>Replicas</span>
                <span className="value">2</span>
              </div>
              <div className="detail-row">
                <span>Object Storage</span>
                <span className="value">MinIO</span>
              </div>
            </div>
          </div>

          <div className="status-card">
            <div className="status-icon running">✓</div>
            <h4>AI Services</h4>
            <div className="status-detail">
              <div className="detail-row">
                <span>LLM</span>
                <span className="value running">vLLM 운영중</span>
              </div>
              <div className="detail-row">
                <span>Vector DB</span>
                <span className="value running">Qdrant 운영중</span>
              </div>
              <div className="detail-row">
                <span>Image Gen</span>
                <span className="value running">ComfyUI 운영중</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* API Examples */}
      <div className="goal-api-examples">
        <h3>🔌 예상 API 인터페이스</h3>
        <div className="api-examples-grid">
          {apiExamples.map((example, idx) => (
            <div key={idx} className="api-example">
              <h4>{example.title}</h4>
              <pre>{example.code}</pre>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default GoalPage;
