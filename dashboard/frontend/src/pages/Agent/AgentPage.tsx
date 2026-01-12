import { useState, useEffect } from 'react';
import { Workflow, List, Loader2, CheckCircle2, XCircle, Code, Hammer, Rocket, FileCode, FileText, Box, Copy } from 'lucide-react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { WorkflowList } from '@/pages/WorkflowList';
import { WorkflowEditor } from '@/pages/WorkflowEditor';
import { useWorkflowStore } from '@/stores/workflowStore';

interface GeneratedFiles {
  'agent.py': string;
  'Dockerfile': string;
  'requirements.txt': string;
  'k8s-deployment.yaml': string;
}

export function AgentPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { workflows, loadWorkflows } = useWorkflowStore();

  // 워크플로우 목록 로드
  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  // LangGraph 상태
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFiles | null>(null);
  const [activeTab, setActiveTab] = useState<keyof GeneratedFiles>('agent.py');
  const [buildId, setBuildId] = useState<string | null>(null);
  const [buildStatus, setBuildStatus] = useState<string | null>(null);
  const [buildLogs, setBuildLogs] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isBuilding, setIsBuilding] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 코드 생성
  const handleGenerateCode = async () => {
    if (!selectedWorkflowId) {
      setError('워크플로우를 선택해주세요');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setGeneratedFiles(null);

    try {
      // 워크플로우 데이터 가져오기
      const workflowRes = await axios.get(`/api/workflows/${selectedWorkflowId}`);
      const workflowData = workflowRes.data.workflow;

      // 코드 생성 API 호출
      const response = await axios.post('/api/langgraph/generate-code', workflowData);

      if (response.data.success && response.data.files) {
        setGeneratedFiles(response.data.files);
        setActiveTab('agent.py');
        setSuccess('코드 생성 완료! 4개의 파일이 생성되었습니다.');
      } else {
        setError('코드 생성 응답 형식 오류');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '코드 생성 실패');
    } finally {
      setIsGenerating(false);
    }
  };

  // 빌드
  const handleBuild = async () => {
    if (!selectedWorkflowId) {
      setError('워크플로우를 선택해주세요');
      return;
    }

    setIsBuilding(true);
    setError(null);
    setBuildStatus(null);
    setBuildLogs([]);

    try {
      const workflowRes = await axios.get(`/api/workflows/${selectedWorkflowId}`);
      const workflowData = workflowRes.data.workflow;

      const response = await axios.post('/api/langgraph/build', {
        workflow: workflowData,
        image_name: `langgraph-agent-${selectedWorkflowId.slice(0, 8)}`,
        image_tag: 'latest'
      });

      setBuildId(response.data.build_id);
      setBuildStatus('building');

      // 빌드 상태 폴링
      pollBuildStatus(response.data.build_id);
    } catch (err: any) {
      setError(err.response?.data?.detail || '빌드 시작 실패');
      setIsBuilding(false);
    }
  };

  // 빌드 상태 폴링
  const pollBuildStatus = async (id: string) => {
    const maxAttempts = 60;
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await axios.get(`/api/langgraph/build/${id}/status`);
        setBuildStatus(response.data.status);

        if (response.data.logs) {
          setBuildLogs(response.data.logs);
        }

        if (response.data.status === 'completed' || response.data.status === 'failed') {
          setIsBuilding(false);
          if (response.data.status === 'completed') {
            setSuccess('빌드 완료! 이제 배포할 수 있습니다.');
          } else {
            setError('빌드 실패: ' + (response.data.error || ''));
          }
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          setIsBuilding(false);
          setError('빌드 타임아웃');
        }
      } catch (err) {
        setIsBuilding(false);
        setError('빌드 상태 확인 실패');
      }
    };

    poll();
  };

  // 배포
  const handleDeploy = async () => {
    if (!buildId) {
      setError('먼저 빌드를 완료해주세요');
      return;
    }

    setIsDeploying(true);
    setError(null);

    try {
      const response = await axios.post(`/api/langgraph/deploy/${buildId}`);
      setSuccess('배포 완료! ' + (response.data.message || 'K8s 클러스터에 에이전트가 배포되었습니다.'));
    } catch (err: any) {
      setError(err.response?.data?.detail || '배포 실패');
    } finally {
      setIsDeploying(false);
    }
  };

  // URL 경로에서 현재 모드 판단
  const isEditorMode = location.pathname.includes('/workflow/');

  const copyToClipboard = (text: string, filename: string) => {
    navigator.clipboard.writeText(text);
    setSuccess(`${filename}이(가) 클립보드에 복사되었습니다`);
    setTimeout(() => setSuccess(null), 2000);
  };

  const getFileIcon = (filename: string) => {
    if (filename.endsWith('.py')) return <FileCode size={14} />;
    if (filename.endsWith('.yaml')) return <Box size={14} />;
    return <FileText size={14} />;
  };

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">
          <Workflow size={20} style={{ marginRight: 8 }} />
          Agent Workflow
        </h2>
        {!isEditorMode && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn btn-primary"
              onClick={() => navigate('/agent')}
            >
              <List size={14} /> 워크플로우 목록
            </button>
          </div>
        )}
      </div>

      {/* Content - 라우팅 기반 */}
      <Routes>
        <Route
          index
          element={
            <div className="card" style={{ minHeight: 500 }}>
              <div style={{ padding: 24 }}>
                <WorkflowList />
              </div>
            </div>
          }
        />
        <Route
          path="workflow/:id"
          element={
            <div className="card" style={{ minHeight: 500, padding: 0 }}>
              <div style={{ height: 'calc(100vh - 250px)', minHeight: 500 }}>
                <WorkflowEditor />
              </div>
            </div>
          }
        />
      </Routes>

      {/* LangGraph Info - 목록 페이지에서만 표시 */}
      {!isEditorMode && (
        <div className="card" style={{ marginTop: 16, padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <Workflow size={18} color="var(--accent-purple)" />
            <h3 style={{ fontWeight: 600 }}>LangGraph 연동</h3>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
            생성한 워크플로우를 LangGraph 코드로 변환하고 K8s에 배포할 수 있습니다.
          </p>

          {/* 워크플로우 선택 */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              워크플로우 선택
            </label>
            <select
              value={selectedWorkflowId || ''}
              onChange={(e) => {
                setSelectedWorkflowId(e.target.value || null);
                setError(null);
                setSuccess(null);
                setGeneratedFiles(null);
                setBuildId(null);
                setBuildStatus(null);
                setBuildLogs([]);
              }}
              style={{
                width: '100%',
                maxWidth: 300,
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid var(--border-color)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                fontSize: 13
              }}
            >
              <option value="">워크플로우를 선택하세요</option>
              {workflows.map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
          </div>

          {/* 상태 메시지 */}
          {error && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 12px',
              marginBottom: 12,
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 6,
              color: '#ef4444',
              fontSize: 13
            }}>
              <XCircle size={16} />
              {error}
            </div>
          )}
          {success && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 12px',
              marginBottom: 12,
              background: 'rgba(34, 197, 94, 0.1)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
              borderRadius: 6,
              color: '#22c55e',
              fontSize: 13
            }}>
              <CheckCircle2 size={16} />
              {success}
            </div>
          )}

          {/* 버튼들 */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              className="btn btn-secondary"
              onClick={handleGenerateCode}
              disabled={isGenerating || !selectedWorkflowId}
            >
              {isGenerating ? <Loader2 size={14} className="spin" /> : <Code size={14} />}
              1. 코드 생성
            </button>
            <button
              className="btn btn-secondary"
              onClick={handleBuild}
              disabled={isBuilding || !selectedWorkflowId}
            >
              {isBuilding ? <Loader2 size={14} className="spin" /> : <Hammer size={14} />}
              2. 빌드 {buildStatus && buildStatus !== 'completed' && buildStatus !== 'failed' && `(${buildStatus})`}
            </button>
            <button
              className="btn btn-success"
              onClick={handleDeploy}
              disabled={isDeploying || !buildId || buildStatus !== 'completed'}
            >
              {isDeploying ? <Loader2 size={14} className="spin" /> : <Rocket size={14} />}
              3. 배포
            </button>
          </div>

          {/* 빌드 로그 */}
          {buildLogs.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 8 }}>
                빌드 로그
              </div>
              <div style={{
                padding: 12,
                background: '#1e1e1e',
                borderRadius: 6,
                border: '1px solid var(--border-color)',
                fontSize: 11,
                fontFamily: 'monospace',
                maxHeight: 150,
                overflow: 'auto'
              }}>
                {buildLogs.map((log, idx) => (
                  <div key={idx} style={{ color: '#d4d4d4', marginBottom: 4 }}>
                    <span style={{ color: '#569cd6' }}>[{idx + 1}]</span> {log}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 생성된 코드 미리보기 - 탭 형식 */}
          {generatedFiles && (
            <div style={{ marginTop: 16 }}>
              {/* 탭 헤더 */}
              <div style={{
                display: 'flex',
                gap: 2,
                borderBottom: '1px solid var(--border-color)',
                marginBottom: 0
              }}>
                {(Object.keys(generatedFiles) as Array<keyof GeneratedFiles>).map((filename) => (
                  <button
                    key={filename}
                    onClick={() => setActiveTab(filename)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '8px 16px',
                      border: 'none',
                      background: activeTab === filename ? 'var(--bg-secondary)' : 'transparent',
                      color: activeTab === filename ? 'var(--text-primary)' : 'var(--text-muted)',
                      borderBottom: activeTab === filename ? '2px solid var(--accent-purple)' : '2px solid transparent',
                      cursor: 'pointer',
                      fontSize: 12,
                      fontWeight: activeTab === filename ? 600 : 400,
                      transition: 'all 0.2s'
                    }}
                  >
                    {getFileIcon(filename)}
                    {filename}
                  </button>
                ))}
              </div>

              {/* 코드 내용 */}
              <div style={{
                position: 'relative',
                background: 'var(--bg-secondary)',
                borderRadius: '0 0 6px 6px',
                border: '1px solid var(--border-color)',
                borderTop: 'none'
              }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => copyToClipboard(generatedFiles[activeTab], activeTab)}
                  style={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    zIndex: 10
                  }}
                >
                  <Copy size={12} /> 복사
                </button>
                <pre style={{
                  padding: 16,
                  paddingTop: 40,
                  margin: 0,
                  fontSize: 11,
                  overflow: 'auto',
                  maxHeight: 400,
                  whiteSpace: 'pre',
                  fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                  lineHeight: 1.5,
                  color: '#d4d4d4'
                }}>
                  {generatedFiles[activeTab]}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default AgentPage;
