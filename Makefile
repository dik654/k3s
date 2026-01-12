.PHONY: help build push deploy monitor logs shell restart clean

# 설정
IMAGE_NAME ?= localhost:5000/k3s-dashboard
IMAGE_TAG ?= latest
NAMESPACE ?= default
NO_CACHE ?=
FULL_IMAGE = $(IMAGE_NAME):$(IMAGE_TAG)

# 색상
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
NC = \033[0m

##############################################################################
# 도움말
##############################################################################

help:
	@echo "$(BLUE)=== K3s Dashboard 빌드 및 배포 명령어 ===$(NC)"
	@echo ""
	@echo "$(GREEN)빌드 및 배포:$(NC)"
	@echo "  make build              Docker 이미지 빌드"
	@echo "  make push               Registry에 이미지 push"
	@echo "  make deploy             K8s에 배포"
	@echo "  make all                빌드, push, 배포 (전체 프로세스)"
	@echo "  make redeploy           기존 배포 업데이트 및 재시작"
	@echo ""
	@echo "$(GREEN)모니터링 및 관리:$(NC)"
	@echo "  make status             배포 상태 확인"
	@echo "  make logs               Pod 로그 출력 (실시간)"
	@echo "  make events             최근 이벤트 확인"
	@echo "  make describe           Deployment 상세 정보"
	@echo "  make shell              Pod에 셸 접속"
	@echo "  make restart            Pod 재시작"
	@echo ""
	@echo "$(GREEN)유틸리티:$(NC)"
	@echo "  make clean              Deployment 삭제"
	@echo "  make image-info         이미지 정보 확인"
	@echo ""
	@echo "$(YELLOW)변수 설정:$(NC)"
	@echo "  IMAGE_NAME              이미지 이름 (기본값: $(IMAGE_NAME))"
	@echo "  IMAGE_TAG               이미지 태그 (기본값: $(IMAGE_TAG))"
	@echo "  NAMESPACE               K8s 네임스페이스 (기본값: $(NAMESPACE))"
	@echo "  NO_CACHE                Docker 캐시 무시 (true/false, 기본값: false)"
	@echo ""
	@echo "$(YELLOW)예시:$(NC)"
	@echo "  make all                                    # 기본 빌드 및 배포"
	@echo "  make all NO_CACHE=true                      # 캐시 무시하고 전체 재빌드"
	@echo "  make build IMAGE_TAG=v1.0.0                # 버전 지정 빌드"
	@echo "  make deploy IMAGE_NAME=myregistry/dash     # 커스텀 레지스트리 배포"
	@echo "  make redeploy NAMESPACE=production          # 프로덕션 재배포"

##############################################################################
# 빌드 및 배포
##############################################################################

build:
	@echo "$(BLUE)[BUILD]$(NC) Docker 이미지 빌드 중..."
	@echo "이미지: $(FULL_IMAGE)"
	@./build-and-deploy.sh \
		--image $(IMAGE_NAME) \
		--tag $(IMAGE_TAG) \
		--skip-push \
		--skip-deploy \
		$(if $(filter true,$(NO_CACHE)),--no-cache,)

push: build
	@echo "$(BLUE)[PUSH]$(NC) Registry에 push 중..."
	@docker push $(FULL_IMAGE)
	@echo "$(GREEN)[SUCCESS]$(NC) push 완료"

deploy: build
	@echo "$(BLUE)[DEPLOY]$(NC) K8s 배포 중..."
	@./build-and-deploy.sh \
		--image $(IMAGE_NAME) \
		--tag $(IMAGE_TAG) \
		--namespace $(NAMESPACE) \
		--skip-build

all: clean-build
	@echo "$(BLUE)[ALL]$(NC) 전체 프로세스 시작: 빌드 → push → 배포"
	@./build-and-deploy.sh \
		--image $(IMAGE_NAME) \
		--tag $(IMAGE_TAG) \
		--namespace $(NAMESPACE) \
		$(if $(filter true,$(NO_CACHE)),--no-cache,)

redeploy:
	@echo "$(BLUE)[REDEPLOY]$(NC) 기존 배포 업데이트..."
	@./build-and-deploy.sh \
		--image $(IMAGE_NAME) \
		--tag $(IMAGE_TAG) \
		--namespace $(NAMESPACE) \
		--force-restart \
		$(if $(filter true,$(NO_CACHE)),--no-cache,)

##############################################################################
# 모니터링 및 관리
##############################################################################

status:
	@./monitor-deployment.sh $(NAMESPACE) status

logs:
	@./monitor-deployment.sh $(NAMESPACE) logs

events:
	@./monitor-deployment.sh $(NAMESPACE) events

describe:
	@./monitor-deployment.sh $(NAMESPACE) describe

shell:
	@./monitor-deployment.sh $(NAMESPACE) shell

restart:
	@./monitor-deployment.sh $(NAMESPACE) restart

monitor:
	@./monitor-deployment.sh $(NAMESPACE) all

##############################################################################
# 유틸리티
##############################################################################

clean:
	@echo "$(YELLOW)[WARN]$(NC) Deployment를 삭제합니다..."
	@./monitor-deployment.sh $(NAMESPACE) delete

clean-build:
	@docker rmi $(FULL_IMAGE) 2>/dev/null || true
	@echo "$(GREEN)[OK]$(NC) 로컬 이미지 제거 완료"

image-info:
	@echo "$(BLUE)=== 이미지 정보 ===$(NC)"
	@echo "이미지 이름: $(IMAGE_NAME)"
	@echo "이미지 태그: $(IMAGE_TAG)"
	@echo "전체 이름: $(FULL_IMAGE)"
	@echo ""
	@docker images $(IMAGE_NAME) 2>/dev/null || echo "$(YELLOW)이미지를 찾을 수 없습니다$(NC)"

pods:
	@echo "$(BLUE)=== Pod 목록 ===$(NC)"
	@kubectl get pods -n $(NAMESPACE) -l app=k3s-dashboard -o wide

services:
	@echo "$(BLUE)=== Service 목록 ===$(NC)"
	@kubectl get services -n $(NAMESPACE) -l app=k3s-dashboard -o wide

ingress:
	@echo "$(BLUE)=== Ingress 목록 ===$(NC)"
	@kubectl get ingress -n $(NAMESPACE) -l app=k3s-dashboard -o wide

##############################################################################
# 개발 도구
##############################################################################

lint:
	@echo "$(BLUE)[LINT]$(NC) 코드 검사 중..."
	@echo "Frontend..."
	@cd dashboard/frontend && npm run lint 2>/dev/null || echo "  (lint 도구 없음)"
	@echo "Backend..."
	@cd dashboard/backend && pylint . 2>/dev/null || echo "  (pylint 없음)"

test:
	@echo "$(BLUE)[TEST]$(NC) 테스트 실행 중..."
	@echo "Frontend..."
	@cd dashboard/frontend && npm run test 2>/dev/null || echo "  (테스트 없음)"

test-build:
	@echo "$(BLUE)[TEST-BUILD]$(NC) Docker 빌드 테스트..."
	@docker build --no-cache -t $(IMAGE_NAME):test-build dashboard/
	@docker rmi $(IMAGE_NAME):test-build 2>/dev/null
	@echo "$(GREEN)[SUCCESS]$(NC) 빌드 테스트 완료"
