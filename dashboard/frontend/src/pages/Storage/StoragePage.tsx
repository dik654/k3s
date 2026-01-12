import { useState, useCallback, useMemo } from 'react';
import axios from 'axios';
import {
  Archive, Plus, Settings, Folder, Cloud, File, HardDrive,
  Trash2, ChevronRight, Search, ArrowLeft, FolderPlus, Upload,
  Download, Info, X, Eye, RefreshCw, Tag, Clock, Shield, Lock,
  Link2, Copy, ExternalLink
} from 'lucide-react';
import { useStorage, useBucketObjects, useStorageActions } from './hooks/useStorage';
import {
  CreateBucketModal, CreateFolderModal, UploadModal, DeleteConfirmModal
} from './components/StorageModals';
import { StorageAdvancedTabs } from './StorageAdvanced';
import type { StorageObject, DeleteConfirm, PreviewFile, PresignedExpiry } from '@/types';

const API_BASE = '/api';

interface StoragePageProps {
  showToast: (msg: string, type?: string) => void;
}

export function StoragePage({ showToast }: StoragePageProps) {
  const { storageStatus, buckets, loading, refresh: refreshStorage } = useStorage();
  const [selectedBucket, setSelectedBucket] = useState<string | null>(null);
  const [currentPath, setCurrentPath] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Modal states
  const [showCreateBucket, setShowCreateBucket] = useState(false);
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [newBucketName, setNewBucketName] = useState('');
  const [newFolderName, setNewFolderName] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirm | null>(null);

  // Preview & Detail states
  const [previewFile, setPreviewFile] = useState<PreviewFile | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [objectDetail, setObjectDetail] = useState<StorageObject | null>(null);
  const [objectTags, setObjectTags] = useState<Record<string, string>>({});
  const [objectVersions, setObjectVersions] = useState<any[]>([]);
  const [presignedUrl, setPresignedUrl] = useState('');
  const [presignedExpiry, setPresignedExpiry] = useState<PresignedExpiry>({ days: 0, hours: 1, minutes: 0 });
  const [detailLoading, setDetailLoading] = useState(false);

  // Advanced settings
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Drag & Drop
  const [draggedItem, setDraggedItem] = useState<StorageObject | null>(null);
  const [dragOverTarget, setDragOverTarget] = useState<string | null>(null);

  const { objects, loading: objectsLoading, refresh: refreshObjects } = useBucketObjects(selectedBucket, currentPath);
  const {
    actionLoading,
    createBucket,
    deleteBucket,
    createFolder,
    uploadFile,
    deleteObject,
    downloadObject
  } = useStorageActions(showToast);

  // Base64를 UTF-8 문자열로 디코딩
  const decodeBase64UTF8 = (base64: string): string => {
    try {
      const binaryString = atob(base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      return new TextDecoder('utf-8').decode(bytes);
    } catch {
      return atob(base64);
    }
  };

  // 미리보기 가능한 파일 타입 확인
  const isPreviewable = (filename: string): boolean => {
    const ext = filename.toLowerCase().split('.').pop() || '';
    const previewableExtensions = [
      'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico',
      'mp4', 'webm', 'ogg', 'mov',
      'mp3', 'wav', 'aac',
      'pdf',
      'txt', 'md', 'json', 'xml', 'html', 'htm', 'css', 'js', 'ts', 'py', 'yaml', 'yml', 'log', 'csv'
    ];
    return previewableExtensions.includes(ext);
  };

  // 파일 타입 분류
  const getFileType = (filename: string, contentType?: string): string => {
    const ext = filename.toLowerCase().split('.').pop() || '';
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'].includes(ext)) return 'image';
    if (['mp4', 'webm', 'ogg', 'mov'].includes(ext)) return 'video';
    if (['mp3', 'wav', 'aac'].includes(ext) || (ext === 'ogg' && contentType?.includes('audio'))) return 'audio';
    if (ext === 'pdf') return 'pdf';
    if (['html', 'htm'].includes(ext)) return 'html';
    if (['txt', 'md', 'json', 'xml', 'css', 'js', 'ts', 'py', 'yaml', 'yml', 'log', 'csv'].includes(ext)) return 'text';
    return 'unknown';
  };

  // 필터링된 객체 목록
  const filteredObjects = useMemo(() => {
    const parentDir: StorageObject | null = currentPath ? {
      name: '..',
      display_name: '..',
      is_folder: true,
      size: 0,
      size_human: '-',
      last_modified: null,
      isParentDir: true
    } : null;

    const filtered = objects.filter(obj => {
      if (obj.is_folder && currentPath && obj.name === currentPath) return false;
      return obj.display_name.toLowerCase().includes(searchTerm.toLowerCase());
    });

    return parentDir ? [parentDir, ...filtered] : filtered;
  }, [objects, currentPath, searchTerm]);

  // 버킷 생성
  const handleCreateBucket = async () => {
    if (!newBucketName.trim()) return;
    const success = await createBucket(newBucketName);
    if (success) {
      setNewBucketName('');
      setShowCreateBucket(false);
      refreshStorage();
    }
  };

  // 버킷 삭제
  const handleDeleteBucket = async (name: string, force = false) => {
    const success = await deleteBucket(name, force);
    if (success) {
      setDeleteConfirm(null);
      if (selectedBucket === name) {
        setSelectedBucket(null);
      }
      refreshStorage();
    }
  };

  // 폴더 생성
  const handleCreateFolder = async () => {
    if (!newFolderName.trim() || !selectedBucket) return;
    const folderPath = currentPath + newFolderName;
    const success = await createFolder(selectedBucket, folderPath);
    if (success) {
      setNewFolderName('');
      setShowCreateFolder(false);
      refreshObjects();
    }
  };

  // 파일 업로드
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !selectedBucket) return;

    const success = await uploadFile(selectedBucket, currentPath, file);
    if (success) {
      setShowUpload(false);
      refreshObjects();
    }
    event.target.value = '';
  };

  // 객체 삭제
  const handleDeleteObject = async (objectName: string) => {
    if (!selectedBucket) return;
    const success = await deleteObject(selectedBucket, objectName);
    if (success) {
      setDeleteConfirm(null);
      refreshObjects();
    }
  };

  // 다운로드
  const handleDownload = async (objectName: string) => {
    if (!selectedBucket) return;
    await downloadObject(selectedBucket, objectName);
  };

  // 폴더 진입
  const handleNavigate = (obj: StorageObject) => {
    if (obj.is_folder) {
      setCurrentPath(obj.name);
    }
  };

  // 상위 폴더로
  const handleGoBack = () => {
    const parts = currentPath.split('/').filter(Boolean);
    parts.pop();
    setCurrentPath(parts.length > 0 ? parts.join('/') + '/' : '');
  };

  // 파일 미리보기
  const handlePreview = async (obj: StorageObject) => {
    if (obj.is_folder || !selectedBucket) return;

    try {
      setPreviewLoading(true);
      const res = await axios.get(`${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(obj.name)}/download`);
      const fileType = getFileType(obj.display_name, res.data.content_type);

      setPreviewFile({
        name: obj.display_name,
        fullName: obj.name,
        content: res.data.content,
        contentType: res.data.content_type,
        fileType: fileType,
        size: obj.size_human
      });
    } catch (error: any) {
      showToast('파일 미리보기 실패: ' + error.message, 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // 파일 클릭 핸들러
  const handleFileClick = (obj: StorageObject) => {
    if (obj.isParentDir) {
      handleGoBack();
    } else if (obj.is_folder) {
      handleNavigate(obj);
    } else if (isPreviewable(obj.display_name)) {
      handlePreview(obj);
    }
  };

  // 객체 세부 정보 조회
  const handleShowDetail = async (obj: StorageObject) => {
    if (obj.is_folder || !selectedBucket) return;

    setDetailLoading(true);
    setObjectDetail(obj);
    setPresignedUrl('');
    setPresignedExpiry({ days: 0, hours: 1, minutes: 0 });

    try {
      const tagsRes = await axios.get(
        `${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(obj.name)}/tags`
      ).catch(() => ({ data: { tags: {} } }));
      setObjectTags(tagsRes.data.tags || {});

      const versionsRes = await axios.get(
        `${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(obj.name)}/versions`
      ).catch(() => ({ data: { versions: [] } }));
      setObjectVersions(versionsRes.data.versions || []);
    } catch (error) {
      console.error('Failed to fetch object details:', error);
    } finally {
      setDetailLoading(false);
    }
  };

  // Presigned URL 생성
  const handleGeneratePresignedUrl = async () => {
    if (!objectDetail || !selectedBucket) return;

    const expirySeconds =
      (presignedExpiry.days * 86400) +
      (presignedExpiry.hours * 3600) +
      (presignedExpiry.minutes * 60);

    if (expirySeconds <= 0) {
      showToast('만료 시간을 설정해주세요', 'error');
      return;
    }

    try {
      const res = await axios.post(
        `${API_BASE}/storage/buckets/${selectedBucket}/presigned-url`,
        {
          object_name: objectDetail.name,
          method: 'GET',
          expires: expirySeconds
        }
      );
      setPresignedUrl(res.data.url);
      showToast('임시 URL이 생성되었습니다');
    } catch (error: any) {
      showToast('URL 생성 실패: ' + error.message, 'error');
    }
  };

  // 태그 관리
  const handleAddTag = async (key: string, value: string) => {
    if (!objectDetail || !key.trim() || !selectedBucket) return;

    try {
      const newTags = { ...objectTags, [key]: value };
      await axios.put(
        `${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(objectDetail.name)}/tags`,
        { tags: newTags }
      );
      setObjectTags(newTags);
      showToast('태그가 추가되었습니다');
    } catch (error: any) {
      showToast('태그 추가 실패: ' + error.message, 'error');
    }
  };

  const handleRemoveTag = async (key: string) => {
    if (!objectDetail || !selectedBucket) return;

    try {
      const newTags = { ...objectTags };
      delete newTags[key];
      await axios.put(
        `${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(objectDetail.name)}/tags`,
        { tags: newTags }
      );
      setObjectTags(newTags);
      showToast('태그가 삭제되었습니다');
    } catch (error: any) {
      showToast('태그 삭제 실패: ' + error.message, 'error');
    }
  };

  // URL 복사
  const handleCopyUrl = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      showToast('URL이 복사되었습니다');
    } catch {
      showToast('URL 복사 실패', 'error');
    }
  };

  // 드래그 앤 드롭 핸들러
  const handleDragStart = (e: React.DragEvent, obj: StorageObject) => {
    if (obj.is_folder || obj.isParentDir) {
      e.preventDefault();
      return;
    }
    setDraggedItem(obj);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', obj.name);
  };

  const handleDragOver = (e: React.DragEvent, targetObj: StorageObject) => {
    e.preventDefault();
    if (targetObj && (targetObj.is_folder || targetObj.isParentDir)) {
      e.dataTransfer.dropEffect = 'move';
      setDragOverTarget(targetObj.name);
    }
  };

  const handleDragLeave = () => {
    setDragOverTarget(null);
  };

  const handleDrop = async (e: React.DragEvent, targetObj: StorageObject) => {
    e.preventDefault();
    setDragOverTarget(null);

    if (!draggedItem || !targetObj || !selectedBucket) return;
    if (draggedItem.name === targetObj.name) return;

    let newPath = '';

    if (targetObj.isParentDir) {
      const parts = currentPath.split('/').filter(Boolean);
      parts.pop();
      const parentPath = parts.length > 0 ? parts.join('/') + '/' : '';
      newPath = parentPath + draggedItem.display_name;
    } else if (targetObj.is_folder) {
      newPath = targetObj.name + draggedItem.display_name;
    }

    if (newPath) {
      try {
        await axios.post(`${API_BASE}/storage/buckets/${selectedBucket}/objects/move`, {
          source: draggedItem.name,
          destination: newPath
        });
        showToast(`'${draggedItem.display_name}'을 이동했습니다`);
        refreshObjects();
      } catch (error: any) {
        showToast('파일 이동 실패: ' + error.message, 'error');
      }
    }

    setDraggedItem(null);
  };

  const handleDragEnd = () => {
    setDraggedItem(null);
    setDragOverTarget(null);
  };

  if (loading) {
    return (
      <section className="section">
        <div className="card">
          <div className="loading-container">
            <div className="spinner large"></div>
            <p>스토리지 정보를 불러오는 중...</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="section storage-section">
      {/* Storage Status Header */}
      <div className="storage-header">
        <div className="storage-status-card">
          <Archive size={24} />
          <div>
            <h3>RustFS Storage</h3>
            <span className={`status-badge ${storageStatus?.status === 'connected' ? 'running' : 'stopped'}`}>
              {storageStatus?.status === 'connected' ? '연결됨' : '연결 안됨'}
            </span>
          </div>
          {storageStatus?.status === 'connected' && (
            <span className="bucket-count">{buckets.length}개 버킷</span>
          )}
        </div>
        <div className="header-actions">
          <button
            className={`btn ${showAdvanced ? 'btn-primary' : ''}`}
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <Settings size={16} /> 고급 설정
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreateBucket(true)}>
            <Plus size={16} /> 버킷 생성
          </button>
        </div>
      </div>

      {storageStatus?.status !== 'connected' ? (
        <div className="card">
          <div className="no-data">
            <Archive size={48} color="var(--color-text-muted)" />
            <p>RustFS 서비스에 연결할 수 없습니다</p>
            <p className="hint">{storageStatus?.message || 'RustFS를 먼저 실행하세요'}</p>
          </div>
        </div>
      ) : (
        <div className={`storage-layout ${showAdvanced ? 'with-advanced' : ''}`}>
          {/* Bucket List */}
          <div className="bucket-panel">
            <div className="panel-header">
              <h3>버킷</h3>
              <span className="s3-compat-badge" title="AWS S3 API 호환">
                <Cloud size={12} /> S3
              </span>
            </div>
            <div className="bucket-list">
              {buckets.length === 0 ? (
                <div className="empty-state">
                  <Folder size={32} color="var(--color-text-muted)" />
                  <p>버킷이 없습니다</p>
                </div>
              ) : (
                buckets.map((bucket) => (
                  <div
                    key={bucket.name}
                    className={`bucket-item ${selectedBucket === bucket.name ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedBucket(bucket.name);
                      setCurrentPath('');
                    }}
                  >
                    <div className="bucket-icon">
                      <Archive size={20} />
                    </div>
                    <div className="bucket-details">
                      <div className="bucket-name-row">
                        <span className="bucket-name">{bucket.name}</span>
                        <span className="bucket-type-badge">S3 호환</span>
                        <div className="bucket-actions">
                          <button
                            className="btn-icon bucket-settings"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedBucket(bucket.name);
                              setShowAdvanced(true);
                            }}
                            title="버킷 설정"
                          >
                            <Settings size={14} />
                          </button>
                          <button
                            className="btn-icon danger bucket-delete"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteConfirm({ type: 'bucket', name: bucket.name, hasObjects: bucket.object_count > 0 });
                            }}
                            title="버킷 삭제"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                      <div className="bucket-stats">
                        <span className="bucket-stat">
                          <File size={12} />
                          {bucket.object_count} 객체
                        </span>
                        <span className="bucket-stat">
                          <HardDrive size={12} />
                          {bucket.total_size_human}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Advanced Sidebar - inline next to bucket panel */}
          {showAdvanced && (
            <div className="advanced-sidebar-inline">
              <div className="sidebar-header">
                <Settings size={16} />
                <span>설정</span>
                <button className="btn-icon close-btn" onClick={() => setShowAdvanced(false)}>
                  <X size={16} />
                </button>
              </div>
              <StorageAdvancedTabs
                bucketName={selectedBucket || undefined}
                selectedObject={objectDetail?.name}
                showToast={showToast}
              />
            </div>
          )}

          {/* Objects Panel */}
          <div className="objects-panel">
            {!selectedBucket ? (
              <div className="no-bucket-selected">
                <Folder size={48} color="var(--color-text-muted)" />
                <p>버킷을 선택하세요</p>
              </div>
            ) : (
              <>
                <div className="objects-toolbar">
                  <div className="breadcrumb">
                    <span className="breadcrumb-bucket" onClick={() => setCurrentPath('')}>
                      {selectedBucket}
                    </span>
                    {currentPath && (
                      <>
                        <ChevronRight size={16} />
                        {currentPath.split('/').filter(Boolean).map((part, idx, arr) => (
                          <span key={idx}>
                            <span
                              className="breadcrumb-part"
                              onClick={() => setCurrentPath(arr.slice(0, idx + 1).join('/') + '/')}
                            >
                              {part}
                            </span>
                            {idx < arr.length - 1 && <ChevronRight size={16} />}
                          </span>
                        ))}
                      </>
                    )}
                  </div>
                  <div className="toolbar-actions">
                    <div className="search-box">
                      <Search size={16} />
                      <input
                        type="text"
                        placeholder="검색..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                    </div>
                    {currentPath && (
                      <button className="btn btn-outline" onClick={handleGoBack}>
                        <ArrowLeft size={16} /> 상위 폴더
                      </button>
                    )}
                    <button className="btn btn-outline" onClick={() => setShowCreateFolder(true)}>
                      <FolderPlus size={16} /> 폴더
                    </button>
                    <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
                      <Upload size={16} /> 업로드
                    </button>
                  </div>
                </div>

                <div className="objects-list">
                  {objectsLoading ? (
                    <div className="loading-container">
                      <div className="spinner"></div>
                    </div>
                  ) : filteredObjects.length === 0 ? (
                    <div className="empty-state">
                      <File size={32} color="var(--color-text-muted)" />
                      <p>{searchTerm ? '검색 결과가 없습니다' : '이 위치에 파일이 없습니다'}</p>
                    </div>
                  ) : (
                    <table className="objects-table">
                      <thead>
                        <tr>
                          <th>이름</th>
                          <th>크기</th>
                          <th>수정일</th>
                          <th>작업</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredObjects.map((obj) => (
                          <tr
                            key={obj.name}
                            className={`${obj.is_folder ? 'folder-row' : ''} ${obj.isParentDir ? 'parent-dir-row' : ''} ${dragOverTarget === obj.name ? 'drag-over' : ''} ${draggedItem?.name === obj.name ? 'dragging' : ''}`}
                            draggable={!obj.is_folder && !obj.isParentDir}
                            onDragStart={(e) => handleDragStart(e, obj)}
                            onDragOver={(e) => handleDragOver(e, obj)}
                            onDragLeave={handleDragLeave}
                            onDrop={(e) => handleDrop(e, obj)}
                            onDragEnd={handleDragEnd}
                          >
                            <td>
                              <div
                                className="object-name"
                                onClick={() => handleFileClick(obj)}
                                style={{ cursor: obj.is_folder || isPreviewable(obj.display_name) ? 'pointer' : 'default' }}
                              >
                                {obj.isParentDir ? (
                                  <ArrowLeft size={18} color="var(--color-text-muted)" />
                                ) : obj.is_folder ? (
                                  <Folder size={18} color="var(--color-accent-yellow)" />
                                ) : (
                                  <File size={18} color={isPreviewable(obj.display_name) ? 'var(--color-accent-blue)' : 'var(--color-text-muted)'} />
                                )}
                                <span>{obj.display_name}</span>
                                {!obj.is_folder && isPreviewable(obj.display_name) && (
                                  <span className="preview-hint" title="클릭하여 미리보기">👁</span>
                                )}
                              </div>
                            </td>
                            <td>{obj.size_human}</td>
                            <td>{obj.last_modified ? new Date(obj.last_modified).toLocaleDateString() : '-'}</td>
                            <td>
                              <div className="action-buttons">
                                {!obj.is_folder && !obj.isParentDir && (
                                  <>
                                    <button
                                      className="btn-icon"
                                      onClick={() => handleShowDetail(obj)}
                                      title="세부 정보"
                                    >
                                      <Info size={14} />
                                    </button>
                                    <button
                                      className="btn-icon"
                                      onClick={() => handleDownload(obj.name)}
                                      title="다운로드"
                                    >
                                      <Download size={14} />
                                    </button>
                                    <button
                                      className="btn-icon danger"
                                      onClick={() => setDeleteConfirm({ type: 'object', name: obj.name, isFolder: obj.is_folder })}
                                      title="삭제"
                                    >
                                      <Trash2 size={14} />
                                    </button>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      <CreateBucketModal
        isOpen={showCreateBucket}
        newBucketName={newBucketName}
        actionLoading={actionLoading}
        onClose={() => setShowCreateBucket(false)}
        onChange={setNewBucketName}
        onCreate={handleCreateBucket}
      />

      <CreateFolderModal
        isOpen={showCreateFolder}
        newFolderName={newFolderName}
        actionLoading={actionLoading}
        onClose={() => setShowCreateFolder(false)}
        onChange={setNewFolderName}
        onCreate={handleCreateFolder}
      />

      <UploadModal
        isOpen={showUpload}
        actionLoading={actionLoading}
        onClose={() => setShowUpload(false)}
        onUpload={handleFileUpload}
      />

      <DeleteConfirmModal
        deleteConfirm={deleteConfirm}
        actionLoading={actionLoading}
        onClose={() => setDeleteConfirm(null)}
        onConfirm={() => {
          if (deleteConfirm?.type === 'bucket') {
            handleDeleteBucket(deleteConfirm.name, deleteConfirm.hasObjects);
          } else if (deleteConfirm) {
            handleDeleteObject(deleteConfirm.name);
          }
        }}
      />

      {/* Preview Modal */}
      {(previewFile || previewLoading) && (
        <div className="modal-overlay preview-overlay" onClick={() => setPreviewFile(null)}>
          <div className="modal modal-preview" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{previewFile?.name || '파일 미리보기'}</h3>
              <div className="modal-header-actions">
                {previewFile && (
                  <button
                    className="btn btn-sm btn-outline"
                    onClick={() => handleDownload(previewFile.fullName)}
                    title="다운로드"
                  >
                    <Download size={16} /> 다운로드
                  </button>
                )}
                <button className="btn-icon" onClick={() => setPreviewFile(null)}>
                  <X size={20} />
                </button>
              </div>
            </div>
            <div className="modal-body preview-content">
              {previewLoading ? (
                <div className="preview-loading">
                  <RefreshCw className="spin" size={32} />
                  <p>파일을 불러오는 중...</p>
                </div>
              ) : previewFile?.fileType === 'image' ? (
                <img
                  src={`data:${previewFile.contentType};base64,${previewFile.content}`}
                  alt={previewFile.name}
                  className="preview-image"
                />
              ) : previewFile?.fileType === 'video' ? (
                <video
                  src={`data:${previewFile.contentType};base64,${previewFile.content}`}
                  controls
                  autoPlay
                  className="preview-video"
                />
              ) : previewFile?.fileType === 'audio' ? (
                <div className="preview-audio-container">
                  <div className="audio-icon">🎵</div>
                  <p>{previewFile.name}</p>
                  <audio
                    src={`data:${previewFile.contentType};base64,${previewFile.content}`}
                    controls
                    autoPlay
                    className="preview-audio"
                  />
                </div>
              ) : previewFile?.fileType === 'pdf' && selectedBucket ? (
                <iframe
                  src={`${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(previewFile.fullName)}/stream`}
                  className="preview-pdf"
                  title={previewFile.name}
                />
              ) : previewFile?.fileType === 'html' ? (
                <iframe
                  srcDoc={(() => {
                    try {
                      const htmlContent = decodeBase64UTF8(previewFile.content);
                      const fontStyle = `
                        <meta charset="UTF-8">
                        <style>
                          @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
                          * { font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif; }
                          body { margin: 16px; line-height: 1.6; }
                        </style>
                      `;
                      if (htmlContent.includes('<head>')) {
                        return htmlContent.replace('<head>', '<head>' + fontStyle);
                      }
                      return '<!DOCTYPE html><html><head>' + fontStyle + '</head><body>' + htmlContent + '</body></html>';
                    } catch {
                      return '<p>HTML을 표시할 수 없습니다</p>';
                    }
                  })()}
                  className="preview-html"
                  title={previewFile.name}
                  sandbox="allow-same-origin allow-scripts"
                />
              ) : previewFile?.fileType === 'text' ? (
                <pre className="preview-text">
                  {decodeBase64UTF8(previewFile.content)}
                </pre>
              ) : (
                <div className="preview-unsupported">
                  <File size={48} />
                  <p>미리보기를 지원하지 않는 파일 형식입니다</p>
                  {previewFile && (
                    <button
                      className="btn btn-primary"
                      onClick={() => handleDownload(previewFile.fullName)}
                    >
                      <Download size={16} /> 다운로드
                    </button>
                  )}
                </div>
              )}
            </div>
            {previewFile && (
              <div className="modal-footer preview-footer">
                <span className="file-info">
                  크기: {previewFile.size} | 타입: {previewFile.contentType}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Object Detail Panel */}
      {objectDetail && (
        <div className="object-detail-panel">
          <div className="detail-panel-header">
            <h3>객체 세부 정보</h3>
            <button className="btn-icon" onClick={() => setObjectDetail(null)}>
              <X size={20} />
            </button>
          </div>

          <div className="detail-panel-content">
            <div className="detail-actions">
              <button
                className="btn btn-outline"
                onClick={() => handleDownload(objectDetail.name)}
              >
                <Download size={16} /> 다운로드
              </button>
              {isPreviewable(objectDetail.display_name) && (
                <button
                  className="btn btn-outline"
                  onClick={() => handlePreview(objectDetail)}
                >
                  <Eye size={16} /> 미리보기
                </button>
              )}
            </div>

            {/* 객체 정보 */}
            <div className="detail-section">
              <h4><File size={16} /> 객체 정보</h4>
              <div className="detail-info-grid">
                <div className="detail-info-item">
                  <label>객체 이름</label>
                  <span className="info-value monospace">{objectDetail.display_name}</span>
                </div>
                <div className="detail-info-item">
                  <label>전체 경로</label>
                  <span className="info-value monospace">{objectDetail.name}</span>
                </div>
                <div className="detail-info-item">
                  <label>객체 크기</label>
                  <span className="info-value">{objectDetail.size_human} ({objectDetail.size?.toLocaleString()} bytes)</span>
                </div>
                <div className="detail-info-item">
                  <label>객체 유형</label>
                  <span className="info-value">{objectDetail.content_type || 'application/octet-stream'}</span>
                </div>
                <div className="detail-info-item">
                  <label>ETag</label>
                  <span className="info-value monospace">{objectDetail.etag || '-'}</span>
                </div>
                <div className="detail-info-item">
                  <label>마지막 수정 시간</label>
                  <span className="info-value">
                    {objectDetail.last_modified
                      ? new Date(objectDetail.last_modified).toLocaleString('ko-KR')
                      : '-'}
                  </span>
                </div>
              </div>
            </div>

            {/* 태그 섹션 */}
            <div className="detail-section">
              <h4><Tag size={16} /> 태그 설정</h4>
              {detailLoading ? (
                <div className="loading-inline"><RefreshCw className="spin" size={16} /> 로딩 중...</div>
              ) : (
                <>
                  <div className="tags-display">
                    {Object.entries(objectTags).length > 0 ? (
                      Object.entries(objectTags).map(([key, value]) => (
                        <div key={key} className="tag-chip">
                          <span className="tag-chip-key">{key}</span>
                          <span className="tag-chip-value">{value}</span>
                          <button className="tag-chip-remove" onClick={() => handleRemoveTag(key)}>
                            <X size={12} />
                          </button>
                        </div>
                      ))
                    ) : (
                      <p className="no-data-text">설정된 태그가 없습니다</p>
                    )}
                  </div>
                  <div className="add-tag-inline">
                    <input
                      type="text"
                      placeholder="키"
                      id="new-tag-key"
                      className="tag-input"
                    />
                    <input
                      type="text"
                      placeholder="값"
                      id="new-tag-value"
                      className="tag-input"
                    />
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={() => {
                        const keyEl = document.getElementById('new-tag-key') as HTMLInputElement;
                        const valueEl = document.getElementById('new-tag-value') as HTMLInputElement;
                        if (keyEl?.value) {
                          handleAddTag(keyEl.value, valueEl?.value || '');
                          keyEl.value = '';
                          if (valueEl) valueEl.value = '';
                        }
                      }}
                    >
                      추가
                    </button>
                  </div>
                </>
              )}
            </div>

            {/* 버전 정보 */}
            <div className="detail-section">
              <h4><Clock size={16} /> 버전 정보</h4>
              {detailLoading ? (
                <div className="loading-inline"><RefreshCw className="spin" size={16} /> 로딩 중...</div>
              ) : objectVersions.length > 0 ? (
                <div className="versions-display">
                  {objectVersions.slice(0, 5).map((ver, idx) => (
                    <div key={ver.version_id || idx} className="version-row">
                      <div className="version-row-info">
                        <span className="version-id-text">{ver.version_id || 'null'}</span>
                        <span className="version-date-text">
                          {ver.last_modified ? new Date(ver.last_modified).toLocaleString('ko-KR') : '-'}
                        </span>
                      </div>
                      {ver.is_latest && <span className="version-badge latest">최신</span>}
                      {ver.is_delete_marker && <span className="version-badge deleted">삭제됨</span>}
                    </div>
                  ))}
                  {objectVersions.length > 5 && (
                    <p className="more-text">외 {objectVersions.length - 5}개 버전</p>
                  )}
                </div>
              ) : (
                <p className="no-data-text">버전 관리가 비활성화되어 있거나 버전 정보가 없습니다</p>
              )}
            </div>

            {/* 법적 보관 */}
            <div className="detail-section">
              <h4><Shield size={16} /> 법적 보관</h4>
              <div className="legal-hold-status">
                <Lock size={16} color="var(--color-text-muted)" />
                <span className="no-data-text">법적 보관이 설정되지 않았습니다</span>
              </div>
            </div>

            {/* 임시 URL 생성 */}
            <div className="detail-section">
              <h4><Link2 size={16} /> 임시 URL 만료</h4>
              <div className="presigned-form-inline">
                <div className="expiry-inputs">
                  <div className="expiry-input-group">
                    <input
                      type="number"
                      min="0"
                      max="7"
                      value={presignedExpiry.days}
                      onChange={(e) => setPresignedExpiry({ ...presignedExpiry, days: parseInt(e.target.value) || 0 })}
                    />
                    <label>일</label>
                  </div>
                  <div className="expiry-input-group">
                    <input
                      type="number"
                      min="0"
                      max="23"
                      value={presignedExpiry.hours}
                      onChange={(e) => setPresignedExpiry({ ...presignedExpiry, hours: parseInt(e.target.value) || 0 })}
                    />
                    <label>시간</label>
                  </div>
                  <div className="expiry-input-group">
                    <input
                      type="number"
                      min="0"
                      max="59"
                      value={presignedExpiry.minutes}
                      onChange={(e) => setPresignedExpiry({ ...presignedExpiry, minutes: parseInt(e.target.value) || 0 })}
                    />
                    <label>분</label>
                  </div>
                </div>
                <button className="btn btn-primary" onClick={handleGeneratePresignedUrl}>
                  URL 생성
                </button>
              </div>

              {presignedUrl && (
                <div className="presigned-result-inline">
                  <input type="text" value={presignedUrl} readOnly className="presigned-url-input" />
                  <button className="btn btn-outline" onClick={() => handleCopyUrl(presignedUrl)}>
                    <Copy size={14} />
                  </button>
                  <a
                    href={presignedUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-outline"
                  >
                    <ExternalLink size={14} />
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </section>
  );
}

export default StoragePage;
