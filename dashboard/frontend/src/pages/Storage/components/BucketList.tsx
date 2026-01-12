import { Archive, File, HardDrive, Settings, Trash2, Folder } from 'lucide-react';
import type { Bucket } from '@/types';

interface BucketListProps {
  buckets: Bucket[];
  selectedBucket: string | null;
  onSelectBucket: (name: string) => void;
  onSettings: (name: string) => void;
  onDelete: (name: string, hasObjects: boolean) => void;
}

export function BucketList({
  buckets,
  selectedBucket,
  onSelectBucket,
  onSettings,
  onDelete
}: BucketListProps) {
  if (buckets.length === 0) {
    return (
      <div className="empty-state">
        <Folder size={32} color="var(--color-text-muted)" />
        <p>버킷이 없습니다</p>
      </div>
    );
  }

  return (
    <div className="bucket-list">
      {buckets.map((bucket) => (
        <div
          key={bucket.name}
          className={`bucket-item ${selectedBucket === bucket.name ? 'selected' : ''}`}
          onClick={() => onSelectBucket(bucket.name)}
        >
          <div className="bucket-icon">
            <Archive size={20} />
          </div>
          <div className="bucket-details">
            <div className="bucket-name-row">
              <span className="bucket-name">{bucket.name}</span>
              <span className="bucket-type-badge">S3 호환</span>
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
          <div className="bucket-actions">
            <button
              className="btn-icon bucket-settings"
              onClick={(e) => {
                e.stopPropagation();
                onSettings(bucket.name);
              }}
              title="버킷 설정"
            >
              <Settings size={14} />
            </button>
            <button
              className="btn-icon danger bucket-delete"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(bucket.name, bucket.object_count > 0);
              }}
              title="버킷 삭제"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default BucketList;
