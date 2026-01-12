import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  MoreVertical,
  Play,
  Trash2,
  Copy,
  Clock,
  Plus,
  Loader2,
  FileCode2,
} from 'lucide-react';
import { useWorkflowStore } from '@/stores/workflowStore';

export function WorkflowList() {
  const navigate = useNavigate();
  const { workflows, isLoadingList, loadWorkflows, createWorkflow, deleteWorkflow } = useWorkflowStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowDesc, setNewWorkflowDesc] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  const filteredWorkflows = workflows.filter((w) =>
    w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    w.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateWorkflow = async () => {
    if (!newWorkflowName.trim()) return;

    setIsCreating(true);
    try {
      const id = await createWorkflow(newWorkflowName.trim(), newWorkflowDesc.trim());
      setShowCreateModal(false);
      setNewWorkflowName('');
      setNewWorkflowDesc('');
      // 생성 후 에디터로 이동
      navigate(`/agent/workflow/${id}`);
    } catch (error) {
      console.error('Failed to create workflow:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteWorkflow = async (id: string, name: string) => {
    if (confirm(`"${name}" 워크플로우를 삭제하시겠습니까?`)) {
      try {
        await deleteWorkflow(id);
      } catch (error) {
        console.error('Failed to delete workflow:', error);
      }
    }
  };

  const handleOpenWorkflow = (id: string) => {
    navigate(`/agent/workflow/${id}`);
  };

  return (
    <div>
      {/* Header with Search and Create Button */}
      <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: 300 }}>
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: 12,
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)'
            }}
          />
          <input
            type="text"
            placeholder="워크플로우 검색..."
            className="form-input"
            style={{ paddingLeft: 36, width: '100%' }}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateModal(true)}
        >
          <Plus size={16} />
          새 워크플로우
        </button>
      </div>

      {/* Loading State */}
      {isLoadingList && (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
          <Loader2 size={24} className="spin" style={{ marginBottom: 8 }} />
          <p>워크플로우 로딩 중...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoadingList && filteredWorkflows.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
          <FileCode2 size={48} style={{ marginBottom: 12, opacity: 0.5 }} />
          <p style={{ marginBottom: 16 }}>
            {searchQuery ? '검색 결과가 없습니다.' : '아직 워크플로우가 없습니다.'}
          </p>
          {!searchQuery && (
            <button
              className="btn btn-primary"
              onClick={() => setShowCreateModal(true)}
            >
              <Plus size={16} />
              첫 워크플로우 만들기
            </button>
          )}
        </div>
      )}

      {/* Workflow Grid */}
      {!isLoadingList && filteredWorkflows.length > 0 && (
        <div className="grid-3">
          {filteredWorkflows.map((workflow) => (
            <WorkflowCard
              key={workflow.id}
              workflow={workflow}
              onOpen={() => handleOpenWorkflow(workflow.id)}
              onDelete={() => handleDeleteWorkflow(workflow.id, workflow.name)}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 400 }}>
            <div className="modal-header">
              <h3>새 워크플로우 만들기</h3>
            </div>
            <div className="modal-body">
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">이름 *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="워크플로우 이름"
                  value={newWorkflowName}
                  onChange={(e) => setNewWorkflowName(e.target.value)}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label className="form-label">설명</label>
                <textarea
                  className="form-input"
                  placeholder="워크플로우 설명 (선택)"
                  rows={3}
                  value={newWorkflowDesc}
                  onChange={(e) => setNewWorkflowDesc(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowCreateModal(false)}
                disabled={isCreating}
              >
                취소
              </button>
              <button
                className="btn btn-primary"
                onClick={handleCreateWorkflow}
                disabled={!newWorkflowName.trim() || isCreating}
              >
                {isCreating ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}
                만들기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface WorkflowCardProps {
  workflow: {
    id: string;
    name: string;
    description: string;
    nodeCount: number;
    createdAt: string;
    updatedAt: string;
  };
  onOpen: () => void;
  onDelete: () => void;
}

function WorkflowCard({ workflow, onOpen, onDelete }: WorkflowCardProps) {
  return (
    <div
      className="card"
      style={{ padding: 0, overflow: 'hidden', cursor: 'pointer' }}
      onClick={onOpen}
    >
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h3 style={{ fontWeight: 600, marginBottom: 4 }}>{workflow.name}</h3>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {workflow.description || '설명 없음'}
            </p>
          </div>
          <button
            className="btn-icon"
            onClick={(e) => {
              e.stopPropagation();
              // TODO: dropdown menu
            }}
          >
            <MoreVertical size={16} />
          </button>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          marginTop: 16,
          paddingTop: 12,
          borderTop: '1px solid var(--border-color)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-muted)' }}>
            <Clock size={12} />
            {workflow.updatedAt ? new Date(workflow.updatedAt).toLocaleDateString('ko-KR') : '-'}
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 11,
            color: 'var(--text-muted)'
          }}>
            <FileCode2 size={12} />
            {workflow.nodeCount}개 노드
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{
        display: 'flex',
        borderTop: '1px solid var(--border-color)',
        background: 'var(--bg-secondary)'
      }}>
        <button
          className="btn-icon"
          style={{ flex: 1, borderRadius: 0, padding: '10px 0', fontSize: 11 }}
          onClick={(e) => {
            e.stopPropagation();
            onOpen();
          }}
        >
          <Play size={12} /> 열기
        </button>
        <button
          className="btn-icon"
          style={{ flex: 1, borderRadius: 0, padding: '10px 0', fontSize: 11 }}
          onClick={(e) => {
            e.stopPropagation();
            // TODO: duplicate
          }}
        >
          <Copy size={12} /> 복제
        </button>
        <button
          className="btn-icon"
          style={{ flex: 1, borderRadius: 0, padding: '10px 0', fontSize: 11, color: 'var(--accent-red)' }}
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
        >
          <Trash2 size={12} /> 삭제
        </button>
      </div>
    </div>
  );
}

export default WorkflowList;
