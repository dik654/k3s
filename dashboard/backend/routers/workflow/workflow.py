"""
Workflow CRUD API (n8n-style)
워크플로우 생성, 조회, 수정, 삭제, 실행 API
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from models.workflow import WorkflowCreate, WorkflowUpdate
from core.config import settings

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

WORKFLOWS_DIR = settings.WORKFLOWS_DIR
EXECUTIONS_DIR = os.path.join(os.path.dirname(WORKFLOWS_DIR), "executions")

# 디렉터리 생성
os.makedirs(WORKFLOWS_DIR, exist_ok=True)
os.makedirs(EXECUTIONS_DIR, exist_ok=True)


# 실행 관련 모델
class ExecutionInput(BaseModel):
    """워크플로우 실행 입력"""
    input_data: Optional[Dict[str, Any]] = None


class NodeResult(BaseModel):
    """노드 실행 결과"""
    node_id: str
    status: str  # pending, running, success, error
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


# 실행 상태 저장 (메모리)
execution_states: Dict[str, Dict] = {}


# 헬퍼 함수
def _get_workflow_path(workflow_id: str) -> str:
    """Get file path for a workflow"""
    return os.path.join(WORKFLOWS_DIR, f"{workflow_id}.json")


def _load_workflow(workflow_id: str) -> Optional[dict]:
    """Load a workflow from disk"""
    path = _get_workflow_path(workflow_id)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def _save_workflow(workflow: dict) -> None:
    """Save a workflow to disk"""
    path = _get_workflow_path(workflow['id'])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, ensure_ascii=False, indent=2)


# API 엔드포인트
@router.post("")
async def create_workflow(workflow: WorkflowCreate):
    """Create a new workflow"""
    workflow_id = str(uuid.uuid4())

    new_workflow = {
        "id": workflow_id,
        "name": workflow.name,
        "description": workflow.description or "",
        "nodes": workflow.nodes,
        "connections": workflow.connections,
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat()
    }

    _save_workflow(new_workflow)

    return {
        "success": True,
        "workflow": new_workflow
    }


@router.get("")
async def list_workflows():
    """List all workflows"""
    workflows = []

    if os.path.exists(WORKFLOWS_DIR):
        for filename in os.listdir(WORKFLOWS_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(WORKFLOWS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        workflow = json.load(f)
                        workflows.append({
                            "id": workflow.get("id"),
                            "name": workflow.get("name"),
                            "description": workflow.get("description", ""),
                            "nodeCount": len(workflow.get("nodes", [])),
                            "createdAt": workflow.get("createdAt"),
                            "updatedAt": workflow.get("updatedAt")
                        })
                except Exception as e:
                    print(f"Error loading workflow {filename}: {e}")

    workflows.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)

    return {"workflows": workflows}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a specific workflow"""
    workflow = _load_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {"workflow": workflow}


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, update: WorkflowUpdate):
    """Update an existing workflow"""
    workflow = _load_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if update.name is not None:
        workflow["name"] = update.name
    if update.description is not None:
        workflow["description"] = update.description
    if update.nodes is not None:
        workflow["nodes"] = update.nodes
    if update.connections is not None:
        workflow["connections"] = update.connections

    workflow["updatedAt"] = datetime.now().isoformat()

    _save_workflow(workflow)

    return {
        "success": True,
        "workflow": workflow
    }


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow"""
    path = _get_workflow_path(workflow_id)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Workflow not found")

    os.remove(path)

    return {
        "success": True,
        "message": f"Workflow {workflow_id} deleted"
    }


# ===== 실행 관련 헬퍼 함수 =====

def _get_execution_path(execution_id: str) -> str:
    """Get file path for an execution"""
    return os.path.join(EXECUTIONS_DIR, f"{execution_id}.json")


def _load_execution(execution_id: str) -> Optional[dict]:
    """Load an execution from disk"""
    path = _get_execution_path(execution_id)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def _save_execution(execution: dict) -> None:
    """Save an execution to disk"""
    path = _get_execution_path(execution['id'])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(execution, f, ensure_ascii=False, indent=2)


def _get_node_execution_order(nodes: List[dict], connections: List[dict]) -> List[str]:
    """노드 실행 순서 결정 (토폴로지 정렬)"""
    if not nodes:
        return []

    # 인접 리스트 및 진입 차수 생성
    adjacency = {n.get('id', n.get('data', {}).get('id', '')): [] for n in nodes}
    in_degree = {n.get('id', n.get('data', {}).get('id', '')): 0 for n in nodes}

    for conn in connections:
        source = conn.get('source') or conn.get('sourceNodeId')
        target = conn.get('target') or conn.get('targetNodeId')
        if source and target and source in adjacency:
            adjacency[source].append(target)
            if target in in_degree:
                in_degree[target] += 1

    # 토폴로지 정렬 (Kahn's algorithm)
    queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
    order = []

    while queue:
        node_id = queue.pop(0)
        order.append(node_id)

        for neighbor in adjacency.get(node_id, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


async def _execute_node(node: dict, input_data: dict, execution_id: str) -> dict:
    """단일 노드 실행 (시뮬레이션)"""
    node_id = node.get('id', node.get('data', {}).get('id', ''))
    node_type = node.get('type') or node.get('data', {}).get('type', 'unknown')
    node_name = node.get('name') or node.get('data', {}).get('name', node_type)

    # 실행 상태 업데이트
    if execution_id in execution_states:
        execution_states[execution_id]['node_results'][node_id] = {
            'node_id': node_id,
            'status': 'running',
            'started_at': datetime.now().isoformat()
        }

    # 노드 타입별 시뮬레이션 실행
    await asyncio.sleep(0.5 + (hash(node_id) % 10) / 10)  # 0.5~1.5초 대기

    # 결과 생성 (시뮬레이션)
    result = {
        'node_id': node_id,
        'status': 'success',
        'output': {
            'type': node_type,
            'name': node_name,
            'processed': True,
            'input_received': list(input_data.keys()) if input_data else [],
            'timestamp': datetime.now().isoformat()
        },
        'started_at': execution_states.get(execution_id, {}).get('node_results', {}).get(node_id, {}).get('started_at'),
        'finished_at': datetime.now().isoformat()
    }

    # 실행 상태 업데이트
    if execution_id in execution_states:
        execution_states[execution_id]['node_results'][node_id] = result

    return result


async def _execute_workflow_task(workflow: dict, execution_id: str, input_data: dict):
    """백그라운드에서 워크플로우 실행"""
    try:
        nodes = workflow.get('nodes', [])
        connections = workflow.get('connections', [])

        # 실행 순서 결정
        execution_order = _get_node_execution_order(nodes, connections)

        # 노드 맵 생성
        node_map = {}
        for n in nodes:
            nid = n.get('id', n.get('data', {}).get('id', ''))
            if nid:
                node_map[nid] = n

        # 노드별 실행
        node_outputs = {}
        for node_id in execution_order:
            node = node_map.get(node_id)
            if not node:
                continue

            # 이전 노드 출력을 입력으로
            node_input = input_data.copy() if input_data else {}
            for conn in connections:
                source = conn.get('source') or conn.get('sourceNodeId')
                target = conn.get('target') or conn.get('targetNodeId')
                if target == node_id and source in node_outputs:
                    node_input[source] = node_outputs[source]

            # 노드 실행
            result = await _execute_node(node, node_input, execution_id)
            node_outputs[node_id] = result.get('output', {})

        # 실행 완료
        if execution_id in execution_states:
            execution_states[execution_id]['status'] = 'completed'
            execution_states[execution_id]['finished_at'] = datetime.now().isoformat()
            execution_states[execution_id]['output'] = node_outputs

            # 디스크에 저장
            _save_execution(execution_states[execution_id])

    except Exception as e:
        if execution_id in execution_states:
            execution_states[execution_id]['status'] = 'failed'
            execution_states[execution_id]['error'] = str(e)
            execution_states[execution_id]['finished_at'] = datetime.now().isoformat()
            _save_execution(execution_states[execution_id])


# ===== 실행 API 엔드포인트 =====

@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    execution_input: ExecutionInput,
    background_tasks: BackgroundTasks
):
    """워크플로우 실행"""
    workflow = _load_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    execution_id = str(uuid.uuid4())

    # 실행 상태 초기화
    execution = {
        'id': execution_id,
        'workflow_id': workflow_id,
        'workflow_name': workflow.get('name'),
        'status': 'running',
        'input': execution_input.input_data or {},
        'output': None,
        'error': None,
        'node_results': {},
        'started_at': datetime.now().isoformat(),
        'finished_at': None
    }

    # 메모리에 저장
    execution_states[execution_id] = execution

    # 백그라운드에서 실행
    background_tasks.add_task(
        _execute_workflow_task,
        workflow,
        execution_id,
        execution_input.input_data or {}
    )

    return {
        'success': True,
        'execution_id': execution_id,
        'status': 'running',
        'message': f'Workflow execution started'
    }


@router.get("/{workflow_id}/executions")
async def list_executions(workflow_id: str):
    """워크플로우 실행 이력 조회"""
    workflow = _load_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    executions = []

    # 디스크에서 실행 이력 로드
    if os.path.exists(EXECUTIONS_DIR):
        for filename in os.listdir(EXECUTIONS_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(EXECUTIONS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        execution = json.load(f)
                        if execution.get('workflow_id') == workflow_id:
                            executions.append({
                                'id': execution.get('id'),
                                'status': execution.get('status'),
                                'started_at': execution.get('started_at'),
                                'finished_at': execution.get('finished_at'),
                                'error': execution.get('error')
                            })
                except Exception:
                    pass

    # 메모리에서 실행 중인 항목 추가
    for exec_id, execution in execution_states.items():
        if execution.get('workflow_id') == workflow_id:
            if not any(e['id'] == exec_id for e in executions):
                executions.append({
                    'id': execution.get('id'),
                    'status': execution.get('status'),
                    'started_at': execution.get('started_at'),
                    'finished_at': execution.get('finished_at'),
                    'error': execution.get('error')
                })

    executions.sort(key=lambda x: x.get('started_at', ''), reverse=True)

    return {'executions': executions}


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """실행 상태/결과 조회"""
    # 메모리에서 먼저 확인
    if execution_id in execution_states:
        return {'execution': execution_states[execution_id]}

    # 디스크에서 로드
    execution = _load_execution(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return {'execution': execution}
