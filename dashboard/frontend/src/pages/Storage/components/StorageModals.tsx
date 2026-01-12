import { X, AlertCircle, Upload } from 'lucide-react';
import type { DeleteConfirm } from '@/types';

interface CreateBucketModalProps {
  isOpen: boolean;
  newBucketName: string;
  actionLoading: boolean;
  onClose: () => void;
  onChange: (name: string) => void;
  onCreate: () => void;
}

export function CreateBucketModal({
  isOpen,
  newBucketName,
  actionLoading,
  onClose,
  onChange,
  onCreate
}: CreateBucketModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>버킷 생성</h3>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <label>버킷 이름</label>
          <input
            type="text"
            value={newBucketName}
            onChange={(e) => onChange(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
            placeholder="my-bucket"
            autoFocus
          />
          <p className="hint">영문 소문자, 숫자, 하이픈만 사용 가능 (3자 이상)</p>
        </div>
        <div className="modal-footer">
          <button className="btn btn-outline" onClick={onClose}>취소</button>
          <button
            className="btn btn-primary"
            onClick={onCreate}
            disabled={newBucketName.length < 3 || actionLoading}
          >
            {actionLoading ? '생성 중...' : '생성'}
          </button>
        </div>
      </div>
    </div>
  );
}

interface CreateFolderModalProps {
  isOpen: boolean;
  newFolderName: string;
  actionLoading: boolean;
  onClose: () => void;
  onChange: (name: string) => void;
  onCreate: () => void;
}

export function CreateFolderModal({
  isOpen,
  newFolderName,
  actionLoading,
  onClose,
  onChange,
  onCreate
}: CreateFolderModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>폴더 생성</h3>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <label>폴더 이름</label>
          <input
            type="text"
            value={newFolderName}
            onChange={(e) => onChange(e.target.value)}
            placeholder="new-folder"
            autoFocus
          />
        </div>
        <div className="modal-footer">
          <button className="btn btn-outline" onClick={onClose}>취소</button>
          <button
            className="btn btn-primary"
            onClick={onCreate}
            disabled={!newFolderName.trim() || actionLoading}
          >
            {actionLoading ? '생성 중...' : '생성'}
          </button>
        </div>
      </div>
    </div>
  );
}

interface UploadModalProps {
  isOpen: boolean;
  actionLoading: boolean;
  onClose: () => void;
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function UploadModal({
  isOpen,
  actionLoading,
  onClose,
  onUpload
}: UploadModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>파일 업로드</h3>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <label className="upload-zone" htmlFor="file-upload-input">
            <Upload size={48} color="var(--color-text-muted)" />
            <p>클릭하여 파일 선택</p>
            <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 8 }}>
              또는 파일을 여기에 드래그하세요
            </p>
            <input
              id="file-upload-input"
              type="file"
              onChange={onUpload}
              disabled={actionLoading}
              style={{ display: 'none' }}
            />
          </label>
          {actionLoading && <p className="uploading">업로드 중...</p>}
        </div>
      </div>
    </div>
  );
}

interface DeleteConfirmModalProps {
  deleteConfirm: DeleteConfirm | null;
  actionLoading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function DeleteConfirmModal({
  deleteConfirm,
  actionLoading,
  onClose,
  onConfirm
}: DeleteConfirmModalProps) {
  if (!deleteConfirm) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-danger" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>삭제 확인</h3>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <AlertCircle size={48} color="var(--color-accent-red)" />
          {deleteConfirm.type === 'bucket' ? (
            <>
              <p>버킷 <strong>'{deleteConfirm.name}'</strong>을(를) 삭제하시겠습니까?</p>
              {deleteConfirm.hasObjects && (
                <p className="warning">이 버킷에는 객체가 있습니다. 강제 삭제하면 모든 객체가 함께 삭제됩니다.</p>
              )}
            </>
          ) : (
            <p>
              {deleteConfirm.isFolder ? '폴더' : '파일'} <strong>'{deleteConfirm.name.split('/').pop()}'</strong>을(를) 삭제하시겠습니까?
              {deleteConfirm.isFolder && <span className="warning"> 하위 모든 파일이 함께 삭제됩니다.</span>}
            </p>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-outline" onClick={onClose}>취소</button>
          <button
            className="btn btn-danger"
            onClick={onConfirm}
            disabled={actionLoading}
          >
            {actionLoading ? '삭제 중...' : '삭제'}
          </button>
        </div>
      </div>
    </div>
  );
}
