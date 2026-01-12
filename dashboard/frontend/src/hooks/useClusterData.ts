import { useState, useEffect, useCallback } from 'react';
import { clusterApi, gpuApi, workloadApi } from '@/services/api';
import type {
  NodeMetrics,
  GpuStatus,
  GpuDetailed,
  Workloads,
  PodsData,
  ActionLoadingMap,
} from '@/types';

interface ClusterData {
  nodes: NodeMetrics[];
  pods: PodsData;
  workloads: Workloads;
  gpuStatus: GpuStatus | null;
  gpuDetailed: GpuDetailed | null;
  loading: boolean;
  error: string | null;
}

interface UseClusterDataReturn extends ClusterData {
  refresh: () => Promise<void>;
  actionLoading: ActionLoadingMap;
  handleWorkloadAction: (
    name: string,
    action: 'start' | 'stop',
    config?: Record<string, any>
  ) => Promise<boolean>;
}

export function useClusterData(refreshInterval = 10000): UseClusterDataReturn {
  const [data, setData] = useState<ClusterData>({
    nodes: [],
    pods: { total: 0, by_namespace: {} },
    workloads: {},
    gpuStatus: null,
    gpuDetailed: null,
    loading: true,
    error: null,
  });

  const [actionLoading, setActionLoading] = useState<ActionLoadingMap>({});

  const fetchData = useCallback(async () => {
    try {
      const [nodesRes, podsRes, workloadsRes, gpuStatusRes] = await Promise.all([
        clusterApi.getNodeMetrics(),
        clusterApi.getPods(),
        workloadApi.getStatus(),
        gpuApi.getStatus(),
      ]);

      let gpuDetailedData: GpuDetailed | null = null;
      if (gpuStatusRes.data?.total_gpus > 0) {
        try {
          const gpuDetailedRes = await gpuApi.getDetailed();
          gpuDetailedData = gpuDetailedRes.data;
        } catch {
          // GPU detailed API가 없어도 기본 정보는 표시
        }
      }

      setData({
        nodes: nodesRes.data || [],
        pods: podsRes.data || { total: 0, by_namespace: {} },
        workloads: workloadsRes.data || {},
        gpuStatus: gpuStatusRes.data || null,
        gpuDetailed: gpuDetailedData,
        loading: false,
        error: null,
      });
    } catch (err) {
      setData((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to fetch data',
      }));
    }
  }, []);

  const handleWorkloadAction = useCallback(
    async (
      name: string,
      action: 'start' | 'stop',
      config?: Record<string, any>
    ): Promise<boolean> => {
      setActionLoading((prev) => ({
        ...prev,
        [name]: { loading: true, action },
      }));

      try {
        if (action === 'start') {
          await workloadApi.start(name, config);
        } else {
          await workloadApi.stop(name);
        }

        // 약간의 지연 후 데이터 새로고침
        setTimeout(() => {
          fetchData();
          setActionLoading((prev) => ({
            ...prev,
            [name]: { loading: false },
          }));
        }, 2000);

        return true;
      } catch (err) {
        setActionLoading((prev) => ({
          ...prev,
          [name]: { loading: false },
        }));
        return false;
      }
    },
    [fetchData]
  );

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchData, refreshInterval]);

  return {
    ...data,
    refresh: fetchData,
    actionLoading,
    handleWorkloadAction,
  };
}

export default useClusterData;
