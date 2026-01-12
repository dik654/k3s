/**
 * Custom Edge component for workflow editor
 * Displays animated edges with execution status
 */
import { memo } from 'react';
import {
  EdgeProps,
  getStraightPath,
  EdgeLabelRenderer,
  BaseEdge,
} from 'reactflow';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { useWorkflowStore } from '@/stores/workflowStore';

export const WorkflowEdge = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  source,
  target,
}: EdgeProps) => {
  const { nodeExecutionStatus } = useWorkflowStore();

  // 소스 노드와 타겟 노드의 실행 상태 확인
  const sourceStatus = nodeExecutionStatus[source];
  const targetStatus = nodeExecutionStatus[target];

  // 엣지 상태 결정
  const isActive = sourceStatus === 'success' && (targetStatus === 'running' || targetStatus === 'success');
  const isRunning = sourceStatus === 'success' && targetStatus === 'running';
  const isSuccess = sourceStatus === 'success' && targetStatus === 'success';
  const isPending = sourceStatus === 'pending' || targetStatus === 'pending';

  const [edgePath, labelX, labelY] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  // 엣지 색상 결정
  const edgeColor = isSuccess
    ? '#22c55e' // green
    : isRunning
      ? '#3b82f6' // blue
      : isPending
        ? '#6b7280' // gray
        : '#475569'; // default slate

  return (
    <>
      {/* 기본 엣지 */}
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: edgeColor,
          strokeWidth: 2,
          transition: 'stroke 0.3s ease',
        }}
      />

      {/* 실행 중 애니메이션 */}
      {isRunning && (
        <motion.circle
          r={4}
          fill="#3b82f6"
          initial={{ offsetDistance: '0%' }}
          animate={{ offsetDistance: '100%' }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: 'linear',
          }}
          style={{
            offsetPath: `path('${edgePath}')`,
          }}
        >
          <animate
            attributeName="opacity"
            values="1;0.5;1"
            dur="1s"
            repeatCount="indefinite"
          />
        </motion.circle>
      )}

      {/* 성공 시 체크마크 표시 (선택적) */}
      {isSuccess && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            <div className={clsx(
              'w-4 h-4 rounded-full flex items-center justify-center',
              'bg-green-500 text-white text-xs'
            )}>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
});

WorkflowEdge.displayName = 'WorkflowEdge';

export default WorkflowEdge;
