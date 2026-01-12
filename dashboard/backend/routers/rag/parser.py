"""
Parser API Router
문서 파싱 및 웹 크롤링 기능
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import io
import httpx

router = APIRouter(prefix="/api/parser", tags=["parser"])


class CrawlRequest(BaseModel):
    """크롤링 요청"""
    url: str
    js_rendering: bool = False
    extract_images: bool = False


class ParseResult(BaseModel):
    """파싱 결과"""
    text: str
    metadata: Dict[str, Any]
    pages: Optional[int] = None
    images: Optional[List[str]] = None


@router.post("/parse")
async def parse_document(file: UploadFile = File(...)):
    """
    문서 파싱 (PDF, DOCX, TXT 등)

    PyMuPDF를 사용하여 PDF 파싱
    다른 형식은 기본 텍스트 추출
    """
    try:
        content = await file.read()
        filename = file.filename or "unknown"
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''

        result = {
            "filename": filename,
            "file_type": file_ext,
            "size_bytes": len(content),
            "text": "",
            "metadata": {},
            "pages": None,
            "images": []
        }

        # PDF 파싱
        if file_ext == 'pdf':
            try:
                import fitz  # PyMuPDF

                pdf_document = fitz.open(stream=content, filetype="pdf")
                text_parts = []
                images = []

                for page_num, page in enumerate(pdf_document):
                    # 텍스트 추출
                    text_parts.append(page.get_text())

                    # 이미지 추출 (기본 정보만)
                    image_list = page.get_images()
                    for img_index, img in enumerate(image_list):
                        images.append({
                            "page": page_num + 1,
                            "index": img_index,
                            "xref": img[0]
                        })

                result["text"] = "\n\n".join(text_parts)
                result["pages"] = len(pdf_document)
                result["images"] = images
                result["metadata"] = {
                    "title": pdf_document.metadata.get("title", ""),
                    "author": pdf_document.metadata.get("author", ""),
                    "subject": pdf_document.metadata.get("subject", ""),
                    "creator": pdf_document.metadata.get("creator", ""),
                    "creation_date": pdf_document.metadata.get("creationDate", ""),
                }

                pdf_document.close()

            except ImportError:
                # PyMuPDF가 없으면 기본 처리
                result["text"] = "[PDF 파싱 라이브러리(PyMuPDF)가 설치되지 않았습니다]"
                result["metadata"]["error"] = "PyMuPDF not installed"

        # 텍스트 파일
        elif file_ext in ['txt', 'md', 'csv', 'json', 'xml', 'html']:
            try:
                result["text"] = content.decode('utf-8')
            except UnicodeDecodeError:
                result["text"] = content.decode('latin-1')
            result["pages"] = 1

        # DOCX 파싱
        elif file_ext == 'docx':
            try:
                from docx import Document

                doc = Document(io.BytesIO(content))
                paragraphs = [para.text for para in doc.paragraphs]
                result["text"] = "\n".join(paragraphs)
                result["pages"] = 1  # DOCX는 페이지 정보 제한적
                result["metadata"] = {
                    "core_properties": {
                        "author": doc.core_properties.author or "",
                        "title": doc.core_properties.title or "",
                        "subject": doc.core_properties.subject or "",
                    }
                }
            except ImportError:
                result["text"] = "[DOCX 파싱 라이브러리(python-docx)가 설치되지 않았습니다]"
                result["metadata"]["error"] = "python-docx not installed"

        else:
            # 알 수 없는 형식
            try:
                result["text"] = content.decode('utf-8')
            except:
                result["text"] = f"[지원하지 않는 파일 형식: {file_ext}]"

        # 텍스트 통계 추가
        if result["text"]:
            result["metadata"]["char_count"] = len(result["text"])
            result["metadata"]["word_count"] = len(result["text"].split())
            result["metadata"]["line_count"] = result["text"].count('\n') + 1

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파싱 오류: {str(e)}")


@router.post("/crawl")
async def crawl_url(request: CrawlRequest):
    """
    웹 페이지 크롤링

    URL에서 텍스트 콘텐츠 추출
    js_rendering: JavaScript 렌더링 필요 여부
    extract_images: 이미지 URL 추출 여부
    """
    try:
        url = request.url

        # URL 유효성 검사
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        result = {
            "url": url,
            "text": "",
            "title": "",
            "metadata": {
                "js_rendering": request.js_rendering,
                "extract_images": request.extract_images
            },
            "images": []
        }

        # JavaScript 렌더링이 필요한 경우
        if request.js_rendering:
            # Playwright/Selenium이 필요하지만, 없으면 기본 요청으로 폴백
            result["metadata"]["js_rendering_note"] = "JS 렌더링은 현재 지원되지 않습니다. 기본 HTTP 요청으로 처리됩니다."

        # HTTP 요청
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            html_content = response.text
            result["metadata"]["status_code"] = response.status_code
            result["metadata"]["content_type"] = response.headers.get('content-type', '')

        # HTML 파싱
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, 'html.parser')

            # 제목 추출
            title_tag = soup.find('title')
            result["title"] = title_tag.get_text().strip() if title_tag else ""

            # 스크립트, 스타일 태그 제거
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()

            # 메타 정보 추출
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                result["metadata"]["description"] = meta_desc.get('content', '')

            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords:
                result["metadata"]["keywords"] = meta_keywords.get('content', '')

            # 본문 텍스트 추출
            # article, main, content 태그 우선
            main_content = soup.find('article') or soup.find('main') or soup.find(class_='content') or soup.find('body')

            if main_content:
                result["text"] = main_content.get_text(separator='\n', strip=True)
            else:
                result["text"] = soup.get_text(separator='\n', strip=True)

            # 이미지 추출
            if request.extract_images:
                images = []
                for img in soup.find_all('img', src=True):
                    img_src = img.get('src', '')
                    img_alt = img.get('alt', '')

                    # 상대 경로를 절대 경로로 변환
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        img_src = f"{parsed.scheme}://{parsed.netloc}{img_src}"
                    elif not img_src.startswith(('http://', 'https://')):
                        img_src = url.rsplit('/', 1)[0] + '/' + img_src

                    images.append({
                        "src": img_src,
                        "alt": img_alt
                    })

                result["images"] = images[:50]  # 최대 50개

        except ImportError:
            # BeautifulSoup이 없으면 기본 처리
            result["text"] = html_content
            result["metadata"]["parser_note"] = "BeautifulSoup not installed, returning raw HTML"

        # 텍스트 통계
        if result["text"]:
            result["metadata"]["char_count"] = len(result["text"])
            result["metadata"]["word_count"] = len(result["text"].split())

        return result

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"URL 요청 실패: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP 오류: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 오류: {str(e)}")


@router.get("/supported-formats")
async def get_supported_formats():
    """지원하는 파일 형식 목록"""
    return {
        "document": [
            {"extension": "pdf", "name": "PDF", "parser": "PyMuPDF"},
            {"extension": "docx", "name": "Word Document", "parser": "python-docx"},
            {"extension": "txt", "name": "Plain Text", "parser": "built-in"},
            {"extension": "md", "name": "Markdown", "parser": "built-in"},
        ],
        "data": [
            {"extension": "csv", "name": "CSV", "parser": "built-in"},
            {"extension": "json", "name": "JSON", "parser": "built-in"},
            {"extension": "xml", "name": "XML", "parser": "built-in"},
        ],
        "web": [
            {"extension": "html", "name": "HTML", "parser": "BeautifulSoup"},
        ],
        "crawler_options": {
            "js_rendering": "JavaScript 렌더링 (Playwright 필요)",
            "extract_images": "이미지 URL 추출"
        }
    }


@router.post("/chunk")
async def chunk_text(request: dict):
    """
    텍스트 청킹

    긴 텍스트를 지정된 크기의 청크로 분할
    """
    text = request.get("text", "")
    chunk_size = request.get("chunk_size", 500)
    overlap = request.get("overlap", 50)

    if not text:
        return {"chunks": [], "total_chunks": 0}

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # 단어 경계에서 자르기
        if end < len(text):
            # 공백을 찾아서 단어 경계에서 자름
            space_pos = text.rfind(' ', start, end)
            if space_pos > start:
                end = space_pos

        chunk = text[start:end].strip()
        if chunk:
            chunks.append({
                "index": len(chunks),
                "text": chunk,
                "start": start,
                "end": end,
                "char_count": len(chunk)
            })

        start = end - overlap
        if start < 0:
            start = 0
        if start >= len(text):
            break

    return {
        "chunks": chunks,
        "total_chunks": len(chunks),
        "settings": {
            "chunk_size": chunk_size,
            "overlap": overlap
        }
    }
