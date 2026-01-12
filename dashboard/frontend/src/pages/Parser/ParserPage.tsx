import { useState, useRef } from 'react';
import axios from 'axios';
import {
  FileText,
  Globe,
  Layers,
  Play,
  Upload,
  GitBranch,
  Copy,
  Sparkles,
  FileType,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

interface ParseResult {
  metadata: {
    filename: string;
    pages?: number;
    char_count: number;
    url?: string;
  };
  chunks: {
    content: string;
    metadata: {
      page?: number;
      chunk_id: number;
    };
  }[];
}

interface CrawlOptions {
  jsRendering: boolean;
  extractImages: boolean;
}

type ChunkingStrategy = 'fixed' | 'sentence' | 'recursive' | 'semantic';

export function ParserPage() {
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [url, setUrl] = useState('');
  const [crawlOptions, setCrawlOptions] = useState<CrawlOptions>({
    jsRendering: false,
    extractImages: false
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE}/parser/parse`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setParseResult(response.data);
    } catch (err) {
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : 'Failed to parse file';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCrawl = async () => {
    if (!url.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${API_BASE}/parser/crawl`, {
        url,
        js_rendering: crawlOptions.jsRendering,
        extract_images: crawlOptions.extractImages
      });

      setParseResult(response.data);
    } catch (err) {
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : 'Failed to crawl URL';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
  };

  const pipelineSteps = [
    { icon: '📄', title: '1. 파싱', desc: '문서 → 텍스트' },
    { icon: '👁️', title: '2. OCR', desc: '이미지 → 텍스트' },
    { icon: '🧹', title: '3. 전처리', desc: '정규화, 클리닝' },
    { icon: '✂️', title: '4. 청킹', desc: '텍스트 분할' },
    { icon: '📊', title: '5. 평가', desc: '품질 검증' }
  ];

  const vlmTriggers = [
    { icon: '📊', label: '복잡한 표' },
    { icon: '📈', label: '차트/그래프' },
    { icon: '∑', label: '수식/LaTeX' },
    { icon: '🖼️', label: '다이어그램' },
    { icon: '📐', label: '복잡한 레이아웃' },
    { icon: '✍️', label: '손글씨 OCR' }
  ];

  const supportedFormats = [
    { icon: '📕', name: 'PDF', lib: 'PyMuPDF + pdfplumber' },
    { icon: '📘', name: 'Word (.docx)', lib: 'python-docx' },
    { icon: '📙', name: 'PowerPoint (.pptx)', lib: 'python-pptx' },
    { icon: '📗', name: 'Excel (.xlsx)', lib: 'openpyxl + pandas' },
    { icon: '📄', name: '한글 (.hwp/.hwpx)', lib: 'olefile + xml' },
    { icon: '🌐', name: 'HTML', lib: 'BeautifulSoup' },
    { icon: '📝', name: 'Markdown', lib: 'markdown-it-py' },
    { icon: '🖼️', name: '이미지 (OCR)', lib: 'pytesseract/EasyOCR' }
  ];

  const crawlFeatures = [
    { title: '⚡ 고성능', items: ['비동기 크롤링으로 빠른 처리', '병렬 처리 지원', '효율적인 메모리 사용'] },
    { title: '🤖 LLM 친화적', items: ['깔끔한 마크다운 출력', '불필요한 요소 자동 제거', '구조화된 데이터 추출'] },
    { title: '🎭 JavaScript 렌더링', items: ['Playwright 기반 헤드리스 브라우저', 'SPA/동적 콘텐츠 지원', '사용자 상호작용 시뮬레이션'] },
    { title: '📊 구조화 추출', items: ['CSS 선택자로 특정 요소 추출', 'JSON 스키마 기반 추출', 'LLM 기반 지능형 추출'] }
  ];

  const chunkingStrategies: { id: ChunkingStrategy; title: string; desc: string; color: string }[] = [
    { id: 'fixed', title: 'Fixed Size', desc: '고정 문자/토큰 수로 분할. 간단하고 예측 가능.', color: '#3b82f6' },
    { id: 'sentence', title: 'Sentence-based', desc: '문장 단위로 분할. 의미 보존에 유리.', color: '#10b981' },
    { id: 'recursive', title: 'Recursive', desc: '계층적 분할. 구조 유지에 효과적.', color: '#f59e0b' },
    { id: 'semantic', title: 'Semantic', desc: '임베딩 기반 의미 단위 분할. 최고 품질.', color: '#a855f7' }
  ];

  const hybridParserCode = `import fitz  # PyMuPDF
import base64
from openai import OpenAI
from dataclasses import dataclass
from typing import List, Optional
import io
from PIL import Image

@dataclass
class PageContent:
    text: str
    images: List[bytes]
    tables: List[dict]
    needs_vlm: bool = False
    vlm_reason: Optional[str] = None

class HybridParser:
    def __init__(self, vlm_client: OpenAI):
        self.client = vlm_client

    def parse_pdf(self, pdf_path: str) -> List[PageContent]:
        """1단계: 빠른 파서로 먼저 처리"""
        doc = fitz.open(pdf_path)
        results = []

        for page_num, page in enumerate(doc):
            content = self._parse_page_fast(page)

            # 품질 검증: VLM 필요 여부 판단
            if self._needs_vlm_processing(content, page):
                content.needs_vlm = True
                content = self._process_with_vlm(page, content)

            results.append(content)

        return results

    def _parse_page_fast(self, page) -> PageContent:
        """PyMuPDF로 빠른 텍스트 추출"""
        text = page.get_text("text")
        images = []
        tables = []

        # 이미지 추출
        for img in page.get_images():
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            images.append(base_image["image"])

        # 테이블 감지 (간단한 휴리스틱)
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if self._looks_like_table(block):
                tables.append(block)

        return PageContent(text=text, images=images, tables=tables)

    def _needs_vlm_processing(self, content: PageContent, page) -> bool:
        """VLM 처리가 필요한지 판단하는 휴리스틱"""
        reasons = []

        # 1. 복잡한 표 감지
        if len(content.tables) > 0:
            for table in content.tables:
                if self._is_complex_table(table):
                    reasons.append("complex_table")
                    break

        # 2. 텍스트 추출 품질 저하 감지
        text_coverage = len(content.text) / max(page.rect.width * page.rect.height * 0.001, 1)
        if text_coverage < 0.3 and len(content.images) > 0:
            reasons.append("low_text_coverage")

        # 3. 수식 패턴 감지
        math_patterns = ['∫', '∑', '√', 'α', 'β', 'γ', '∂', '∞']
        if any(p in content.text for p in math_patterns):
            reasons.append("math_detected")

        if reasons:
            content.vlm_reason = ", ".join(reasons)
            return True
        return False

    def _process_with_vlm(self, page, content: PageContent) -> PageContent:
        """2단계: VLM으로 정밀 처리"""
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        base64_image = base64.b64encode(img_bytes).decode('utf-8')

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a document parser. Extract ALL text content
                    from the image, preserving structure. For tables, output as markdown.
                    For math equations, use LaTeX format."""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this document page:"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }}
                    ]
                }
            ],
            max_tokens=4096
        )

        vlm_text = response.choices[0].message.content
        content.text = self._merge_texts(content.text, vlm_text)
        return content

# 사용 예시
if __name__ == "__main__":
    client = OpenAI(api_key="your-api-key")
    parser = HybridParser(vlm_client=client)
    results = parser.parse_pdf("document.pdf")`;

  const comparisonData = [
    { method: 'Parser Only', speed: '매우 빠름', cost: '무료', accuracy: '중간', useCase: '텍스트 위주 문서', color: '#3b82f6', speedColor: 'var(--accent-green)', costColor: 'var(--accent-green)', accuracyColor: 'var(--accent-yellow)' },
    { method: 'VLM Only', speed: '느림', cost: '높음', accuracy: '높음', useCase: '복잡한 레이아웃', color: '#a855f7', speedColor: 'var(--accent-red)', costColor: 'var(--accent-red)', accuracyColor: 'var(--accent-green)' },
    { method: '하이브리드 (권장)', speed: '빠름*', cost: '최적화', accuracy: '높음', useCase: '모든 문서 유형', color: '#10b981', speedColor: 'var(--accent-green)', costColor: 'var(--accent-yellow)', accuracyColor: 'var(--accent-green)', highlight: true }
  ];

  const ragPipelineSteps = [
    { icon: '📁', label: '문서/URL', color: '' },
    { icon: '⚙️', label: 'Parser', color: 'rgba(59, 130, 246, 0.2)', borderColor: 'rgba(59, 130, 246, 0.3)', textColor: '#3b82f6' },
    { icon: '✂️', label: 'Chunker', color: '' },
    { icon: '🔢', label: 'Embedder', color: 'rgba(16, 185, 129, 0.2)', borderColor: 'rgba(16, 185, 129, 0.3)', textColor: '#10b981' },
    { icon: '💾', label: 'Vector DB', color: 'rgba(168, 85, 247, 0.2)', borderColor: 'rgba(168, 85, 247, 0.3)', textColor: '#a855f7' }
  ];

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Parser & Crawler</h2>
        <span className="section-subtitle">문서 파싱 및 웹 크롤링 통합 도구</span>
      </div>

      {/* Parser Overview */}
      <div className="card">
        <div className="card-header">
          <h3><FileText size={18} /> 문서 파싱 개요</h3>
        </div>
        <div className="parser-overview" style={{ padding: '16px' }}>
          <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
            다양한 문서 형식을 파싱하고 AI/LLM 애플리케이션을 위해 전처리하는 종합 도구입니다.
            RAG 파이프라인에서 문서를 처리하기 위한 핵심 단계들을 제공합니다.
          </p>

          {/* Processing Pipeline */}
          <div className="pipeline-flow" style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '24px' }}>
            {pipelineSteps.map((step, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div className="pipeline-step" style={{ background: 'var(--bg-tertiary)', padding: '12px 20px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', marginBottom: '4px' }}>{step.icon}</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{step.title}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{step.desc}</div>
                </div>
                {idx < pipelineSteps.length - 1 && (
                  <div style={{ color: 'var(--text-secondary)' }}>→</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Parser + VLM 2-Stage Processing */}
      <div className="card" style={{ marginTop: '16px' }}>
        <div className="card-header">
          <h3><Sparkles size={18} /> Parser + VLM 2단계 처리</h3>
        </div>
        <div style={{ padding: '16px' }}>
          <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
            1차로 빠른 파서로 문서를 처리하고, 파서가 놓친 복잡한 요소(표, 차트, 수식, 레이아웃)는
            Vision Language Model(VLM)로 2차 처리하여 정확도를 높이는 하이브리드 방식입니다.
          </p>

          {/* 2-Stage Pipeline Diagram */}
          <div style={{
            background: 'linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary))',
            padding: '24px',
            borderRadius: '12px',
            marginBottom: '20px',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', flexWrap: 'wrap' }}>
              {/* Input */}
              <div style={{ textAlign: 'center', padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                <div style={{ fontSize: '24px', marginBottom: '4px' }}>📄</div>
                <div style={{ fontSize: '12px', fontWeight: '600' }}>문서 입력</div>
                <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>PDF, 이미지 등</div>
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '20px' }}>→</div>

              {/* Stage 1: Fast Parser */}
              <div style={{
                textAlign: 'center',
                padding: '16px 20px',
                background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(59, 130, 246, 0.1))',
                borderRadius: '8px',
                border: '2px solid rgba(59, 130, 246, 0.4)'
              }}>
                <div style={{ fontSize: '24px', marginBottom: '4px' }}>⚡</div>
                <div style={{ fontSize: '13px', fontWeight: '700', color: '#3b82f6' }}>1단계: 빠른 파서</div>
                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '4px' }}>PyMuPDF, pdfplumber</div>
                <div style={{ fontSize: '10px', color: 'var(--accent-green)', marginTop: '2px' }}>~0.1초/페이지</div>
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '20px' }}>→</div>

              {/* Decision Point */}
              <div style={{
                textAlign: 'center',
                padding: '12px 16px',
                background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.1))',
                borderRadius: '50%',
                border: '2px solid rgba(245, 158, 11, 0.4)',
                width: '80px',
                height: '80px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <div style={{ fontSize: '20px' }}>🔍</div>
                <div style={{ fontSize: '10px', fontWeight: '600', color: '#f59e0b' }}>품질 검증</div>
              </div>

              {/* Branch to VLM */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>복잡한 요소 감지시</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '20px' }}>↓</div>

                {/* Stage 2: VLM */}
                <div style={{
                  textAlign: 'center',
                  padding: '16px 20px',
                  background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(168, 85, 247, 0.1))',
                  borderRadius: '8px',
                  border: '2px solid rgba(168, 85, 247, 0.4)'
                }}>
                  <div style={{ fontSize: '24px', marginBottom: '4px' }}>🧠</div>
                  <div style={{ fontSize: '13px', fontWeight: '700', color: '#a855f7' }}>2단계: VLM 처리</div>
                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '4px' }}>GPT-4V, Claude Vision</div>
                  <div style={{ fontSize: '10px', color: 'var(--accent-yellow)', marginTop: '2px' }}>~2-5초/페이지</div>
                </div>
              </div>

              <div style={{ color: 'var(--text-secondary)', fontSize: '20px' }}>→</div>

              {/* Output */}
              <div style={{ textAlign: 'center', padding: '12px 16px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.1))', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                <div style={{ fontSize: '24px', marginBottom: '4px' }}>✅</div>
                <div style={{ fontSize: '12px', fontWeight: '600', color: '#10b981' }}>정확한 텍스트</div>
                <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>구조 보존</div>
              </div>
            </div>
          </div>

          {/* When to use VLM */}
          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ marginBottom: '12px', color: 'var(--text-primary)' }}>🎯 VLM 2차 처리가 필요한 경우</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '10px' }}>
              {vlmTriggers.map((trigger, idx) => (
                <div key={idx} style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '18px' }}>{trigger.icon}</span>
                  <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{trigger.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Implementation Code */}
          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ marginBottom: '12px', color: 'var(--text-primary)' }}>💻 구현 코드 예시</h4>
            <div style={{
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '1px solid var(--border-color)'
            }}>
              <div style={{
                background: 'var(--bg-tertiary)',
                padding: '8px 16px',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)' }}>parser_vlm.py</span>
                <Copy
                  size={14}
                  style={{ color: 'var(--text-secondary)', cursor: 'pointer' }}
                  onClick={() => copyCode(hybridParserCode)}
                />
              </div>
              <pre style={{
                margin: 0,
                padding: '16px',
                fontFamily: 'Monaco, Consolas, monospace',
                fontSize: '12px',
                color: 'var(--text-primary)',
                overflowX: 'auto',
                lineHeight: '1.5',
                maxHeight: '400px'
              }}>
                {hybridParserCode}
              </pre>
            </div>
          </div>

          {/* Comparison Table */}
          <div>
            <h4 style={{ marginBottom: '12px', color: 'var(--text-primary)' }}>📊 처리 방식 비교</h4>
            <div style={{ overflowX: 'auto' }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '13px',
                background: 'var(--bg-secondary)',
                borderRadius: '8px',
                overflow: 'hidden'
              }}>
                <thead>
                  <tr style={{ background: 'var(--bg-tertiary)' }}>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>방식</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>속도</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>비용</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>정확도</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>적합한 경우</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonData.map((row, idx) => (
                    <tr key={idx} style={row.highlight ? { background: 'rgba(16, 185, 129, 0.05)' } : {}}>
                      <td style={{ padding: '12px', borderBottom: idx < comparisonData.length - 1 ? '1px solid var(--border-color)' : 'none' }}>
                        <span style={{ color: row.color, fontWeight: '600' }}>{row.method}</span>
                      </td>
                      <td style={{ padding: '12px', borderBottom: idx < comparisonData.length - 1 ? '1px solid var(--border-color)' : 'none', color: row.speedColor }}>{row.speed}</td>
                      <td style={{ padding: '12px', borderBottom: idx < comparisonData.length - 1 ? '1px solid var(--border-color)' : 'none', color: row.costColor }}>{row.cost}</td>
                      <td style={{ padding: '12px', borderBottom: idx < comparisonData.length - 1 ? '1px solid var(--border-color)' : 'none', color: row.accuracyColor }}>{row.accuracy}</td>
                      <td style={{ padding: '12px', borderBottom: idx < comparisonData.length - 1 ? '1px solid var(--border-color)' : 'none', color: 'var(--text-secondary)' }}>{row.useCase}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
              * 하이브리드 방식은 대부분의 페이지를 빠르게 처리하고, VLM이 필요한 페이지만 추가 처리합니다.
            </p>
          </div>
        </div>
      </div>

      {/* Supported Formats */}
      <div className="card" style={{ marginTop: '16px' }}>
        <div className="card-header">
          <h3><FileType size={18} /> 지원 파일 형식</h3>
        </div>
        <div className="formats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px', padding: '16px' }}>
          {supportedFormats.map((format, idx) => (
            <div key={idx} className="format-item" style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '24px' }}>{format.icon}</span>
              <div>
                <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{format.name}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{format.lib}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Crawl4AI Integration */}
      <div className="card" style={{ marginTop: '16px' }}>
        <div className="card-header">
          <h3><Globe size={18} /> Crawl4AI 웹 크롤링</h3>
        </div>
        <div style={{ padding: '16px' }}>
          <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
            Crawl4AI는 LLM 친화적인 고성능 웹 크롤러입니다. 웹 페이지를 깔끔한 마크다운으로 변환하고,
            JavaScript 렌더링, 동적 콘텐츠 추출을 지원합니다.
          </p>

          <div className="crawl-features" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
            {crawlFeatures.map((feature, idx) => (
              <div key={idx} style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px' }}>
                <h4 style={{ marginBottom: '8px', color: 'var(--accent-primary)' }}>{feature.title}</h4>
                <ul style={{ fontSize: '14px', color: 'var(--text-secondary)', paddingLeft: '20px' }}>
                  {feature.items.map((item, itemIdx) => (
                    <li key={itemIdx}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Chunking Strategies */}
      <div className="card" style={{ marginTop: '16px' }}>
        <div className="card-header">
          <h3><Layers size={18} /> 청킹 전략</h3>
        </div>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '12px' }}>
            {chunkingStrategies.map((strategy, idx) => (
              <div
                key={idx}
                style={{
                  background: `linear-gradient(135deg, ${strategy.color}1a, ${strategy.color}0d)`,
                  padding: '16px',
                  borderRadius: '8px',
                  border: `1px solid ${strategy.color}33`
                }}
              >
                <h4 style={{ color: strategy.color, marginBottom: '8px' }}>{strategy.title}</h4>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{strategy.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Parser Demo */}
      <div className="card" style={{ marginTop: '16px' }}>
        <div className="card-header">
          <h3><Play size={18} /> 파싱 데모</h3>
        </div>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            {/* File Upload Area */}
            <div style={{ flex: '1', minWidth: '300px' }}>
              <div
                style={{
                  border: '2px dashed var(--border-color)',
                  borderRadius: '8px',
                  padding: '32px',
                  textAlign: 'center',
                  background: 'var(--bg-tertiary)'
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={48} style={{ color: 'var(--text-secondary)', marginBottom: '12px' }} />
                <p style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>파일을 드래그하거나 클릭하여 업로드</p>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>PDF, DOCX, PPTX, XLSX, HWP, HTML, MD 지원</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  style={{ display: 'none' }}
                  accept=".pdf,.docx,.pptx,.xlsx,.hwp,.hwpx,.html,.md,.png,.jpg,.jpeg"
                  onChange={handleFileUpload}
                />
                <button
                  style={{
                    marginTop: '16px',
                    padding: '8px 24px',
                    background: 'var(--accent-primary)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer'
                  }}
                >
                  {isLoading ? <Loader2 size={16} className="spinning" /> : '파일 선택'}
                </button>
              </div>
            </div>

            {/* URL Crawl Area */}
            <div style={{ flex: '1', minWidth: '300px' }}>
              <div style={{
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '24px',
                background: 'var(--bg-tertiary)'
              }}>
                <h4 style={{ marginBottom: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Globe size={18} />
                  URL 크롤링
                </h4>
                <input
                  type="text"
                  placeholder="https://example.com/page"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    marginBottom: '12px'
                  }}
                />
                <div style={{ display: 'flex', gap: '16px', marginBottom: '12px' }}>
                  <label style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <input
                      type="checkbox"
                      checked={crawlOptions.jsRendering}
                      onChange={(e) => setCrawlOptions({ ...crawlOptions, jsRendering: e.target.checked })}
                    />
                    JavaScript 렌더링
                  </label>
                  <label style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <input
                      type="checkbox"
                      checked={crawlOptions.extractImages}
                      onChange={(e) => setCrawlOptions({ ...crawlOptions, extractImages: e.target.checked })}
                    />
                    이미지 추출
                  </label>
                </div>
                <button
                  onClick={handleCrawl}
                  disabled={isLoading || !url.trim()}
                  style={{
                    width: '100%',
                    padding: '10px',
                    background: 'var(--accent-secondary)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    opacity: isLoading || !url.trim() ? 0.6 : 1
                  }}
                >
                  {isLoading ? <Loader2 size={16} className="spinning" /> : '크롤링 시작'}
                </button>
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div style={{ marginTop: '16px', padding: '12px 16px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={16} style={{ color: '#ef4444' }} />
              <span style={{ color: '#ef4444', fontSize: '14px' }}>{error}</span>
            </div>
          )}

          {/* Result Preview */}
          <div style={{ marginTop: '20px', border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
            <div style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>파싱 결과</span>
              {parseResult && <CheckCircle size={16} style={{ color: 'var(--accent-green)' }} />}
            </div>
            <div style={{ padding: '16px', background: 'var(--bg-secondary)', minHeight: '150px' }}>
              <pre style={{
                margin: 0,
                fontFamily: 'Monaco, Consolas, monospace',
                fontSize: '13px',
                color: 'var(--text-secondary)',
                whiteSpace: 'pre-wrap'
              }}>
                {parseResult ? JSON.stringify(parseResult, null, 2) : `// 파일을 업로드하거나 URL을 입력하면 결과가 여기에 표시됩니다.

예시 출력:
{
  "metadata": {
    "filename": "document.pdf",
    "pages": 10,
    "char_count": 15234
  },
  "chunks": [
    {
      "content": "첫 번째 청크 내용...",
      "metadata": { "page": 1, "chunk_id": 0 }
    },
    ...
  ]
}`}
              </pre>
            </div>
          </div>
        </div>
      </div>

      {/* Integration with RAG */}
      <div className="card" style={{ marginTop: '16px' }}>
        <div className="card-header">
          <h3><GitBranch size={18} /> RAG 파이프라인 통합</h3>
        </div>
        <div style={{ padding: '16px' }}>
          <div className="rag-pipeline-diagram" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
            {ragPipelineSteps.map((step, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  textAlign: 'center',
                  padding: '12px 16px',
                  background: step.color || 'var(--bg-tertiary)',
                  borderRadius: '8px',
                  border: step.borderColor ? `1px solid ${step.borderColor}` : 'none'
                }}>
                  <div style={{ fontSize: '20px', marginBottom: '4px' }}>{step.icon}</div>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: step.textColor || 'var(--text-primary)' }}>{step.label}</div>
                </div>
                {idx < ragPipelineSteps.length - 1 && (
                  <div style={{ color: 'var(--text-secondary)' }}>→</div>
                )}
              </div>
            ))}
          </div>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', textAlign: 'center' }}>
            Parser로 추출한 텍스트를 청킹하고 임베딩하여 Qdrant Vector DB에 저장합니다.
            이후 RAG 쿼리 시 관련 청크를 검색하여 LLM 컨텍스트로 활용합니다.
          </p>
        </div>
      </div>
    </section>
  );
}

export default ParserPage;
