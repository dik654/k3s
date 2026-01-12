"""
베어메탈 프로비저닝 라우터

Tinkerbell 기반 베어메탈 서버 관리:
- 하드웨어 등록/관리
- OS 템플릿 관리
- 프로비저닝 워크플로우
- 대여 세션 관리
- 디스크 스왑
"""
from .tinkerbell import router as tinkerbell_router
from .rental import router as rental_router

__all__ = ['tinkerbell_router', 'rental_router']
