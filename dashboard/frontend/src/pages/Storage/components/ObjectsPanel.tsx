import { useState } from 'react';
import {
  Folder, File, ChevronRight, Search, ArrowLeft,
  FolderPlus, Upload, Download, Trash2, Info
} from 'lucide-react';
import type { StorageObject } from '@/types';

interface ObjectsPanelProps {
  selectedBucket: string | null;
  currentPath: string;
  objects: StorageObject[];
  loading: boolean;
  onNavigate: (path: string) => void;
  onGoBack: () => void;
  onShowCreateFolder: () => void;
  onShowUpload: () => void;
  onDownload: (objectName: string) => void;
  onDelete: (objectName: string, isFolder: boolean) => void;
  onShowDetail: (obj: StorageObject) => void;
  onPreview: (obj: StorageObject) => void;
}

const isPreviewable = (filename: string) => {
  const ext = filename.toLowerCase().split('.').pop() || '';
  const previewableExtensions = [
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico',
    'mp4', 'webm', 'ogg', 'mov', 'mp3', 'wav', 'aac', 'pdf',
    'txt', 'md', 'json', 'xml', 'html', 'htm', 'css', 'js', 'ts', 'py', 'yaml', 'yml', 'log', 'csv'
  ];
  return previewableExtensions.includes(ext);
};

export function ObjectsPanel({
  selectedBucket,
  currentPath,
  objects,
  loading,
  onNavigate,
  onGoBack,
  onShowCreateFolder,
  onShowUpload,
  onDownload,
  onDelete,
  onShowDetail,
  onPreview
}: ObjectsPanelProps) {
  const [searchTerm, setSearchTerm] = useState('');

  if (!selectedBucket) {
    return (
      <div className="no-bucket-selected">
        <Folder size={48} color="var(--color-text-muted)" />
        <p>버킷을 선택하세요</p>
      </div>
    );
  }

  const filteredObjects = [
    ...(currentPath ? [{
      name: '..',
      display_name: '..',
      is_folder: true,
      size: 0,
      size_human: '-',
      last_modified: null,
      isParentDir: true
    }] : []),
    ...objects.filter(obj => {
      if (obj.is_folder && currentPath && obj.name === currentPath) return false;
      return obj.display_name.toLowerCase().includes(searchTerm.toLowerCase());
    })
  ];

  const handleFileClick = (obj: StorageObject) => {
    if (obj.isParentDir) {
      onGoBack();
    } else if (obj.is_folder) {
      onNavigate(obj.name);
    } else if (isPreviewable(obj.display_name)) {
      onPreview(obj);
    }
  };

  return (
    <>
      <div className="objects-toolbar">
        <div className="breadcrumb">
          <span className="breadcrumb-bucket" onClick={() => onNavigate('')}>
            {selectedBucket}
          </span>
          {currentPath && (
            <>
              <ChevronRight size={16} />
              {currentPath.split('/').filter(Boolean).map((part, idx, arr) => (
                <span key={idx}>
                  <span
                    className="breadcrumb-part"
                    onClick={() => onNavigate(arr.slice(0, idx + 1).join('/') + '/')}
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
            <button className="btn btn-outline" onClick={onGoBack}>
              <ArrowLeft size={16} /> 상위 폴더
            </button>
          )}
          <button className="btn btn-outline" onClick={onShowCreateFolder}>
            <FolderPlus size={16} /> 폴더
          </button>
          <button className="btn btn-primary" onClick={onShowUpload}>
            <Upload size={16} /> 업로드
          </button>
        </div>
      </div>

      <div className="objects-list">
        {loading ? (
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
                  className={`${obj.is_folder ? 'folder-row' : ''} ${obj.isParentDir ? 'parent-dir-row' : ''}`}
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
                            onClick={() => onShowDetail(obj)}
                            title="세부 정보"
                          >
                            <Info size={14} />
                          </button>
                          <button
                            className="btn-icon"
                            onClick={() => onDownload(obj.name)}
                            title="다운로드"
                          >
                            <Download size={14} />
                          </button>
                          <button
                            className="btn-icon danger"
                            onClick={() => onDelete(obj.name, obj.is_folder)}
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
  );
}

export default ObjectsPanel;
