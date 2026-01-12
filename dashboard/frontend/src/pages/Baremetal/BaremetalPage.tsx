import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Server, HardDrive, Play, Square, RefreshCw, Clock, User, Cpu, MemoryStick,
  Monitor, Zap, AlertTriangle, CheckCircle, XCircle, Loader, ExternalLink,
  Plus, Settings, ArrowRightLeft
} from 'lucide-react';

// Types
interface BMCInfo {
  ip: string;
  username: string;
  vendor: string;
}

interface DiskInfo {
  device: string;
  size_gb: number;
  disk_type: 'rental' | 'owner';
  label: string;
  is_active: boolean;
}

interface NetworkInterface {
  mac: string;
  ip: string | null;
  gateway: string | null;
  is_management: boolean;
}

interface HardwareSpec {
  cpu_cores: number;
  cpu_model: string;
  memory_gb: number;
  gpu_count: number;
  gpu_model: string;
}

interface Hardware {
  id: string;
  name: string;
  status: 'available' | 'rented' | 'provisioning' | 'maintenance' | 'owner_use';
  bmc: BMCInfo;
  spec: HardwareSpec;
  disks: DiskInfo[];
  active_disk: string | null;
  interfaces: NetworkInterface[];
  owner_id: string | null;
  owner_name: string | null;
  current_rental_id: string | null;
  labels: Record<string, string>;
}

interface OSTemplate {
  id: string;
  name: string;
  os_name: string;
  os_version: string;
  description: string;
  for_rental: boolean;
}

interface RentalSession {
  id: string;
  hardware_id: string;
  hardware_name: string;
  renter_name: string;
  renter_email: string;
  os_name: string;
  ssh_ip: string;
  ssh_port: number;
  ssh_user: string;
  ssh_password: string;
  rental_hours: number;
  started_at: string | null;
  expires_at: string | null;
  status: 'requested' | 'provisioning' | 'active' | 'expiring_soon' | 'expired' | 'cleaning' | 'completed';
}

interface RentalStats {
  rentals: { total: number; active: number; provisioning: number; completed: number };
  hardware: { total: number; available: number; rented: number; owner_use: number };
}

// Status colors and labels
const STATUS_CONFIG: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  available: { color: 'var(--accent-green)', label: '대여 가능', icon: <CheckCircle size={14} /> },
  rented: { color: 'var(--accent-blue)', label: '대여 중', icon: <User size={14} /> },
  provisioning: { color: 'var(--accent-yellow)', label: 'OS 설치 중', icon: <Loader size={14} className="spin" /> },
  maintenance: { color: 'var(--accent-orange)', label: '유지보수', icon: <Settings size={14} /> },
  owner_use: { color: 'var(--accent-purple)', label: '소유자 사용', icon: <Monitor size={14} /> },
};

const RENTAL_STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  requested: { color: 'var(--accent-yellow)', label: '요청됨' },
  provisioning: { color: 'var(--accent-blue)', label: 'OS 설치 중' },
  active: { color: 'var(--accent-green)', label: '활성' },
  expiring_soon: { color: 'var(--accent-orange)', label: '곧 만료' },
  expired: { color: 'var(--accent-red)', label: '만료됨' },
  cleaning: { color: 'var(--accent-purple)', label: '정리 중' },
  completed: { color: 'var(--text-muted)', label: '완료' },
};

export function BaremetalPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'hardware' | 'rentals' | 'templates' | 'guide'>('hardware');

  // Data states
  const [hardware, setHardware] = useState<Hardware[]>([]);
  const [rentals, setRentals] = useState<RentalSession[]>([]);
  const [templates, setTemplates] = useState<OSTemplate[]>([]);
  const [stats, setStats] = useState<RentalStats | null>(null);
  const [tinkerbellStatus, setTinkerbellStatus] = useState<{ demo_mode: boolean; message: string } | null>(null);

  // Modal states
  const [showRentalModal, setShowRentalModal] = useState(false);
  const [selectedHardware, setSelectedHardware] = useState<Hardware | null>(null);
  const [rentalForm, setRentalForm] = useState({
    template_id: '',
    rental_hours: 24,
    renter_name: '',
    renter_email: '',
    notes: ''
  });

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [hwRes, rentalsRes, templatesRes, statsRes, statusRes] = await Promise.all([
        axios.get('/api/baremetal/hardware'),
        axios.get('/api/baremetal/rentals'),
        axios.get('/api/baremetal/templates'),
        axios.get('/api/baremetal/rentals/stats/summary'),
        axios.get('/api/baremetal/status'),
      ]);

      setHardware(hwRes.data);
      setRentals(rentalsRes.data);
      setTemplates(templatesRes.data);
      setStats(statsRes.data);
      setTinkerbellStatus(statusRes.data);
    } catch (error) {
      console.error('Failed to fetch baremetal data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleCreateRental = async () => {
    if (!selectedHardware || !rentalForm.template_id || !rentalForm.renter_name) return;

    try {
      await axios.post('/api/baremetal/rentals', {
        hardware_id: selectedHardware.id,
        ...rentalForm
      });
      setShowRentalModal(false);
      setSelectedHardware(null);
      setRentalForm({ template_id: '', rental_hours: 24, renter_name: '', renter_email: '', notes: '' });
      fetchData();
    } catch (error) {
      console.error('Failed to create rental:', error);
    }
  };

  const handleTerminateRental = async (rentalId: string) => {
    if (!confirm('정말로 이 대여를 종료하시겠습니까? 데이터가 삭제됩니다.')) return;

    try {
      await axios.post(`/api/baremetal/rentals/${rentalId}/terminate`);
      fetchData();
    } catch (error) {
      console.error('Failed to terminate rental:', error);
    }
  };

  const handleSwapDisk = async (hardwareId: string, targetType: 'rental' | 'owner') => {
    if (!confirm(`디스크를 ${targetType === 'rental' ? '대여용' : '소유자용'}으로 전환하시겠습니까?`)) return;

    try {
      await axios.post(`/api/baremetal/hardware/${hardwareId}/swap-disk`, {
        hardware_id: hardwareId,
        target_disk: targetType
      });
      fetchData();
    } catch (error) {
      console.error('Failed to swap disk:', error);
    }
  };

  const formatTimeRemaining = (expiresAt: string | null) => {
    if (!expiresAt) return '-';
    const now = new Date();
    const expires = new Date(expiresAt);
    const diff = expires.getTime() - now.getTime();
    if (diff <= 0) return '만료됨';
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}시간 ${minutes}분`;
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Server size={28} />
            베어메탈 프로비저닝
          </h1>
          <p style={{ color: 'var(--text-muted)', marginTop: 4 }}>
            Tinkerbell 기반 베어메탈 서버 관리 및 대여
            {tinkerbellStatus?.demo_mode && (
              <span style={{ marginLeft: 8, padding: '2px 8px', background: 'var(--accent-yellow)', color: '#000', borderRadius: 4, fontSize: 11 }}>
                데모 모드
              </span>
            )}
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={() => fetchData(true)}
          disabled={refreshing}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
          새로고침
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="stats-grid" style={{ marginBottom: 24 }}>
          <div className="stat-card">
            <div className="stat-header">
              <div className="stat-icon" style={{ background: 'var(--accent-blue)' }}>
                <Server size={18} color="white" />
              </div>
              <span className="stat-label">전체 서버</span>
            </div>
            <div className="stat-value">{stats.hardware.total}</div>
          </div>
          <div className="stat-card">
            <div className="stat-header">
              <div className="stat-icon" style={{ background: 'var(--accent-green)' }}>
                <CheckCircle size={18} color="white" />
              </div>
              <span className="stat-label">대여 가능</span>
            </div>
            <div className="stat-value">{stats.hardware.available}</div>
          </div>
          <div className="stat-card">
            <div className="stat-header">
              <div className="stat-icon" style={{ background: 'var(--accent-purple)' }}>
                <User size={18} color="white" />
              </div>
              <span className="stat-label">대여 중</span>
            </div>
            <div className="stat-value">{stats.hardware.rented}</div>
          </div>
          <div className="stat-card">
            <div className="stat-header">
              <div className="stat-icon" style={{ background: 'var(--accent-orange)' }}>
                <Clock size={18} color="white" />
              </div>
              <span className="stat-label">활성 대여</span>
            </div>
            <div className="stat-value">{stats.rentals.active}</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: 20, borderBottom: '1px solid var(--border-color)', display: 'flex', gap: 0 }}>
        {[
          { id: 'hardware', label: '하드웨어', icon: <Server size={16} /> },
          { id: 'rentals', label: '대여 현황', icon: <Clock size={16} /> },
          { id: 'templates', label: 'OS 템플릿', icon: <HardDrive size={16} /> },
          { id: 'guide', label: '사용 가이드', icon: <ExternalLink size={16} /> },
        ].map(tab => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            style={{
              padding: '12px 20px',
              border: 'none',
              background: activeTab === tab.id ? 'var(--bg-secondary)' : 'transparent',
              borderBottom: activeTab === tab.id ? '2px solid var(--accent-blue)' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
              fontWeight: activeTab === tab.id ? 600 : 400,
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Hardware Tab */}
      {activeTab === 'hardware' && (
        <div className="hardware-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 16 }}>
          {hardware.map(hw => (
            <div key={hw.id} className="card" style={{ padding: 20 }}>
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div>
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <Server size={18} />
                    {hw.name}
                  </h3>
                  {hw.owner_name && (
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>소유자: {hw.owner_name}</span>
                  )}
                </div>
                <span style={{
                  display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
                  background: STATUS_CONFIG[hw.status]?.color || 'var(--text-muted)',
                  color: 'white', borderRadius: 12, fontSize: 12
                }}>
                  {STATUS_CONFIG[hw.status]?.icon}
                  {STATUS_CONFIG[hw.status]?.label}
                </span>
              </div>

              {/* Specs */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8, marginBottom: 16, fontSize: 13 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Cpu size={14} style={{ color: 'var(--text-muted)' }} />
                  <span>{hw.spec.cpu_cores} cores</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <MemoryStick size={14} style={{ color: 'var(--text-muted)' }} />
                  <span>{hw.spec.memory_gb} GB</span>
                </div>
                {hw.spec.gpu_count > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, gridColumn: 'span 2' }}>
                    <Zap size={14} style={{ color: 'var(--accent-green)' }} />
                    <span>{hw.spec.gpu_count}x {hw.spec.gpu_model}</span>
                  </div>
                )}
              </div>

              {/* Disks */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>디스크</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {hw.disks.map(disk => (
                    <div key={disk.device} style={{
                      flex: 1, padding: 8, borderRadius: 6,
                      background: disk.is_active ? 'var(--accent-blue)' : 'var(--bg-tertiary)',
                      color: disk.is_active ? 'white' : 'var(--text-primary)',
                      fontSize: 12
                    }}>
                      <div style={{ fontWeight: 500 }}>{disk.disk_type === 'rental' ? '대여용' : '소유자'}</div>
                      <div style={{ opacity: 0.8 }}>{disk.device} ({disk.size_gb}GB)</div>
                      {disk.is_active && <div style={{ marginTop: 4, fontSize: 10 }}>활성</div>}
                    </div>
                  ))}
                </div>
              </div>

              {/* Network */}
              {hw.interfaces[0]?.ip && (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                  IP: <code style={{ background: 'var(--bg-tertiary)', padding: '2px 6px', borderRadius: 4 }}>{hw.interfaces[0].ip}</code>
                </div>
              )}

              {/* Actions */}
              <div style={{ display: 'flex', gap: 8 }}>
                {hw.status === 'available' && (
                  <button
                    className="btn btn-success"
                    style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                    onClick={() => { setSelectedHardware(hw); setShowRentalModal(true); }}
                  >
                    <Play size={14} /> 대여 시작
                  </button>
                )}
                {hw.status === 'owner_use' && (
                  <button
                    className="btn btn-primary"
                    style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                    onClick={() => handleSwapDisk(hw.id, 'rental')}
                  >
                    <ArrowRightLeft size={14} /> 대여 모드로 전환
                  </button>
                )}
                {hw.status === 'available' && (
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleSwapDisk(hw.id, 'owner')}
                  >
                    <Monitor size={14} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Rentals Tab */}
      {activeTab === 'rentals' && (
        <div className="rentals-list">
          {rentals.length === 0 ? (
            <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
              현재 활성 대여가 없습니다.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {rentals.map(rental => (
                <div key={rental.id} className="card" style={{ padding: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                        <h3 style={{ margin: 0 }}>{rental.hardware_name}</h3>
                        <span style={{
                          padding: '3px 10px', borderRadius: 12, fontSize: 11,
                          background: RENTAL_STATUS_CONFIG[rental.status]?.color,
                          color: 'white'
                        }}>
                          {RENTAL_STATUS_CONFIG[rental.status]?.label}
                        </span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, fontSize: 13 }}>
                        <div>
                          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 2 }}>대여자</div>
                          <div>{rental.renter_name}</div>
                        </div>
                        <div>
                          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 2 }}>OS</div>
                          <div>{rental.os_name || '설치 중...'}</div>
                        </div>
                        <div>
                          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 2 }}>남은 시간</div>
                          <div style={{ fontWeight: 500 }}>{formatTimeRemaining(rental.expires_at)}</div>
                        </div>
                      </div>

                      {rental.status === 'active' && rental.ssh_ip && (
                        <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-tertiary)', borderRadius: 8, fontSize: 12 }}>
                          <div style={{ fontWeight: 500, marginBottom: 6 }}>SSH 접속 정보</div>
                          <code>ssh {rental.ssh_user}@{rental.ssh_ip} -p {rental.ssh_port}</code>
                          <div style={{ marginTop: 4, color: 'var(--text-muted)' }}>
                            비밀번호: <code>{rental.ssh_password}</code>
                          </div>
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: 8 }}>
                      {rental.status === 'active' && (
                        <button
                          className="btn btn-danger"
                          onClick={() => handleTerminateRental(rental.id)}
                          style={{ display: 'flex', alignItems: 'center', gap: 4 }}
                        >
                          <Square size={14} /> 종료
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Templates Tab */}
      {activeTab === 'templates' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
          {templates.map(tpl => (
            <div key={tpl.id} className="card" style={{ padding: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <HardDrive size={18} />
                <h3 style={{ margin: 0, fontSize: 15 }}>{tpl.name}</h3>
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>
                {tpl.os_name} {tpl.os_version}
              </div>
              <p style={{ fontSize: 12, margin: 0, color: 'var(--text-secondary)' }}>
                {tpl.description}
              </p>
              {tpl.for_rental && (
                <span style={{
                  marginTop: 8, display: 'inline-block', padding: '2px 8px',
                  background: 'var(--accent-green)', color: 'white', borderRadius: 10, fontSize: 10
                }}>
                  대여용
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Guide Tab */}
      {activeTab === 'guide' && (
        <div className="card" style={{ padding: 24 }}>
          <h2 style={{ marginBottom: 20 }}>베어메탈 렌탈 시스템 사용 가이드</h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* 개요 */}
            <section>
              <h3 style={{ color: 'var(--accent-blue)', marginBottom: 12 }}>1. 시스템 개요</h3>
              <p style={{ lineHeight: 1.8 }}>
                이 시스템은 베어메탈 서버를 <strong>듀얼 디스크 구조</strong>로 운영하여
                서버 소유자가 유휴 시간에 서버를 대여해줄 수 있게 합니다.
              </p>
              <div style={{ background: 'var(--bg-tertiary)', padding: 16, borderRadius: 8, marginTop: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 8 }}>듀얼 디스크 구조</div>
                <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 2 }}>
                  <li><strong>Disk A (대여용)</strong>: 비어있는 디스크에 OS만 설치하여 대여</li>
                  <li><strong>Disk B (소유자용)</strong>: 소유자의 OS와 데이터가 있는 디스크</li>
                </ul>
              </div>
            </section>

            {/* 흐름 */}
            <section>
              <h3 style={{ color: 'var(--accent-blue)', marginBottom: 12 }}>2. 대여 흐름</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                {[
                  { step: 1, title: '대여 요청', desc: '사용자가 서버와 OS 선택' },
                  { step: 2, title: '디스크 스왑', desc: 'Disk A로 부팅 순서 변경' },
                  { step: 3, title: 'OS 설치', desc: 'Tinkerbell이 자동 프로비저닝' },
                  { step: 4, title: '대여 시작', desc: 'SSH 접속 정보 제공' },
                ].map(item => (
                  <div key={item.step} style={{ background: 'var(--bg-secondary)', padding: 16, borderRadius: 8, textAlign: 'center' }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: '50%', background: 'var(--accent-blue)',
                      color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      margin: '0 auto 8px', fontWeight: 600
                    }}>
                      {item.step}
                    </div>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>{item.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{item.desc}</div>
                  </div>
                ))}
              </div>
            </section>

            {/* 대여 종료 */}
            <section>
              <h3 style={{ color: 'var(--accent-blue)', marginBottom: 12 }}>3. 대여 종료 및 정리</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                {[
                  { step: 1, title: '서버 전원 OFF', desc: 'BMC를 통한 안전한 종료' },
                  { step: 2, title: '디스크 초기화', desc: 'Disk A 완전 삭제 (wipefs)' },
                  { step: 3, title: '소유자 복귀', desc: 'Disk B로 부팅 순서 복구' },
                ].map(item => (
                  <div key={item.step} style={{ background: 'var(--bg-secondary)', padding: 16, borderRadius: 8, textAlign: 'center' }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: '50%', background: 'var(--accent-purple)',
                      color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      margin: '0 auto 8px', fontWeight: 600
                    }}>
                      {item.step}
                    </div>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>{item.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{item.desc}</div>
                  </div>
                ))}
              </div>
            </section>

            {/* Tinkerbell 컴포넌트 */}
            <section>
              <h3 style={{ color: 'var(--accent-blue)', marginBottom: 12 }}>4. Tinkerbell 컴포넌트</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-tertiary)' }}>
                    <th style={{ padding: 12, textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>컴포넌트</th>
                    <th style={{ padding: 12, textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>역할</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { name: 'Tink Server', role: '워크플로우 관리 및 API 서버' },
                    { name: 'Boots', role: 'DHCP, TFTP, HTTP 서버 (PXE 부팅)' },
                    { name: 'Hegel', role: '메타데이터 서버 (cloud-init 등)' },
                    { name: 'Rufio', role: 'BMC 컨트롤러 (IPMI/Redfish로 전원 제어)' },
                  ].map(item => (
                    <tr key={item.name}>
                      <td style={{ padding: 12, borderBottom: '1px solid var(--border-color)', fontWeight: 500 }}>{item.name}</td>
                      <td style={{ padding: 12, borderBottom: '1px solid var(--border-color)' }}>{item.role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            {/* 주의사항 */}
            <section>
              <h3 style={{ color: 'var(--accent-orange)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                <AlertTriangle size={18} /> 주의사항
              </h3>
              <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 2 }}>
                <li>대여 종료 시 <strong>Disk A의 모든 데이터가 삭제</strong>됩니다.</li>
                <li>Disk B (소유자 디스크)는 절대 접근하지 않습니다.</li>
                <li>대여 시간이 만료되면 자동으로 정리 프로세스가 시작됩니다.</li>
                <li>BMC 접속 정보가 정확해야 디스크 스왑이 가능합니다.</li>
              </ul>
            </section>
          </div>
        </div>
      )}

      {/* Rental Modal */}
      {showRentalModal && selectedHardware && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000
        }} onClick={() => setShowRentalModal(false)}>
          <div className="card" style={{ width: 480, padding: 24 }} onClick={e => e.stopPropagation()}>
            <h2 style={{ marginBottom: 20 }}>서버 대여 요청</h2>
            <p style={{ marginBottom: 20, color: 'var(--text-muted)' }}>
              <strong>{selectedHardware.name}</strong>에 대한 대여를 요청합니다.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>OS 템플릿</label>
                <select
                  value={rentalForm.template_id}
                  onChange={e => setRentalForm({ ...rentalForm, template_id: e.target.value })}
                  style={{ width: '100%', padding: 10, borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}
                >
                  <option value="">선택하세요</option>
                  {templates.filter(t => t.for_rental).map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>대여 시간</label>
                <select
                  value={rentalForm.rental_hours}
                  onChange={e => setRentalForm({ ...rentalForm, rental_hours: parseInt(e.target.value) })}
                  style={{ width: '100%', padding: 10, borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}
                >
                  {[1, 2, 4, 8, 12, 24, 48, 72, 168].map(h => (
                    <option key={h} value={h}>{h}시간 {h >= 24 ? `(${h/24}일)` : ''}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>대여자 이름 *</label>
                <input
                  type="text"
                  value={rentalForm.renter_name}
                  onChange={e => setRentalForm({ ...rentalForm, renter_name: e.target.value })}
                  style={{ width: '100%', padding: 10, borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}
                  placeholder="이름을 입력하세요"
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>이메일 (선택)</label>
                <input
                  type="email"
                  value={rentalForm.renter_email}
                  onChange={e => setRentalForm({ ...rentalForm, renter_email: e.target.value })}
                  style={{ width: '100%', padding: 10, borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}
                  placeholder="만료 알림용"
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 }}>메모 (선택)</label>
                <textarea
                  value={rentalForm.notes}
                  onChange={e => setRentalForm({ ...rentalForm, notes: e.target.value })}
                  style={{ width: '100%', padding: 10, borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', minHeight: 80 }}
                  placeholder="용도 등"
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1 }}
                onClick={() => setShowRentalModal(false)}
              >
                취소
              </button>
              <button
                className="btn btn-success"
                style={{ flex: 1 }}
                onClick={handleCreateRental}
                disabled={!rentalForm.template_id || !rentalForm.renter_name}
              >
                대여 요청
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default BaremetalPage;
