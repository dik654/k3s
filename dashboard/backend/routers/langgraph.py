"""
LangGraph Agent API
워크플로우 코드 생성, 빌드, 배포
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import os

router = APIRouter(prefix="/api/langgraph", tags=["langgraph"])

# LangGraph 빌드 상태 저장
langgraph_builds: Dict[str, Dict[str, Any]] = {}


# ============================================
# 모델 정의
# ============================================

class LangGraphWorkflow(BaseModel):
    id: str
    name: str
    description: str = ""
    nodes: list = []
    connections: list = []


class LangGraphBuildRequest(BaseModel):
    workflow: dict
    image_name: str = ""
    image_tag: str = "latest"


# ============================================
# 코드 생성 함수
# ============================================

def generate_langgraph_code(workflow_data: dict) -> str:
    """워크플로우를 LangGraph Python 코드로 변환"""
    nodes = workflow_data.get('nodes', [])
    connections = workflow_data.get('connections', [])
    workflow_name = workflow_data.get('name', 'Untitled Agent')
    workflow_desc = workflow_data.get('description', '')

    # 노드 타입별 분류
    agent_nodes = [n for n in nodes if 'agent' in n.get('type', '').lower()]
    tool_nodes = [n for n in nodes if 'tool' in n.get('type', '').lower()]
    retriever_nodes = [n for n in nodes if 'retriever' in n.get('type', '').lower()]

    # Tools 결정
    tools_list = []
    for tn in tool_nodes:
        params = tn.get('data', {}).get('parameters', {})
        tool_type = params.get('tools', 'web_search')
        if tool_type == 'web_search':
            tools_list.append('web_search')
        elif tool_type == 'calculator':
            tools_list.append('calculator')
        elif tool_type == 'rag_retriever':
            tools_list.append('rag_retriever')

    if retriever_nodes:
        tools_list.append('rag_retriever')

    tools_list = list(set(tools_list))

    # Agent 설정
    agent_config = {
        'model': 'gpt-4',
        'temperature': 0.7,
        'system_prompt': 'You are a helpful assistant.'
    }
    if agent_nodes:
        params = agent_nodes[0].get('data', {}).get('parameters', {})
        agent_config['model'] = params.get('model', 'gpt-4')
        agent_config['temperature'] = params.get('temperature', 0.7)
        agent_config['system_prompt'] = params.get('systemPrompt', 'You are a helpful assistant.')

    code = f'''"""
LangGraph Agent - Auto-generated
Workflow: {workflow_name}
Description: {workflow_desc}
"""

import os
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool

# State Definition
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "Conversation messages"]
    context: str

'''

    # Tools 정의
    if 'web_search' in tools_list:
        code += '''
@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    from langchain_community.tools import DuckDuckGoSearchRun
    search = DuckDuckGoSearchRun()
    return search.run(query)
'''

    if 'calculator' in tools_list:
        code += '''
@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"
'''

    if 'rag_retriever' in tools_list:
        code += '''
@tool
def rag_retriever(query: str) -> str:
    """Retrieve relevant documents from vector store."""
    # Implement your RAG logic here
    return f"Retrieved context for: {query}"
'''

    tools_str = ', '.join(tools_list) if tools_list else ''
    code += f'''
tools = [{tools_str}]

# LLM Configuration
llm = ChatOpenAI(model="{agent_config['model']}", temperature={agent_config['temperature']})
llm_with_tools = llm.bind_tools(tools) if tools else llm

SYSTEM_PROMPT = """{agent_config['system_prompt']}"""

def agent_node(state: AgentState) -> AgentState:
    """Main agent node."""
    messages = list(state["messages"])
    if not any(getattr(m, 'type', '') == 'system' for m in messages):
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    response = llm_with_tools.invoke(messages)
    return {{"messages": state["messages"] + [response], "context": state.get("context", "")}}

def tools_node(state: AgentState) -> AgentState:
    """Execute tool calls."""
    tool_node = ToolNode(tools=tools)
    result = tool_node.invoke(state)
    return {{"messages": state["messages"] + result.get("messages", []), "context": state.get("context", "")}}

def create_graph():
    """Build the LangGraph workflow."""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
'''

    if tools_list:
        code += '''    workflow.add_node("tools", tools_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", tools_condition, {"continue": "tools", "end": END})
    workflow.add_edge("tools", "agent")
'''
    else:
        code += '''    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)
'''

    code += '''
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

graph = create_graph()

def run_agent(user_input: str, thread_id: str = "default") -> str:
    """Run the agent."""
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"messages": [HumanMessage(content=user_input)], "context": ""}, config)
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            return msg.content
    return "No response."

# FastAPI Server
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="LangGraph Agent API")

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        response = run_agent(request.message, request.thread_id)
        return {"response": response, "thread_id": request.thread_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
'''
    return code


def generate_dockerfile() -> str:
    """LangGraph 에이전트용 Dockerfile"""
    return '''FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py .
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8080/health || exit 1
CMD ["python", "agent.py"]
'''


def generate_requirements() -> str:
    """requirements.txt"""
    return '''langchain>=0.1.0
langchain-openai>=0.0.5
langchain-community>=0.0.20
langgraph>=0.0.40
duckduckgo-search>=4.0.0
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
'''


def generate_k8s_yaml(workflow_data: dict, image_name: str, image_tag: str) -> str:
    """K8s Deployment YAML"""
    safe_name = workflow_data.get('name', 'agent').lower().replace(' ', '-').replace('_', '-')[:40]
    return f'''apiVersion: apps/v1
kind: Deployment
metadata:
  name: langgraph-{safe_name}
  namespace: ai-workloads
spec:
  replicas: 1
  selector:
    matchLabels:
      app: langgraph-{safe_name}
  template:
    metadata:
      labels:
        app: langgraph-{safe_name}
    spec:
      containers:
      - name: agent
        image: {image_name}:{image_tag}
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-api-keys
              key: openai-api-key
              optional: true
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: langgraph-{safe_name}
  namespace: ai-workloads
spec:
  selector:
    app: langgraph-{safe_name}
  ports:
  - port: 8080
    targetPort: 8080
'''


# ============================================
# API 엔드포인트
# ============================================

@router.post("/generate-code")
async def generate_langgraph_code_api(workflow: dict):
    """워크플로우를 LangGraph Python 코드로 변환"""
    try:
        code = generate_langgraph_code(workflow)
        dockerfile = generate_dockerfile()
        requirements = generate_requirements()
        k8s_yaml = generate_k8s_yaml(workflow, f"langgraph-{workflow.get('id', 'agent')}", "latest")

        return {
            "success": True,
            "files": {
                "agent.py": code,
                "Dockerfile": dockerfile,
                "requirements.txt": requirements,
                "k8s-deployment.yaml": k8s_yaml
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build")
async def build_langgraph_image(request: LangGraphBuildRequest, background_tasks: BackgroundTasks):
    """워크플로우를 Docker 이미지로 빌드"""
    import tempfile
    import subprocess

    workflow = request.workflow
    image_name = request.image_name or f"langgraph-{workflow.get('id', 'agent')}"
    image_tag = request.image_tag
    build_id = str(uuid.uuid4())[:8]

    langgraph_builds[build_id] = {
        "status": "pending",
        "workflow_id": workflow.get('id'),
        "workflow_name": workflow.get('name'),
        "image_name": image_name,
        "image_tag": image_tag,
        "logs": [],
        "started_at": datetime.now().isoformat()
    }

    async def do_build():
        try:
            langgraph_builds[build_id]["status"] = "building"
            langgraph_builds[build_id]["logs"].append("Starting build...")

            with tempfile.TemporaryDirectory() as tmpdir:
                # Generate files
                code = generate_langgraph_code(workflow)
                with open(os.path.join(tmpdir, "agent.py"), "w") as f:
                    f.write(code)
                langgraph_builds[build_id]["logs"].append("Generated agent.py")

                with open(os.path.join(tmpdir, "Dockerfile"), "w") as f:
                    f.write(generate_dockerfile())

                with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                    f.write(generate_requirements())

                # Docker build
                full_image = f"{image_name}:{image_tag}"
                langgraph_builds[build_id]["logs"].append(f"Building {full_image}...")

                result = subprocess.run(
                    ["docker", "build", "-t", full_image, "."],
                    cwd=tmpdir, capture_output=True, text=True, timeout=600
                )

                if result.returncode != 0:
                    langgraph_builds[build_id]["status"] = "failed"
                    langgraph_builds[build_id]["error"] = result.stderr
                    return

                langgraph_builds[build_id]["logs"].append("Docker build completed")

                # Import to k3s
                tar_path = os.path.join(tmpdir, "image.tar")
                subprocess.run(["docker", "save", "-o", tar_path, full_image], capture_output=True)
                subprocess.run(["sudo", "-n", "k3s", "ctr", "images", "import", tar_path], capture_output=True)

                langgraph_builds[build_id]["status"] = "completed"
                langgraph_builds[build_id]["completed_at"] = datetime.now().isoformat()
                langgraph_builds[build_id]["logs"].append("Build completed!")

        except Exception as e:
            langgraph_builds[build_id]["status"] = "failed"
            langgraph_builds[build_id]["error"] = str(e)

    background_tasks.add_task(do_build)
    return {"success": True, "build_id": build_id}


@router.get("/build/{build_id}/status")
async def get_build_status(build_id: str):
    """빌드 상태 조회"""
    if build_id not in langgraph_builds:
        raise HTTPException(status_code=404, detail="Build not found")
    return langgraph_builds[build_id]


@router.get("/builds")
async def list_builds():
    """빌드 목록"""
    return {"builds": list(langgraph_builds.values())}


@router.post("/deploy/{build_id}")
async def deploy_agent(build_id: str):
    """빌드된 에이전트 배포"""
    import subprocess
    import tempfile

    if build_id not in langgraph_builds:
        raise HTTPException(status_code=404, detail="Build not found")

    build = langgraph_builds[build_id]
    if build["status"] != "completed":
        raise HTTPException(status_code=400, detail="Build not completed")

    k8s_yaml = generate_k8s_yaml(
        {"name": build["workflow_name"], "id": build["workflow_id"]},
        build["image_name"],
        build["image_tag"]
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(k8s_yaml)
        yaml_path = f.name

    result = subprocess.run(["kubectl", "apply", "-f", yaml_path], capture_output=True, text=True)
    os.unlink(yaml_path)

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr)

    return {"success": True, "message": "Deployed successfully"}
