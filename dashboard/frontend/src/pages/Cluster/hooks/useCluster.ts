import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export interface ClusterNode {
  name: string;
  role: 'master' | 'worker';
  status: string;
  internal_ip: string;
  cpu_capacity: number;
  memory_capacity: string;
  gpu_count: number;
  pod_count: number;
  pod_capacity: number;
  kubelet_version: string;
}

export interface NodeDetail extends ClusterNode {
  os: string;
  kernel: string;
  architecture: string;
  container_runtime: string;
  pods: Array<{ namespace: string; name: string; status: string }>;
  labels: Record<string, string>;
  taints: Array<{ key: string; value: string; effect: string }>;
}

export interface ClusterResources {
  cpu: { total: number; used: number };
  memory: { total: number; total_human: string; used: number };
  gpu: { total: number; used: number };
  pods: { capacity: number; used: number };
}

export interface JoinCommand {
  master_ip: string;
  instructions: {
    worker: string;
    master: string;
  };
  note: string;
}

export function useCluster(showToast: (msg: string, type?: string) => void) {
  const [nodes, setNodes] = useState<ClusterNode[]>([]);
  const [clusterResources, setClusterResources] = useState<ClusterResources | null>(null);
  const [loading, setLoading] = useState(true);
  const [initialLoaded, setInitialLoaded] = useState(false);

  const fetchNodes = useCallback(async () => {
    try {
      const res = await axios.get('/api/cluster/nodes');
      setNodes(res.data.nodes || []);
    } catch (error) {
      showToast('노드 목록 조회 실패', 'error');
    }
  }, [showToast]);

  const fetchResources = useCallback(async () => {
    try {
      const res = await axios.get('/api/cluster/resources');
      setClusterResources(res.data);
    } catch (error) {
      console.error('리소스 조회 실패:', error);
    }
  }, []);

  useEffect(() => {
    const loadData = async () => {
      if (!initialLoaded) setLoading(true);
      await Promise.all([fetchNodes(), fetchResources()]);
      if (!initialLoaded) {
        setLoading(false);
        setInitialLoaded(true);
      }
    };
    loadData();
    const interval = setInterval(() => {
      fetchNodes();
      fetchResources();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchNodes, fetchResources, initialLoaded]);

  return { nodes, clusterResources, loading, refresh: fetchNodes };
}

export function useNodeDetail(nodeName: string | null, showToast: (msg: string, type?: string) => void) {
  const [nodeDetail, setNodeDetail] = useState<NodeDetail | null>(null);

  const fetchNodeDetail = useCallback(async (name: string) => {
    try {
      const res = await axios.get(`/api/cluster/nodes/${name}`);
      setNodeDetail(res.data);
    } catch (error) {
      showToast('노드 상세 정보 조회 실패', 'error');
    }
  }, [showToast]);

  useEffect(() => {
    if (nodeName) {
      fetchNodeDetail(nodeName);
    } else {
      setNodeDetail(null);
    }
  }, [nodeName, fetchNodeDetail]);

  return nodeDetail;
}

export function useNodeActions(showToast: (msg: string, type?: string) => void, onSuccess: () => void) {
  const [actionLoading, setActionLoading] = useState<Record<string, string | null>>({});

  const handleNodeAction = async (nodeName: string, action: 'cordon' | 'uncordon' | 'drain' | 'delete') => {
    setActionLoading(prev => ({ ...prev, [nodeName]: action }));
    try {
      let res;
      switch (action) {
        case 'cordon':
          res = await axios.post(`/api/cluster/nodes/${nodeName}/cordon`);
          break;
        case 'uncordon':
          res = await axios.post(`/api/cluster/nodes/${nodeName}/uncordon`);
          break;
        case 'drain':
          if (!window.confirm(`'${nodeName}' 노드를 드레인하시겠습니까? 모든 Pod가 다른 노드로 이동됩니다.`)) {
            setActionLoading(prev => ({ ...prev, [nodeName]: null }));
            return;
          }
          res = await axios.post(`/api/cluster/nodes/${nodeName}/drain`);
          break;
        case 'delete':
          if (!window.confirm(`'${nodeName}' 노드를 클러스터에서 제거하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
            setActionLoading(prev => ({ ...prev, [nodeName]: null }));
            return;
          }
          res = await axios.delete(`/api/cluster/nodes/${nodeName}`);
          break;
        default:
          return;
      }
      showToast(res.data.message);
      onSuccess();
    } catch (error: any) {
      showToast(error.response?.data?.detail || '작업 실패', 'error');
    } finally {
      setActionLoading(prev => ({ ...prev, [nodeName]: null }));
    }
  };

  return { actionLoading, handleNodeAction };
}

export function useJoinCommand(showToast: (msg: string, type?: string) => void) {
  const [joinCommand, setJoinCommand] = useState<JoinCommand | null>(null);

  const fetchJoinCommand = useCallback(async () => {
    try {
      const res = await axios.get('/api/cluster/join-command');
      setJoinCommand(res.data);
    } catch (error) {
      showToast('조인 명령어 조회 실패', 'error');
    }
  }, [showToast]);

  return { joinCommand, fetchJoinCommand };
}
