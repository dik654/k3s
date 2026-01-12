import { memo, useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { motion } from 'framer-motion';
import {
  MessageSquare,
  Search,
  Bot,
  Share2,
  Database,
  FileText,
  GitBranch,
  GitMerge,
  Shuffle,
  Hash,
  Edit3,
  Repeat,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Play,
  Square,
  User,
  Layers,
  Wrench,
  CornerDownLeft,
  Columns,
  Zap,
  Trash2,
  Filter,
  Scissors,
  Globe,
  Webhook,
  HardDrive,
  Variable,
  Shield,
  AlertTriangle,
  Terminal,
  Timer,
  PlayCircle,
  Calendar,
  Settings,
} from 'lucide-react';
import clsx from 'clsx';
import { useWorkflowStore } from '@/stores/workflowStore';

// 아이콘 맵 확장
const iconMap: Record<string, React.ComponentType<any>> = {
  'message-square': MessageSquare,
  'search': Search,
  'bot': Bot,
  'share-2': Share2,
  'database': Database,
  'file-text': FileText,
  'git-branch': GitBranch,
  'git-merge': GitMerge,
  'shuffle': Shuffle,
  'hash': Hash,
  'edit-3': Edit3,
  'repeat': Repeat,
  'play': Play,
  'square': Square,
  'user': User,
  'layers': Layers,
  'wrench': Wrench,
  'corner-down-left': CornerDownLeft,
  'columns': Columns,
  'clock': Clock,
  'zap': Zap,
  'filter': Filter,
  'scissors': Scissors,
  'globe': Globe,
  'webhook': Webhook,
  'hard-drive': HardDrive,
  'variable': Variable,
  'shield': Shield,
  'alert-triangle': AlertTriangle,
  'terminal': Terminal,
  'timer': Timer,
  'play-circle': PlayCircle,
  'calendar': Calendar,
  'settings': Settings,
  'regex': FileText, // regex 아이콘 대체
};

// 실행 상태별 스타일
const executionStyles = {
  pending: { borderColor: '#64748b', glowColor: 'transparent' },
  running: { borderColor: '#3b82f6', glowColor: 'rgba(59, 130, 246, 0.4)' },
  success: { borderColor: '#22c55e', glowColor: 'rgba(34, 197, 94, 0.3)' },
  error: { borderColor: '#ef4444', glowColor: 'rgba(239, 68, 68, 0.3)' },
};

// 실행 상태 아이콘
const ExecutionStatusBadge = ({ status }: { status?: string }) => {
  if (!status) return null;

  const icons = {
    running: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    success: <CheckCircle2 className="w-3.5 h-3.5" />,
    error: <XCircle className="w-3.5 h-3.5" />,
    pending: <Clock className="w-3.5 h-3.5" />,
  };

  const colors = {
    running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    success: 'bg-green-500/20 text-green-400 border-green-500/30',
    error: 'bg-red-500/20 text-red-400 border-red-500/30',
    pending: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  };

  return (
    <motion.div
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={clsx(
        'absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center border',
        colors[status as keyof typeof colors]
      )}
    >
      {icons[status as keyof typeof icons]}
    </motion.div>
  );
};

export const WorkflowNode = memo(({ id, data, selected }: NodeProps) => {
  const { selectedNodeId, nodeExecutionStatus, deleteNode } = useWorkflowStore();
  const isSelected = selected || selectedNodeId === id;
  const [isHovered, setIsHovered] = useState(false);
  const executionStatus = nodeExecutionStatus[id];

  const Icon = iconMap[data.icon] || Zap;
  const execStyle = executionStatus ? executionStyles[executionStatus as keyof typeof executionStyles] : null;

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        position: 'relative',
        width: 200,
        background: '#1e293b',
        borderRadius: 12,
        border: isSelected
          ? `2px solid ${data.color}`
          : execStyle
            ? `2px solid ${execStyle.borderColor}`
            : '1px solid #334155',
        boxShadow: isSelected
          ? `0 0 20px ${data.color}40`
          : execStyle
            ? `0 0 12px ${execStyle.glowColor}`
            : '0 4px 12px rgba(0,0,0,0.3)',
      }}
    >
      {/* 입력 핸들 */}
      {data.inputs?.map((input: any, index: number) => (
        <Handle
          key={input.id}
          type="target"
          position={Position.Left}
          id={input.id}
          style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            border: '2px solid #475569',
            background: '#1e293b',
            top: `${50 + (index - (data.inputs.length - 1) / 2) * 15}%`,
          }}
        />
      ))}

      {/* 출력 핸들 */}
      {data.outputs?.map((output: any, index: number) => (
        <Handle
          key={output.id}
          type="source"
          position={Position.Right}
          id={output.id}
          style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            border: `2px solid ${data.color}`,
            background: isHovered ? data.color : '#1e293b',
            top: `${50 + (index - (data.outputs.length - 1) / 2) * 15}%`,
          }}
        />
      ))}
        {/* 실행 상태 배지 */}
        <ExecutionStatusBadge status={executionStatus} />

        {/* 상단 컬러 바 */}
        <div style={{ height: 3, width: '100%', backgroundColor: data.color }} />

        {/* 헤더 영역 */}
        <div style={{ padding: '12px 12px 8px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* 아이콘 */}
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: `linear-gradient(135deg, ${data.color}, ${data.color}cc)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Icon style={{ width: 18, height: 18, color: 'white' }} strokeWidth={2.5} />
          </div>

          {/* 노드 이름 및 타입 */}
          <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
            <div style={{
              fontWeight: 600,
              fontSize: 13,
              color: 'white',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {data.name || data.label}
            </div>
            <div style={{
              fontSize: 10,
              color: '#94a3b8',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {data.type}
            </div>
          </div>

        </div>

        {/* 포트 섹션 */}
        <div style={{
          padding: '8px 12px 10px 12px',
          borderTop: '1px solid #334155',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 10,
        }}>
          {/* 입력 포트 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {data.inputs?.map((input: any) => (
              <div key={input.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: input.required ? '#fbbf24' : '#64748b',
                }} />
                <span style={{ color: '#94a3b8' }}>{input.name}</span>
              </div>
            ))}
          </div>

          {/* 출력 포트 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
            {data.outputs?.map((output: any) => (
              <div key={output.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: '#94a3b8' }}>{output.name}</span>
                <div style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: data.color,
                  boxShadow: `0 0 4px ${data.color}`,
                }} />
              </div>
            ))}
          </div>
        </div>

        {/* 실행 중 애니메이션 */}
        {executionStatus === 'running' && (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            pointerEvents: 'none',
            background: `linear-gradient(90deg, transparent, ${data.color}15, transparent)`,
            animation: 'shimmer 1.5s infinite',
          }} />
        )}

        {/* 삭제 버튼 - 호버시 표시 */}
        {isHovered && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              deleteNode(id);
            }}
            style={{
              position: 'absolute',
              top: -8,
              right: -8,
              width: 20,
              height: 20,
              borderRadius: '50%',
              border: 'none',
              background: '#ef4444',
              color: 'white',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
            }}
          >
            <Trash2 style={{ width: 10, height: 10 }} />
          </button>
        )}
    </div>
  );
});

WorkflowNode.displayName = 'WorkflowNode';

export default WorkflowNode;
