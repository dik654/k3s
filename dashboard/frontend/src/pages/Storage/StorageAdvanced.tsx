import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  Shield,
  GitBranch,
  Link,
  Tag,
  Clock,
  Save,
  Trash2,
  Plus,
  X,
  Copy,
  CheckCircle,
  AlertCircle,
  Settings,
  BarChart3,
  FileText,
  Loader2,
  Lock,
  Users,
  UserPlus,
  UserMinus,
  Key,
  ToggleLeft,
  ToggleRight,
  HardDrive,
  Camera,
  RotateCcw,
  Database,
  Expand,
  RefreshCw
} from 'lucide-react';

const API_BASE = '/api';

// TypeScript Interfaces
interface PolicyTemplate {
  name: string;
  description: string;
  policy: Record<string, unknown> | null;
}

interface VersioningState {
  status: 'Enabled' | 'Suspended' | null;
}

interface PresignedUrlResult {
  url: string;
  expires_in: string;
  method: string;
}

interface LifecycleRule {
  rule_id: string;
  prefix?: string;
  enabled: boolean;
  expiration_days?: number;
  noncurrent_expiration_days?: number;
}

interface LifecycleTemplate {
  name: string;
  description: string;
  rule: Omit<LifecycleRule, 'rule_id'>;
}

interface BucketStatsData {
  total_objects: number;
  total_folders: number;
  total_size_human: string;
  versioning_enabled: boolean;
  file_types: Record<string, number>;
  size_distribution: Record<string, number>;
}

interface ObjectLockConfig {
  enabled: boolean;
  mode?: 'GOVERNANCE' | 'COMPLIANCE';
  duration?: number;
  duration_unit?: 'DAYS' | 'YEARS';
}

interface IAMUser {
  accessKey?: string;
  access_key?: string;
  policyName?: string;
  policy?: string;
  userStatus?: string;
  status?: string;
}

interface BucketUser {
  user: string;
  access: 'read' | 'write' | 'admin';
  quota_bytes?: number;
  quota_human?: string;
}

interface BucketQuota {
  quota_bytes?: number;
  quota_human?: string;
  used_human?: string;
}

interface LonghornStatus {
  installed: boolean;
  total_storage?: string;
  used_storage?: string;
  usage_percent?: number;
  volume_count?: number;
}

interface LonghornVolume {
  name: string;
  size_human: string;
  state: string;
  pvc_name?: string;
}

interface LonghornSnapshot {
  name: string;
  created: string;
  size_human: string;
}

interface ComponentProps {
  bucketName?: string;
  objectName?: string;
  showToast: (msg: string, type?: string) => void;
  onClose?: () => void;
  selectedObject?: string;
}

// 버킷 정책 관리 컴포넌트
export const BucketPolicyManager = ({ bucketName, showToast }: ComponentProps) => {
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const [templates, setTemplates] = useState<PolicyTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [policyJson, setPolicyJson] = useState('');
  const initialLoadDone = useRef(false);

  const fetchPolicy = useCallback(async () => {
    if (!bucketName) return;
    try {
      const [policyRes, templatesRes] = await Promise.all([
        axios.get(`${API_BASE}/storage/buckets/${bucketName}/policy`),
        axios.get(`${API_BASE}/storage/policy-templates`)
      ]);
      setPolicy(policyRes.data.policy);
      setPolicyJson(policyRes.data.policy ? JSON.stringify(policyRes.data.policy, null, 2) : '');
      setTemplates(templatesRes.data.templates || []);
    } catch {
      showToast('정책 조회 실패', 'error');
    } finally {
      setLoading(false);
      initialLoadDone.current = true;
    }
  }, [bucketName, showToast]);

  useEffect(() => {
    initialLoadDone.current = false;
    setLoading(true);
    fetchPolicy();
  }, [bucketName, fetchPolicy]);

  const handleApplyTemplate = async (template: PolicyTemplate) => {
    if (!bucketName) return;
    if (!template.policy) {
      try {
        await axios.delete(`${API_BASE}/storage/buckets/${bucketName}/policy`);
        showToast('버킷이 비공개로 설정되었습니다');
        fetchPolicy();
      } catch {
        showToast('정책 삭제 실패', 'error');
      }
      return;
    }

    const policyWithBucket = JSON.parse(
      JSON.stringify(template.policy).replace(/BUCKET_NAME/g, bucketName)
    );

    try {
      await axios.put(`${API_BASE}/storage/buckets/${bucketName}/policy`, {
        policy: policyWithBucket
      });
      showToast(`'${template.name}' 정책이 적용되었습니다`);
      fetchPolicy();
    } catch {
      showToast('정책 적용 실패', 'error');
    }
  };

  const handleSavePolicy = async () => {
    if (!bucketName) return;
    try {
      const parsedPolicy = JSON.parse(policyJson);
      await axios.put(`${API_BASE}/storage/buckets/${bucketName}/policy`, {
        policy: parsedPolicy
      });
      showToast('정책이 저장되었습니다');
      setEditing(false);
      fetchPolicy();
    } catch (error) {
      if (error instanceof SyntaxError) {
        showToast('올바른 JSON 형식이 아닙니다', 'error');
      } else {
        showToast('정책 저장 실패', 'error');
      }
    }
  };

  if (loading && !initialLoadDone.current) {
    return (
      <div className="loading-container">
        <Loader2 className="spin" size={24} />
        <p>정책 정보 로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="advanced-panel policy-panel">
      <div className="panel-section">
        <h4><Shield size={16} /> 정책 템플릿</h4>
        <div className="template-grid">
          {templates.map((template) => (
            <div
              key={template.name}
              className={`template-card ${!template.policy ? 'private' : ''}`}
              onClick={() => handleApplyTemplate(template)}
            >
              <div className="template-name">{template.name}</div>
              <div className="template-desc">{template.description}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel-section">
        <div className="section-header">
          <h4><FileText size={16} /> 현재 정책</h4>
          <button
            className={`btn btn-sm ${editing ? 'btn-primary' : ''}`}
            onClick={() => setEditing(!editing)}
          >
            {editing ? '취소' : '편집'}
          </button>
        </div>

        {policy ? (
          editing ? (
            <div className="policy-editor">
              <textarea
                value={policyJson}
                onChange={(e) => setPolicyJson(e.target.value)}
                className="code-editor"
                rows={15}
              />
              <div className="editor-actions">
                <button className="btn btn-primary" onClick={handleSavePolicy}>
                  <Save size={14} /> 저장
                </button>
              </div>
            </div>
          ) : (
            <pre className="policy-view">
              {JSON.stringify(policy, null, 2)}
            </pre>
          )
        ) : (
          <div className="empty-state">
            <Shield size={32} />
            <p>정책이 설정되지 않음 (비공개)</p>
          </div>
        )}
      </div>
    </div>
  );
};

// 버전 관리 컴포넌트
export const VersioningManager = ({ bucketName, showToast }: ComponentProps) => {
  const [versioning, setVersioning] = useState<VersioningState | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const initialLoadDone = useRef(false);

  const fetchVersioning = useCallback(async () => {
    if (!bucketName) return;
    try {
      const res = await axios.get(`${API_BASE}/storage/buckets/${bucketName}/versioning`);
      setVersioning(res.data.versioning);
    } catch {
      if (!initialLoadDone.current) {
        showToast('버전 관리 상태 조회 실패', 'error');
      }
    } finally {
      setLoading(false);
      initialLoadDone.current = true;
    }
  }, [bucketName, showToast]);

  useEffect(() => {
    initialLoadDone.current = false;
    setLoading(true);
    fetchVersioning();
  }, [bucketName, fetchVersioning]);

  const handleToggleVersioning = async () => {
    if (!bucketName) return;
    try {
      setUpdating(true);
      const newStatus = versioning?.status !== 'Enabled';
      await axios.put(`${API_BASE}/storage/buckets/${bucketName}/versioning`, {
        enabled: newStatus
      });
      showToast(`버전 관리가 ${newStatus ? '활성화' : '비활성화'}되었습니다`);
      fetchVersioning();
    } catch {
      showToast('버전 관리 설정 실패', 'error');
    } finally {
      setUpdating(false);
    }
  };

  if (loading && !initialLoadDone.current) {
    return (
      <div className="loading-container">
        <Loader2 className="spin" size={24} />
        <p>버전 관리 정보 로딩 중...</p>
      </div>
    );
  }

  const isEnabled = versioning?.status === 'Enabled';

  return (
    <div className="advanced-panel versioning-panel">
      <div className="versioning-status">
        <div className="status-info">
          <GitBranch size={32} className={isEnabled ? 'enabled' : 'disabled'} />
          <div>
            <h4>객체 버전 관리</h4>
            <p className={`status-text ${isEnabled ? 'enabled' : 'disabled'}`}>
              {isEnabled ? '활성화됨' : '비활성화됨'}
            </p>
          </div>
        </div>
        <button
          className={`btn ${isEnabled ? 'btn-danger' : 'btn-primary'}`}
          onClick={handleToggleVersioning}
          disabled={updating}
        >
          {updating ? <Loader2 className="spin" size={14} /> : null}
          {isEnabled ? '비활성화' : '활성화'}
        </button>
      </div>

      <div className="versioning-info">
        <div className="info-card">
          <CheckCircle size={20} className="success" />
          <div>
            <strong>버전 관리 활성화 시</strong>
            <ul>
              <li>객체 수정/삭제 시 이전 버전 보존</li>
              <li>실수로 삭제한 파일 복구 가능</li>
              <li>변경 이력 추적 가능</li>
            </ul>
          </div>
        </div>
        <div className="info-card warning">
          <AlertCircle size={20} className="warning" />
          <div>
            <strong>주의사항</strong>
            <ul>
              <li>스토리지 사용량 증가</li>
              <li>한번 활성화하면 완전 비활성화 불가 (Suspended만 가능)</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

// Presigned URL 생성 컴포넌트
export const PresignedUrlGenerator = ({ bucketName, objectName, showToast }: ComponentProps) => {
  const [url, setUrl] = useState<PresignedUrlResult | null>(null);
  const [method, setMethod] = useState('GET');
  const [expiresHours, setExpiresHours] = useState(1);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    if (!bucketName || !objectName) return;
    try {
      setLoading(true);
      const res = await axios.post(`${API_BASE}/storage/buckets/${bucketName}/presigned-url`, {
        object_name: objectName,
        expires_hours: expiresHours,
        method: method
      });
      setUrl(res.data);
      showToast('Presigned URL이 생성되었습니다');
    } catch {
      showToast('URL 생성 실패', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (url) {
      navigator.clipboard.writeText(url.url);
      setCopied(true);
      showToast('URL이 클립보드에 복사되었습니다');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="advanced-panel presigned-panel">
      <h4><Link size={16} /> Presigned URL 생성</h4>

      <div className="presigned-form">
        <div className="form-row">
          <label>대상 객체</label>
          <input type="text" value={objectName || '파일을 선택하세요'} disabled />
        </div>

        <div className="form-row">
          <label>작업 유형</label>
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="GET">다운로드 (GET)</option>
            <option value="PUT">업로드 (PUT)</option>
          </select>
        </div>

        <div className="form-row">
          <label>유효 시간</label>
          <select value={expiresHours} onChange={(e) => setExpiresHours(Number(e.target.value))}>
            <option value={1}>1시간</option>
            <option value={6}>6시간</option>
            <option value={12}>12시간</option>
            <option value={24}>24시간</option>
            <option value={48}>48시간</option>
            <option value={168}>7일</option>
          </select>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={!objectName || loading}
        >
          {loading ? <Loader2 className="spin" size={14} /> : <Link size={14} />}
          URL 생성
        </button>
      </div>

      {url && (
        <div className="presigned-result">
          <div className="url-display">
            <code>{url.url}</code>
            <button className="btn-icon" onClick={handleCopy}>
              {copied ? <CheckCircle size={16} className="success" /> : <Copy size={16} />}
            </button>
          </div>
          <div className="url-info">
            <span>유효기간: {url.expires_in}</span>
            <span>방식: {url.method}</span>
          </div>
        </div>
      )}
    </div>
  );
};

// 객체 태그 관리 컴포넌트
export const ObjectTagsManager = ({ bucketName, objectName, showToast, onClose }: ComponentProps) => {
  const [tags, setTags] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchTags = useCallback(async () => {
    if (!objectName || !bucketName) return;
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/storage/buckets/${bucketName}/objects/${encodeURIComponent(objectName)}/tags`);
      setTags(res.data.tags || {});
    } catch {
      setTags({});
    } finally {
      setLoading(false);
    }
  }, [bucketName, objectName]);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  const handleAddTag = () => {
    if (newKey.trim() && newValue.trim()) {
      setTags({ ...tags, [newKey.trim()]: newValue.trim() });
      setNewKey('');
      setNewValue('');
    }
  };

  const handleRemoveTag = (key: string) => {
    const newTags = { ...tags };
    delete newTags[key];
    setTags(newTags);
  };

  const handleSave = async () => {
    if (!bucketName || !objectName) return;
    try {
      setSaving(true);
      if (Object.keys(tags).length === 0) {
        await axios.delete(`${API_BASE}/storage/buckets/${bucketName}/objects/${encodeURIComponent(objectName)}/tags`);
      } else {
        await axios.put(`${API_BASE}/storage/buckets/${bucketName}/objects/${encodeURIComponent(objectName)}/tags`, {
          tags: tags
        });
      }
      showToast('태그가 저장되었습니다');
      if (onClose) onClose();
    } catch {
      showToast('태그 저장 실패', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <Loader2 className="spin" size={24} />
      </div>
    );
  }

  return (
    <div className="advanced-panel tags-panel">
      <div className="tags-header">
        <h4><Tag size={16} /> 객체 태그</h4>
        <span className="object-name">{objectName}</span>
      </div>

      <div className="tags-list">
        {Object.entries(tags).map(([key, value]) => (
          <div key={key} className="tag-item">
            <span className="tag-key">{key}</span>
            <span className="tag-value">{value}</span>
            <button className="btn-icon danger" onClick={() => handleRemoveTag(key)}>
              <X size={14} />
            </button>
          </div>
        ))}

        {Object.keys(tags).length === 0 && (
          <div className="empty-state small">
            <Tag size={24} />
            <p>태그가 없습니다</p>
          </div>
        )}
      </div>

      <div className="add-tag-form">
        <input
          type="text"
          placeholder="키"
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
        />
        <input
          type="text"
          placeholder="값"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
        />
        <button className="btn btn-secondary" onClick={handleAddTag}>
          <Plus size={14} />
        </button>
      </div>

      <div className="panel-actions">
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="spin" size={14} /> : <Save size={14} />}
          저장
        </button>
      </div>
    </div>
  );
};

// 생명주기 규칙 관리 컴포넌트
export const LifecycleManager = ({ bucketName, showToast }: ComponentProps) => {
  const [rules, setRules] = useState<LifecycleRule[]>([]);
  const [templates, setTemplates] = useState<LifecycleTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddRule, setShowAddRule] = useState(false);
  const [newRule, setNewRule] = useState<LifecycleRule>({
    rule_id: '',
    prefix: '',
    enabled: true,
    expiration_days: 30
  });
  const initialLoadDone = useRef(false);

  const fetchLifecycle = useCallback(async () => {
    if (!bucketName) return;
    try {
      const [rulesRes, templatesRes] = await Promise.all([
        axios.get(`${API_BASE}/storage/buckets/${bucketName}/lifecycle`),
        axios.get(`${API_BASE}/storage/lifecycle-templates`)
      ]);
      setRules(rulesRes.data.rules || []);
      setTemplates(templatesRes.data.templates || []);
    } catch {
      if (!initialLoadDone.current) {
        showToast('생명주기 규칙 조회 실패', 'error');
      }
    } finally {
      setLoading(false);
      initialLoadDone.current = true;
    }
  }, [bucketName, showToast]);

  useEffect(() => {
    initialLoadDone.current = false;
    setLoading(true);
    fetchLifecycle();
  }, [bucketName, fetchLifecycle]);

  const handleApplyTemplate = async (template: LifecycleTemplate) => {
    if (!bucketName) return;
    const rule: LifecycleRule = { ...template.rule, rule_id: `${template.name}-${Date.now()}` };
    try {
      await axios.put(`${API_BASE}/storage/buckets/${bucketName}/lifecycle`, {
        rules: [...rules, rule]
      });
      showToast(`'${template.description}' 규칙이 추가되었습니다`);
      fetchLifecycle();
    } catch {
      showToast('규칙 추가 실패', 'error');
    }
  };

  const handleAddRule = async () => {
    if (!bucketName) return;
    if (!newRule.rule_id.trim()) {
      showToast('규칙 ID를 입력하세요', 'error');
      return;
    }
    try {
      await axios.put(`${API_BASE}/storage/buckets/${bucketName}/lifecycle`, {
        rules: [...rules, newRule]
      });
      showToast('규칙이 추가되었습니다');
      setShowAddRule(false);
      setNewRule({ rule_id: '', prefix: '', enabled: true, expiration_days: 30 });
      fetchLifecycle();
    } catch {
      showToast('규칙 추가 실패', 'error');
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!bucketName) return;
    try {
      const updatedRules = rules.filter(r => r.rule_id !== ruleId);
      if (updatedRules.length === 0) {
        await axios.delete(`${API_BASE}/storage/buckets/${bucketName}/lifecycle`);
      } else {
        await axios.put(`${API_BASE}/storage/buckets/${bucketName}/lifecycle`, {
          rules: updatedRules
        });
      }
      showToast('규칙이 삭제되었습니다');
      fetchLifecycle();
    } catch {
      showToast('규칙 삭제 실패', 'error');
    }
  };

  if (loading && !initialLoadDone.current) {
    return (
      <div className="loading-container">
        <Loader2 className="spin" size={24} />
        <p>생명주기 규칙 로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="advanced-panel lifecycle-panel">
      <div className="panel-section">
        <h4><Clock size={16} /> 규칙 템플릿</h4>
        <div className="template-grid compact">
          {templates.map((template) => (
            <div
              key={template.name}
              className="template-card small"
              onClick={() => handleApplyTemplate(template)}
            >
              <div className="template-name">{template.description}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel-section">
        <div className="section-header">
          <h4>현재 규칙 ({rules.length})</h4>
          <button className="btn btn-sm btn-primary" onClick={() => setShowAddRule(true)}>
            <Plus size={14} /> 추가
          </button>
        </div>

        {rules.length === 0 ? (
          <div className="empty-state">
            <Clock size={32} />
            <p>생명주기 규칙이 없습니다</p>
          </div>
        ) : (
          <div className="rules-list">
            {rules.map((rule) => (
              <div key={rule.rule_id} className={`rule-item ${rule.enabled ? '' : 'disabled'}`}>
                <div className="rule-info">
                  <div className="rule-id">{rule.rule_id}</div>
                  <div className="rule-details">
                    {rule.prefix && <span>접두사: {rule.prefix}</span>}
                    {rule.expiration_days && <span>{rule.expiration_days}일 후 삭제</span>}
                    {rule.noncurrent_expiration_days && <span>이전 버전 {rule.noncurrent_expiration_days}일 후 삭제</span>}
                  </div>
                </div>
                <div className="rule-actions">
                  <span className={`status-badge ${rule.enabled ? 'running' : 'stopped'}`}>
                    {rule.enabled ? '활성' : '비활성'}
                  </span>
                  <button className="btn-icon danger" onClick={() => handleDeleteRule(rule.rule_id)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showAddRule && (
        <div className="modal-overlay" onClick={() => setShowAddRule(false)}>
          <div className="modal-content small" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>생명주기 규칙 추가</h3>
              <button className="btn-icon" onClick={() => setShowAddRule(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>규칙 ID</label>
                <input
                  type="text"
                  value={newRule.rule_id}
                  onChange={(e) => setNewRule({ ...newRule, rule_id: e.target.value })}
                  placeholder="my-rule-1"
                />
              </div>
              <div className="form-group">
                <label>접두사 (선택)</label>
                <input
                  type="text"
                  value={newRule.prefix || ''}
                  onChange={(e) => setNewRule({ ...newRule, prefix: e.target.value })}
                  placeholder="logs/"
                />
              </div>
              <div className="form-group">
                <label>만료 일수</label>
                <input
                  type="number"
                  value={newRule.expiration_days || 30}
                  onChange={(e) => setNewRule({ ...newRule, expiration_days: Number(e.target.value) })}
                  min={1}
                />
              </div>
              <div className="form-group checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={newRule.enabled}
                    onChange={(e) => setNewRule({ ...newRule, enabled: e.target.checked })}
                  />
                  활성화
                </label>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn" onClick={() => setShowAddRule(false)}>취소</button>
              <button className="btn btn-primary" onClick={handleAddRule}>추가</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// 버킷 통계 컴포넌트
export const BucketStats = ({ bucketName, showToast }: ComponentProps) => {
  const [stats, setStats] = useState<BucketStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const initialLoadDone = useRef(false);

  const fetchStats = useCallback(async (isBackground = false) => {
    if (!bucketName) return;
    try {
      if (isBackground) {
        setIsRefreshing(true);
      }
      const res = await axios.get(`${API_BASE}/storage/buckets/${bucketName}/stats`);
      setStats(res.data.stats);
    } catch {
      if (!isBackground) {
        showToast('통계 조회 실패', 'error');
      }
    } finally {
      setLoading(false);
      setIsRefreshing(false);
      initialLoadDone.current = true;
    }
  }, [bucketName, showToast]);

  useEffect(() => {
    initialLoadDone.current = false;
    setLoading(true);
    fetchStats(false);
    const interval = setInterval(() => fetchStats(true), 30000);
    return () => clearInterval(interval);
  }, [bucketName, fetchStats]);

  if (loading && !stats) {
    return (
      <div className="loading-container">
        <Loader2 className="spin" size={24} />
        <p>통계 로딩 중...</p>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="advanced-panel stats-panel">
      <div className="stats-header">
        <h4><BarChart3 size={16} /> 버킷 통계</h4>
        {isRefreshing && <Loader2 className="spin refresh-indicator" size={14} />}
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total_objects}</div>
          <div className="stat-label">총 객체</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_folders}</div>
          <div className="stat-label">폴더</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_size_human}</div>
          <div className="stat-label">총 용량</div>
        </div>
        <div className="stat-card">
          <div className={`stat-value ${stats.versioning_enabled ? 'enabled' : ''}`}>
            {stats.versioning_enabled ? 'ON' : 'OFF'}
          </div>
          <div className="stat-label">버전 관리</div>
        </div>
      </div>

      {Object.keys(stats.file_types).length > 0 && (
        <div className="stats-section">
          <h5>파일 유형 분포</h5>
          <div className="file-types">
            {Object.entries(stats.file_types).map(([ext, count]) => (
              <div key={ext} className="file-type-item">
                <span className="ext">.{ext}</span>
                <span className="count">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="stats-section">
        <h5>크기 분포</h5>
        <div className="size-distribution">
          {Object.entries(stats.size_distribution).map(([range, count]) => (
            <div key={range} className="size-item">
              <span className="range">{range}</span>
              <div className="bar-container">
                <div
                  className="bar"
                  style={{
                    width: `${(count / Math.max(stats.total_objects, 1)) * 100}%`
                  }}
                />
              </div>
              <span className="count">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// 객체 잠금 관리 컴포넌트
export const ObjectLockManager = ({ bucketName, showToast }: ComponentProps) => {
  const [config, setConfig] = useState<ObjectLockConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [mode, setMode] = useState<'GOVERNANCE' | 'COMPLIANCE'>('GOVERNANCE');
  const [duration, setDuration] = useState(30);
  const [durationUnit, setDurationUnit] = useState<'DAYS' | 'YEARS'>('DAYS');

  const fetchConfig = useCallback(async () => {
    if (!bucketName) return;
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/storage/buckets/${bucketName}/object-lock`);
      setConfig(res.data);
      if (res.data.mode) setMode(res.data.mode);
      if (res.data.duration) setDuration(res.data.duration);
      if (res.data.duration_unit) setDurationUnit(res.data.duration_unit);
    } catch {
      showToast('객체 잠금 설정 조회 실패', 'error');
    } finally {
      setLoading(false);
    }
  }, [bucketName, showToast]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSave = async () => {
    if (!bucketName) return;
    try {
      setSaving(true);
      await axios.put(`${API_BASE}/storage/buckets/${bucketName}/object-lock`, {
        mode,
        duration,
        duration_unit: durationUnit
      });
      showToast('객체 잠금 설정이 저장되었습니다');
      fetchConfig();
    } catch (error: any) {
      showToast(error.response?.data?.detail || '설정 저장 실패', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-state">
        <Loader2 className="spin" size={24} />
        <span>로딩 중...</span>
      </div>
    );
  }

  return (
    <div className="object-lock-manager">
      <div className="section-header">
        <Lock size={18} />
        <h4>객체 잠금 (Object Lock)</h4>
      </div>

      {!config?.enabled ? (
        <div className="info-box warning">
          <AlertCircle size={16} />
          <div>
            <strong>객체 잠금 비활성화</strong>
            <p>이 버킷은 객체 잠금이 활성화되지 않았습니다. 버킷 생성 시에만 활성화할 수 있습니다.</p>
          </div>
        </div>
      ) : (
        <>
          <div className="info-box success">
            <CheckCircle size={16} />
            <span>객체 잠금이 활성화되어 있습니다</span>
          </div>

          <div className="form-section">
            <h5>기본 보존 정책</h5>

            <div className="form-group">
              <label>보존 모드</label>
              <select value={mode} onChange={(e) => setMode(e.target.value as 'GOVERNANCE' | 'COMPLIANCE')}>
                <option value="GOVERNANCE">Governance (관리자 삭제 가능)</option>
                <option value="COMPLIANCE">Compliance (삭제 불가)</option>
              </select>
              <span className="hint">
                {mode === 'GOVERNANCE'
                  ? '특별 권한으로 삭제 가능'
                  : '보존 기간 동안 절대 삭제 불가'}
              </span>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>보존 기간</label>
                <input
                  type="number"
                  min="1"
                  value={duration}
                  onChange={(e) => setDuration(parseInt(e.target.value) || 1)}
                />
              </div>
              <div className="form-group">
                <label>단위</label>
                <select value={durationUnit} onChange={(e) => setDurationUnit(e.target.value as 'DAYS' | 'YEARS')}>
                  <option value="DAYS">일</option>
                  <option value="YEARS">년</option>
                </select>
              </div>
            </div>

            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="spin" size={14} /> : <Save size={14} />}
              저장
            </button>
          </div>
        </>
      )}
    </div>
  );
};

// IAM 사용자 관리 컴포넌트
export const IAMManager = ({ showToast }: ComponentProps) => {
  const [users, setUsers] = useState<IAMUser[]>([]);
  const [policies, setPolicies] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddUser, setShowAddUser] = useState(false);
  const [newUser, setNewUser] = useState({ access_key: '', secret_key: '', policy: 'readwrite' });
  const [showSecrets] = useState<Record<string, boolean>>({});

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const [usersRes, policiesRes] = await Promise.all([
        axios.get(`${API_BASE}/storage/iam/users`),
        axios.get(`${API_BASE}/storage/iam/policies`)
      ]);
      setUsers(usersRes.data.users || []);
      setPolicies(policiesRes.data.policies || []);
    } catch {
      try {
        const res = await axios.get(`${API_BASE}/storage/users`);
        setUsers(res.data.users || []);
        setPolicies(['readonly', 'readwrite', 'writeonly', 'consoleAdmin']);
      } catch {
        showToast('사용자 목록 조회 실패', 'error');
      }
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleCreateUser = async () => {
    if (!newUser.access_key || !newUser.secret_key) {
      showToast('Access Key와 Secret Key를 입력하세요', 'error');
      return;
    }
    if (newUser.secret_key.length < 8) {
      showToast('Secret Key는 8자 이상이어야 합니다', 'error');
      return;
    }

    try {
      await axios.post(`${API_BASE}/storage/iam/users`, newUser);
      showToast(`사용자 '${newUser.access_key}'가 생성되었습니다`);
      setShowAddUser(false);
      setNewUser({ access_key: '', secret_key: '', policy: 'readwrite' });
      fetchUsers();
    } catch (error: any) {
      showToast(error.response?.data?.detail || '사용자 생성 실패', 'error');
    }
  };

  const handleDeleteUser = async (accessKey: string) => {
    if (!window.confirm(`'${accessKey}' 사용자를 삭제하시겠습니까?`)) return;

    try {
      await axios.delete(`${API_BASE}/storage/iam/users/${accessKey}`);
      showToast(`사용자 '${accessKey}'가 삭제되었습니다`);
      fetchUsers();
    } catch (error: any) {
      showToast(error.response?.data?.detail || '사용자 삭제 실패', 'error');
    }
  };

  const handleToggleStatus = async (accessKey: string, currentStatus: string) => {
    const enabled = currentStatus !== 'enabled';
    try {
      await axios.put(`${API_BASE}/storage/iam/users/${accessKey}/status?enabled=${enabled}`);
      showToast(`사용자가 ${enabled ? '활성화' : '비활성화'}되었습니다`);
      fetchUsers();
    } catch {
      showToast('상태 변경 실패', 'error');
    }
  };

  const handleChangePolicy = async (accessKey: string, policy: string) => {
    try {
      await axios.put(`${API_BASE}/storage/iam/users/${accessKey}/policy?policy=${policy}`);
      showToast(`정책이 '${policy}'로 변경되었습니다`);
      fetchUsers();
    } catch {
      showToast('정책 변경 실패', 'error');
    }
  };

  if (loading) {
    return (
      <div className="loading-state">
        <Loader2 className="spin" size={24} />
        <span>로딩 중...</span>
      </div>
    );
  }

  return (
    <div className="iam-manager">
      <div className="section-header">
        <Users size={18} />
        <h4>IAM 사용자 관리</h4>
        <button className="btn btn-sm btn-primary" onClick={() => setShowAddUser(true)}>
          <UserPlus size={14} />
          사용자 추가
        </button>
      </div>

      {showAddUser && (
        <div className="add-user-form">
          <h5>새 사용자 생성</h5>
          <div className="form-row">
            <div className="form-group">
              <label>Access Key</label>
              <input
                type="text"
                placeholder="사용자 ID"
                value={newUser.access_key}
                onChange={(e) => setNewUser({ ...newUser, access_key: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Secret Key</label>
              <input
                type="password"
                placeholder="비밀번호 (8자 이상)"
                value={newUser.secret_key}
                onChange={(e) => setNewUser({ ...newUser, secret_key: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>정책</label>
              <select
                value={newUser.policy}
                onChange={(e) => setNewUser({ ...newUser, policy: e.target.value })}
              >
                {policies.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="form-actions">
            <button className="btn btn-primary" onClick={handleCreateUser}>
              <UserPlus size={14} />
              생성
            </button>
            <button className="btn btn-secondary" onClick={() => setShowAddUser(false)}>
              취소
            </button>
          </div>
        </div>
      )}

      <div className="users-list">
        {users.length === 0 ? (
          <div className="empty-state">
            <Users size={32} />
            <p>등록된 사용자가 없습니다</p>
          </div>
        ) : (
          <table className="users-table">
            <thead>
              <tr>
                <th>Access Key</th>
                <th>정책</th>
                <th>상태</th>
                <th>작업</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const accessKey = user.accessKey || user.access_key || '';
                return (
                  <tr key={accessKey}>
                    <td className="access-key">
                      <Key size={14} />
                      <span>{accessKey}</span>
                      {accessKey === 'admin' && (
                        <span className="badge admin">관리자</span>
                      )}
                    </td>
                    <td>
                      <select
                        value={user.policyName || user.policy || 'readwrite'}
                        onChange={(e) => handleChangePolicy(accessKey, e.target.value)}
                        disabled={accessKey === 'admin'}
                      >
                        {policies.map((p) => (
                          <option key={p} value={p}>{p}</option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <button
                        className={`status-toggle ${(user.userStatus || user.status) === 'enabled' ? 'enabled' : 'disabled'}`}
                        onClick={() => handleToggleStatus(accessKey, user.userStatus || user.status || '')}
                        disabled={accessKey === 'admin'}
                      >
                        {(user.userStatus || user.status) === 'enabled' ? (
                          <><ToggleRight size={16} /> 활성</>
                        ) : (
                          <><ToggleLeft size={16} /> 비활성</>
                        )}
                      </button>
                    </td>
                    <td>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => handleDeleteUser(accessKey)}
                        disabled={accessKey === 'admin'}
                        title="삭제"
                      >
                        <UserMinus size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// 버킷별 사용자 접근 권한 관리 컴포넌트
export const BucketUserAccessManager = ({ bucketName, showToast }: ComponentProps) => {
  const [users, setUsers] = useState<BucketUser[]>([]);
  const [allUsers, setAllUsers] = useState<IAMUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddUser, setShowAddUser] = useState(false);
  const [newPermission, setNewPermission] = useState({ user: '', access: 'read', quota_gb: '' });
  const [bucketQuota, setBucketQuota] = useState<BucketQuota | null>(null);
  const [quotaInput, setQuotaInput] = useState('');
  const initialLoadDone = useRef(false);

  const fetchData = useCallback(async () => {
    if (!bucketName) return;
    try {
      const [usersRes, allUsersRes, quotaRes] = await Promise.all([
        axios.get(`${API_BASE}/storage/buckets/${bucketName}/users`).catch(() => ({ data: { users: [] } })),
        axios.get(`${API_BASE}/storage/iam/users`).catch(() => ({ data: { users: [] } })),
        axios.get(`${API_BASE}/storage/buckets/${bucketName}/quota`).catch(() => ({ data: null }))
      ]);
      setUsers(usersRes.data.users || []);
      setAllUsers(allUsersRes.data.users || []);
      setBucketQuota(quotaRes.data);
      if (quotaRes.data?.quota_bytes) {
        setQuotaInput((quotaRes.data.quota_bytes / (1024 * 1024 * 1024)).toFixed(1));
      }
    } catch {
      if (!initialLoadDone.current) {
        showToast('버킷 사용자 정보 조회 실패', 'error');
      }
    } finally {
      setLoading(false);
      initialLoadDone.current = true;
    }
  }, [bucketName, showToast]);

  useEffect(() => {
    initialLoadDone.current = false;
    setLoading(true);
    fetchData();
  }, [bucketName, fetchData]);

  const handleAddUser = async () => {
    if (!bucketName) return;
    if (!newPermission.user) {
      showToast('사용자를 선택하세요', 'error');
      return;
    }

    try {
      await axios.post(`${API_BASE}/storage/buckets/${bucketName}/users`, {
        user: newPermission.user,
        access: newPermission.access,
        quota_gb: newPermission.quota_gb ? parseFloat(newPermission.quota_gb) : null
      });
      showToast(`'${newPermission.user}'에게 접근 권한이 부여되었습니다`);
      setShowAddUser(false);
      setNewPermission({ user: '', access: 'read', quota_gb: '' });
      fetchData();
    } catch (error: any) {
      showToast(error.response?.data?.detail || '권한 부여 실패', 'error');
    }
  };

  const handleRemoveUser = async (user: string) => {
    if (!bucketName) return;
    if (!window.confirm(`'${user}'의 접근 권한을 제거하시겠습니까?`)) return;

    try {
      await axios.delete(`${API_BASE}/storage/buckets/${bucketName}/users/${user}`);
      showToast(`'${user}'의 접근 권한이 제거되었습니다`);
      fetchData();
    } catch (error: any) {
      showToast(error.response?.data?.detail || '권한 제거 실패', 'error');
    }
  };

  const handleUpdateAccess = async (user: string, access: string) => {
    if (!bucketName) return;
    try {
      const existingUser = users.find(u => u.user === user);
      await axios.put(`${API_BASE}/storage/buckets/${bucketName}/users/${user}`, {
        user,
        access,
        quota_gb: existingUser?.quota_bytes ? existingUser.quota_bytes / (1024 * 1024 * 1024) : null
      });
      showToast('접근 권한이 변경되었습니다');
      fetchData();
    } catch {
      showToast('권한 변경 실패', 'error');
    }
  };

  const handleSetQuota = async () => {
    if (!bucketName) return;
    if (!quotaInput) {
      showToast('할당량을 입력하세요', 'error');
      return;
    }

    try {
      await axios.put(`${API_BASE}/storage/buckets/${bucketName}/quota?quota_gb=${parseFloat(quotaInput)}`);
      showToast(`버킷 할당량이 ${quotaInput}GB로 설정되었습니다`);
      fetchData();
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const errMsg = typeof detail === 'string' ? detail : '할당량 설정 실패';
      showToast(errMsg, 'error');
    }
  };

  if (loading && !initialLoadDone.current) {
    return (
      <div className="loading-state">
        <Loader2 className="spin" size={24} />
        <span>로딩 중...</span>
      </div>
    );
  }

  return (
    <div className="bucket-access-manager">
      {/* 버킷 할당량 설정 */}
      <div className="section-header">
        <HardDrive size={18} />
        <h4>버킷 할당량</h4>
      </div>
      <div className="quota-section">
        <div className="quota-info">
          {bucketQuota?.quota_human && (
            <span>현재: {bucketQuota.used_human} / {bucketQuota.quota_human}</span>
          )}
        </div>
        <div className="quota-input-row">
          <input
            type="number"
            step="0.1"
            min="0.1"
            placeholder="할당량 (GB)"
            value={quotaInput}
            onChange={(e) => setQuotaInput(e.target.value)}
          />
          <span className="unit">GB</span>
          <button className="btn btn-sm btn-primary" onClick={handleSetQuota}>
            설정
          </button>
        </div>
      </div>

      {/* 사용자 접근 권한 */}
      <div className="section-header" style={{ marginTop: '20px' }}>
        <Users size={18} />
        <h4>사용자 접근 권한</h4>
        <button className="btn btn-sm btn-primary" onClick={() => setShowAddUser(true)}>
          <UserPlus size={14} />
          추가
        </button>
      </div>

      {showAddUser && (
        <div className="add-user-form">
          <h5>사용자 권한 추가</h5>
          <div className="form-row">
            <div className="form-group">
              <label>사용자</label>
              <select
                value={newPermission.user}
                onChange={(e) => setNewPermission({ ...newPermission, user: e.target.value })}
              >
                <option value="">선택...</option>
                {!allUsers.some(u => (u.accessKey || u.access_key) === 'admin') && (
                  <option value="admin">admin</option>
                )}
                {allUsers.map((u) => (
                  <option key={u.accessKey || u.access_key} value={u.accessKey || u.access_key}>
                    {u.accessKey || u.access_key}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>접근 권한</label>
              <select
                value={newPermission.access}
                onChange={(e) => setNewPermission({ ...newPermission, access: e.target.value })}
              >
                <option value="read">읽기</option>
                <option value="write">읽기/쓰기</option>
                <option value="admin">관리자</option>
              </select>
            </div>
            <div className="form-group">
              <label>개인 할당량 (GB)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                placeholder="무제한"
                value={newPermission.quota_gb}
                onChange={(e) => setNewPermission({ ...newPermission, quota_gb: e.target.value })}
              />
            </div>
          </div>
          <div className="form-actions">
            <button className="btn btn-primary" onClick={handleAddUser}>
              <UserPlus size={14} />
              추가
            </button>
            <button className="btn btn-secondary" onClick={() => setShowAddUser(false)}>
              취소
            </button>
          </div>
        </div>
      )}

      <div className="users-list">
        {users.length === 0 ? (
          <div className="empty-state">
            <Users size={32} />
            <p>이 버킷에 접근 권한이 부여된 사용자가 없습니다</p>
          </div>
        ) : (
          <table className="users-table">
            <thead>
              <tr>
                <th>사용자</th>
                <th>접근 권한</th>
                <th>할당량</th>
                <th>작업</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.user}>
                  <td className="access-key">
                    <Key size={14} />
                    <span>{user.user}</span>
                  </td>
                  <td>
                    <select
                      value={user.access}
                      onChange={(e) => handleUpdateAccess(user.user, e.target.value)}
                    >
                      <option value="read">읽기</option>
                      <option value="write">읽기/쓰기</option>
                      <option value="admin">관리자</option>
                    </select>
                  </td>
                  <td>
                    {user.quota_human || '무제한'}
                  </td>
                  <td>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleRemoveUser(user.user)}
                      title="제거"
                    >
                      <UserMinus size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// Longhorn 볼륨/스냅샷 관리 컴포넌트
export const LonghornManager = ({ showToast }: ComponentProps) => {
  const [volumes, setVolumes] = useState<LonghornVolume[]>([]);
  const [selectedVolume, setSelectedVolume] = useState<LonghornVolume | null>(null);
  const [snapshots, setSnapshots] = useState<LonghornSnapshot[]>([]);
  const [longhornStatus, setLonghornStatus] = useState<LonghornStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [showCreateSnapshot, setShowCreateSnapshot] = useState(false);
  const [newSnapshotName, setNewSnapshotName] = useState('');
  const [expandSize, setExpandSize] = useState('');
  const [showExpand, setShowExpand] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [statusRes, volumesRes] = await Promise.all([
        axios.get(`${API_BASE}/longhorn/status`),
        axios.get(`${API_BASE}/longhorn/volumes`)
      ]);
      setLonghornStatus(statusRes.data);
      setVolumes(volumesRes.data.volumes || []);
    } catch (error: any) {
      if (error.response?.status === 404 || error.response?.status === 503 ||
          error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
        setLonghornStatus({ installed: false });
      } else {
        setLonghornStatus({ installed: false });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSnapshots = useCallback(async (volumeName: string) => {
    if (!volumeName) return;
    try {
      setSnapshotLoading(true);
      const res = await axios.get(`${API_BASE}/longhorn/volumes/${volumeName}/snapshots`);
      setSnapshots(res.data.snapshots || []);
    } catch {
      showToast('스냅샷 목록 조회 실패', 'error');
    } finally {
      setSnapshotLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (selectedVolume) {
      fetchSnapshots(selectedVolume.name);
    }
  }, [selectedVolume, fetchSnapshots]);

  const handleCreateSnapshot = async () => {
    if (!selectedVolume) return;
    if (!newSnapshotName.trim()) {
      showToast('스냅샷 이름을 입력하세요', 'error');
      return;
    }
    try {
      await axios.post(`${API_BASE}/longhorn/volumes/${selectedVolume.name}/snapshots`, {
        name: newSnapshotName
      });
      showToast(`스냅샷 '${newSnapshotName}'이 생성되었습니다`);
      setShowCreateSnapshot(false);
      setNewSnapshotName('');
      fetchSnapshots(selectedVolume.name);
    } catch (error: any) {
      showToast(error.response?.data?.detail || '스냅샷 생성 실패', 'error');
    }
  };

  const handleDeleteSnapshot = async (snapshotName: string) => {
    if (!window.confirm(`'${snapshotName}' 스냅샷을 삭제하시겠습니까?`)) return;
    try {
      await axios.delete(`${API_BASE}/longhorn/snapshots/${snapshotName}`);
      showToast(`스냅샷 '${snapshotName}'이 삭제되었습니다`);
      if (selectedVolume) {
        fetchSnapshots(selectedVolume.name);
      }
    } catch (error: any) {
      showToast(error.response?.data?.detail || '스냅샷 삭제 실패', 'error');
    }
  };

  const handleRestoreSnapshot = async (snapshotName: string) => {
    if (!selectedVolume) return;
    if (!window.confirm(`'${snapshotName}' 스냅샷에서 새 볼륨을 생성하시겠습니까?`)) return;
    try {
      const res = await axios.post(`${API_BASE}/longhorn/volumes/${selectedVolume.name}/restore`, {
        snapshot_name: snapshotName
      });
      showToast(res.data.message);
      fetchData();
    } catch (error: any) {
      showToast(error.response?.data?.detail || '복원 실패', 'error');
    }
  };

  const handleExpandVolume = async () => {
    if (!selectedVolume) return;
    const sizeGb = parseInt(expandSize);
    if (!sizeGb || sizeGb <= 0) {
      showToast('유효한 크기를 입력하세요', 'error');
      return;
    }
    try {
      await axios.put(`${API_BASE}/longhorn/volumes/${selectedVolume.name}/expand?size_gb=${sizeGb}`);
      showToast(`볼륨이 ${sizeGb}GB로 확장 요청되었습니다`);
      setShowExpand(false);
      setExpandSize('');
      fetchData();
    } catch (error: any) {
      showToast(error.response?.data?.detail || '볼륨 확장 실패', 'error');
    }
  };

  if (loading) {
    return (
      <div className="loading-state">
        <Loader2 className="spin" size={24} />
        <span>로딩 중...</span>
      </div>
    );
  }

  if (!longhornStatus?.installed) {
    return (
      <div className="info-box warning">
        <AlertCircle size={16} />
        <div>
          <strong>Longhorn 미설치</strong>
          <p>Longhorn이 설치되어 있지 않습니다. 동적 볼륨 관리를 사용하려면 Longhorn을 설치하세요.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="longhorn-manager">
      {/* Longhorn 상태 요약 */}
      <div className="longhorn-status-summary">
        <div className="status-card">
          <Database size={20} />
          <div>
            <span className="label">전체 스토리지</span>
            <span className="value">{longhornStatus.total_storage}</span>
          </div>
        </div>
        <div className="status-card">
          <HardDrive size={20} />
          <div>
            <span className="label">사용 중</span>
            <span className="value">{longhornStatus.used_storage} ({longhornStatus.usage_percent}%)</span>
          </div>
        </div>
        <div className="status-card">
          <CheckCircle size={20} />
          <div>
            <span className="label">볼륨 수</span>
            <span className="value">{longhornStatus.volume_count}개</span>
          </div>
        </div>
      </div>

      <div className="longhorn-content">
        {/* 볼륨 목록 */}
        <div className="volume-list">
          <div className="section-header">
            <Database size={18} />
            <h4>Longhorn 볼륨</h4>
            <button className="btn-icon" onClick={fetchData} title="새로고침">
              <RefreshCw size={14} />
            </button>
          </div>

          {volumes.length === 0 ? (
            <div className="empty-state">
              <Database size={32} />
              <p>Longhorn 볼륨이 없습니다</p>
            </div>
          ) : (
            <div className="volumes">
              {volumes.map((vol) => (
                <div
                  key={vol.name}
                  className={`volume-item ${selectedVolume?.name === vol.name ? 'selected' : ''}`}
                  onClick={() => setSelectedVolume(vol)}
                >
                  <div className="volume-info">
                    <span className="volume-name">{vol.name}</span>
                    <span className="volume-meta">
                      {vol.size_human} | {vol.state}
                      {vol.pvc_name && ` | PVC: ${vol.pvc_name}`}
                    </span>
                  </div>
                  <span className={`status-badge ${vol.state === 'attached' ? 'success' : 'warning'}`}>
                    {vol.state}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 스냅샷 관리 */}
        <div className="snapshot-panel">
          {selectedVolume ? (
            <>
              <div className="section-header">
                <Camera size={18} />
                <h4>스냅샷 - {selectedVolume.name}</h4>
                <div className="header-actions">
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => setShowExpand(true)}
                    title="볼륨 확장"
                  >
                    <Expand size={14} />
                    확장
                  </button>
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => setShowCreateSnapshot(true)}
                  >
                    <Plus size={14} />
                    스냅샷 생성
                  </button>
                </div>
              </div>

              {/* 볼륨 확장 폼 */}
              {showExpand && (
                <div className="expand-form">
                  <h5>볼륨 확장</h5>
                  <p className="hint">현재 크기: {selectedVolume.size_human}</p>
                  <div className="form-row">
                    <input
                      type="number"
                      placeholder="새 크기 (GB)"
                      value={expandSize}
                      onChange={(e) => setExpandSize(e.target.value)}
                      min="1"
                    />
                    <span className="unit">GB</span>
                    <button className="btn btn-primary" onClick={handleExpandVolume}>
                      확장
                    </button>
                    <button className="btn btn-secondary" onClick={() => setShowExpand(false)}>
                      취소
                    </button>
                  </div>
                </div>
              )}

              {/* 스냅샷 생성 폼 */}
              {showCreateSnapshot && (
                <div className="create-snapshot-form">
                  <h5>새 스냅샷 생성</h5>
                  <div className="form-row">
                    <input
                      type="text"
                      placeholder="스냅샷 이름"
                      value={newSnapshotName}
                      onChange={(e) => setNewSnapshotName(e.target.value)}
                    />
                    <button className="btn btn-primary" onClick={handleCreateSnapshot}>
                      <Camera size={14} />
                      생성
                    </button>
                    <button className="btn btn-secondary" onClick={() => setShowCreateSnapshot(false)}>
                      취소
                    </button>
                  </div>
                </div>
              )}

              {/* 스냅샷 목록 */}
              {snapshotLoading ? (
                <div className="loading-state">
                  <Loader2 className="spin" size={20} />
                  <span>스냅샷 로딩 중...</span>
                </div>
              ) : snapshots.length === 0 ? (
                <div className="empty-state stacked">
                  <Camera size={32} />
                  <p>스냅샷이 없습니다</p>
                  <span className="hint">스냅샷을 생성하여 볼륨 상태를 저장하세요</span>
                </div>
              ) : (
                <div className="snapshots-list">
                  {snapshots.map((snap) => (
                    <div key={snap.name} className="snapshot-item">
                      <div className="snapshot-info">
                        <span className="snapshot-name">{snap.name}</span>
                        <span className="snapshot-meta">
                          {new Date(snap.created).toLocaleString()} | {snap.size_human}
                        </span>
                      </div>
                      <div className="snapshot-actions">
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => handleRestoreSnapshot(snap.name)}
                          title="이 스냅샷에서 새 볼륨 생성"
                        >
                          <RotateCcw size={14} />
                          복원
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDeleteSnapshot(snap.name)}
                          title="스냅샷 삭제"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="empty-state stacked">
              <Camera size={32} />
              <p>볼륨을 선택하세요</p>
              <span className="hint">볼륨을 선택하면 스냅샷을 관리할 수 있습니다</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Tab 정의
interface TabItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
}

// 고급 기능 탭 컴포넌트
export const StorageAdvancedTabs = ({ bucketName, selectedObject, showToast }: ComponentProps) => {
  const [activeTab, setActiveTab] = useState('stats');

  const tabs: TabItem[] = [
    { id: 'stats', label: '통계', icon: BarChart3 },
    { id: 'policy', label: '정책', icon: Shield },
    { id: 'versioning', label: '버전', icon: GitBranch },
    { id: 'lifecycle', label: '생명주기', icon: Clock },
    { id: 'objectlock', label: '잠금', icon: Lock },
    { id: 'access', label: '접근관리', icon: UserPlus },
    { id: 'presigned', label: 'URL 생성', icon: Link },
    { id: 'iam', label: 'IAM', icon: Users },
    { id: 'longhorn', label: '스냅샷', icon: Camera },
  ];

  if (!bucketName) {
    return (
      <div className="advanced-panel">
        <div className="empty-state">
          <Settings size={32} />
          <p>버킷을 선택하세요</p>
        </div>
      </div>
    );
  }

  return (
    <div className="storage-advanced-horizontal">
      <div className="advanced-tabs-header">
        {tabs.map((tab) => {
          const IconComponent = tab.icon;
          return (
            <button
              key={tab.id}
              className={`advanced-tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              title={tab.label}
            >
              <IconComponent size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      <div className="advanced-tab-content">
        {activeTab === 'stats' && (
          <BucketStats bucketName={bucketName} showToast={showToast} />
        )}
        {activeTab === 'policy' && (
          <BucketPolicyManager bucketName={bucketName} showToast={showToast} />
        )}
        {activeTab === 'versioning' && (
          <VersioningManager bucketName={bucketName} showToast={showToast} />
        )}
        {activeTab === 'lifecycle' && (
          <LifecycleManager bucketName={bucketName} showToast={showToast} />
        )}
        {activeTab === 'objectlock' && (
          <ObjectLockManager bucketName={bucketName} showToast={showToast} />
        )}
        {activeTab === 'access' && (
          <BucketUserAccessManager bucketName={bucketName} showToast={showToast} />
        )}
        {activeTab === 'presigned' && (
          <PresignedUrlGenerator
            bucketName={bucketName}
            objectName={selectedObject}
            showToast={showToast}
          />
        )}
        {activeTab === 'iam' && (
          <IAMManager showToast={showToast} />
        )}
        {activeTab === 'longhorn' && (
          <LonghornManager showToast={showToast} />
        )}
      </div>
    </div>
  );
};

export default StorageAdvancedTabs;
