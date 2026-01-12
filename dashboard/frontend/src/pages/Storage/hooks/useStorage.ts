import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import type { StorageStatus, Bucket, StorageObject } from '@/types';

const API_BASE = '/api';

export function useStorage() {
  const [storageStatus, setStorageStatus] = useState<StorageStatus | null>(null);
  const [buckets, setBuckets] = useState<Bucket[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStorageData = useCallback(async () => {
    try {
      const [statusRes, bucketsRes] = await Promise.all([
        axios.get(`${API_BASE}/storage/status`),
        axios.get(`${API_BASE}/storage/buckets`).catch(() => ({ data: { buckets: [] } }))
      ]);
      setStorageStatus(statusRes.data);
      setBuckets(bucketsRes.data.buckets || []);
    } catch (error: any) {
      setStorageStatus({ status: 'disconnected', error: error.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStorageData();
  }, [fetchStorageData]);

  return { storageStatus, buckets, loading, refresh: fetchStorageData };
}

export function useBucketObjects(bucketName: string | null, currentPath: string) {
  const [objects, setObjects] = useState<StorageObject[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchObjects = useCallback(async () => {
    if (!bucketName) return;

    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/storage/buckets/${bucketName}/objects`, {
        params: { prefix: currentPath }
      });
      setObjects(res.data.objects || []);
    } catch (error) {
      console.error('Failed to fetch objects:', error);
    } finally {
      setLoading(false);
    }
  }, [bucketName, currentPath]);

  useEffect(() => {
    fetchObjects();
  }, [fetchObjects]);

  return { objects, loading, refresh: fetchObjects };
}

export function useStorageActions(showToast: (msg: string, type?: string) => void) {
  const [actionLoading, setActionLoading] = useState(false);

  const createBucket = async (name: string) => {
    setActionLoading(true);
    try {
      await axios.post(`${API_BASE}/storage/buckets`, { name: name.toLowerCase() });
      showToast(`버킷 '${name}'이 생성되었습니다`);
      return true;
    } catch (error: any) {
      showToast(error.response?.data?.detail || '버킷 생성 실패', 'error');
      return false;
    } finally {
      setActionLoading(false);
    }
  };

  const deleteBucket = async (name: string, force = false) => {
    setActionLoading(true);
    try {
      await axios.delete(`${API_BASE}/storage/buckets/${name}`, { params: { force } });
      showToast(`버킷 '${name}'이 삭제되었습니다`);
      return true;
    } catch (error: any) {
      showToast(error.response?.data?.detail || '버킷 삭제 실패', 'error');
      return false;
    } finally {
      setActionLoading(false);
    }
  };

  const createFolder = async (bucketName: string, folderPath: string) => {
    setActionLoading(true);
    try {
      await axios.post(`${API_BASE}/storage/buckets/${bucketName}/folders`, {
        folder_name: folderPath
      });
      showToast(`폴더가 생성되었습니다`);
      return true;
    } catch (error: any) {
      showToast(error.response?.data?.detail || '폴더 생성 실패', 'error');
      return false;
    } finally {
      setActionLoading(false);
    }
  };

  const uploadFile = async (bucketName: string, path: string, file: File) => {
    setActionLoading(true);
    return new Promise<boolean>((resolve) => {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const base64Content = (e.target?.result as string).split(',')[1];
          await axios.post(`${API_BASE}/storage/buckets/${bucketName}/objects`, {
            object_name: path + file.name,
            content: base64Content,
            content_type: file.type || 'application/octet-stream'
          });
          showToast(`'${file.name}'이 업로드되었습니다`);
          resolve(true);
        } catch (error: any) {
          showToast(error.response?.data?.detail || '업로드 실패', 'error');
          resolve(false);
        } finally {
          setActionLoading(false);
        }
      };
      reader.onerror = () => {
        showToast('파일을 읽는 중 오류가 발생했습니다', 'error');
        setActionLoading(false);
        resolve(false);
      };
      reader.readAsDataURL(file);
    });
  };

  const deleteObject = async (bucketName: string, objectName: string) => {
    setActionLoading(true);
    try {
      await axios.delete(`${API_BASE}/storage/buckets/${bucketName}/objects/${encodeURIComponent(objectName)}`);
      showToast('삭제되었습니다');
      return true;
    } catch (error: any) {
      showToast(error.response?.data?.detail || '삭제 실패', 'error');
      return false;
    } finally {
      setActionLoading(false);
    }
  };

  const downloadObject = async (bucketName: string, objectName: string) => {
    setActionLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/storage/buckets/${bucketName}/objects/${encodeURIComponent(objectName)}/download`);
      const link = document.createElement('a');
      link.href = `data:${res.data.content_type};base64,${res.data.content}`;
      link.download = objectName.split('/').pop() || objectName;
      link.click();
      showToast('다운로드가 시작되었습니다');
      return true;
    } catch (error: any) {
      showToast(error.response?.data?.detail || '다운로드 실패', 'error');
      return false;
    } finally {
      setActionLoading(false);
    }
  };

  return {
    actionLoading,
    createBucket,
    deleteBucket,
    createFolder,
    uploadFile,
    deleteObject,
    downloadObject
  };
}
