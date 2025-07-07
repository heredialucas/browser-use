#!/usr/bin/env python3
"""
Servidor FastAPI para Guruwalk Agent - Optimizado para Render
"""

import asyncio
import os
import sys
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

load_dotenv()

# Modelos
class TaskRequest(BaseModel):
    task: str = "default"
    custom_task: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None

# App
app = FastAPI(title="Guruwalk Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage
tasks = {}
browser_session = None
llm_model = None

# Lazy loading functions
async def get_browser():
    global browser_session
    if browser_session is None:
        from browser_use.browser import BrowserSession, BrowserProfile
        
        print("🔄 Starting browser...")
        profile = BrowserProfile(
            headless=True,
            user_data_dir=None,
            disable_security=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-extensions',
                '--disable-plugins',
                '--no-first-run',
                '--disable-default-apps',
            ]
        )
        
        try:
            browser_session = BrowserSession(browser_profile=profile)
            await asyncio.wait_for(browser_session.start(), timeout=60)
            print("✅ Browser started")
        except asyncio.TimeoutError:
            print("❌ Browser startup timeout")
            raise HTTPException(status_code=503, detail="Browser startup timeout")
        except Exception as e:
            print(f"❌ Browser failed to start: {e}")
            raise HTTPException(status_code=503, detail=f"Browser unavailable: {str(e)}")
    
    return browser_session

async def get_llm():
    global llm_model
    if llm_model is None:
        from browser_use.llm.openai.chat import ChatOpenAI
        llm_model = ChatOpenAI(model='gpt-4o-mini')
        print("✅ LLM initialized")
    
    return llm_model

# Endpoints
@app.get("/")
async def root():
    return {"message": "Guruwalk Agent API", "status": "online"}

@app.get("/ping")
async def ping():
    return {"ping": "pong"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "browser": "ready" if browser_session else "not_started",
        "active_tasks": len([t for t in tasks.values() if t["status"] == "running"]),
        "server": "online"
    }

@app.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    
    # Default task
    default_task = """
    1. Ve a https://www.guruwalk.com/es
    2. Haz clic en 'Iniciar sesión' o 'Login'.
    3. Haz clic en el botón que dice 'Seguir con contraseña' o similar.
    4. Cuando aparezcan los campos, ingresa el email: heredialucasfac22@gmail.com
    5. Ingresa la contraseña exacta: Lucas37312237. (incluye el punto al final)
    6. Haz clic en 'Iniciar sesión' para completar el login.
    7. Una vez dentro, navega a la sección 'Reservas'.
    8. Confirma que puedes ver el contenido de Reservas.
    9. Termina el flujo mostrando que fue exitoso.
    """
    
    final_task = request.custom_task if request.custom_task else default_task
    
    tasks[task_id] = {
        "status": "pending",
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(run_task, task_id, final_task)
    
    return TaskResponse(
        task_id=task_id,
        status="started",
        message="Task created successfully"
    )

@app.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return TaskStatus(
        task_id=task_id,
        status=task["status"],
        result=task["result"],
        error=task["error"]
    )

@app.get("/tasks")
async def list_tasks():
    return {"tasks": list(tasks.keys()), "count": len(tasks)}

# Background task runner
async def run_task(task_id: str, task_text: str):
    try:
        print(f"🚀 Starting task {task_id}")
        tasks[task_id]["status"] = "running"
        
        # Get browser and LLM
        browser = await get_browser()
        llm = await get_llm()
        
        # Import and create agent
        from browser_use import Agent
        agent = Agent(task=task_text, llm=llm, browser_session=browser)
        
        # Run agent
        result = await agent.run()
        
        # Save result
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = {
            "success": True,
            "usage": result.usage.model_dump() if result and result.usage else None
        }
        
        print(f"✅ Task {task_id} completed")
        
    except Exception as e:
        print(f"❌ Task {task_id} failed: {e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)

# Run server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=75
    ) 