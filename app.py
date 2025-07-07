#!/usr/bin/env python3
"""
Servidor ultra-simple para Render - Arranca inmediatamente
"""

import os
import asyncio
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

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
app = FastAPI(title="Guruwalk Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage simple
tasks = {}

# Endpoints simples
@app.get("/")
def root():
    return {"status": "online", "message": "Guruwalk Agent API"}

@app.get("/ping")
def ping():
    return {"ping": "pong"}

@app.get("/health")
def health():
    return {"status": "healthy", "tasks_count": len(tasks)}

@app.post("/tasks")
def create_task(request: TaskRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    
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
        "task": final_task,
        "result": None,
        "error": None
    }
    
    # Ejecutar en background
    background_tasks.add_task(run_agent_task, task_id)
    
    return TaskResponse(
        task_id=task_id,
        status="started",
        message="Task created successfully"
    )

@app.get("/tasks/{task_id}")
def get_task(task_id: str):
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
def list_tasks():
    return {"tasks": list(tasks.keys()), "count": len(tasks)}

# Background task que usa lazy loading
def run_agent_task(task_id: str):
    """Ejecutar tarea en background con lazy loading"""
    asyncio.create_task(_async_run_task(task_id))

async def _async_run_task(task_id: str):
    try:
        print(f"🚀 Starting task {task_id}")
        tasks[task_id]["status"] = "running"
        
        # Import solo cuando se necesita
        from browser_use import Agent
        from browser_use.browser import BrowserSession, BrowserProfile
        from browser_use.llm.openai.chat import ChatOpenAI
        
        # Crear browser
        profile = BrowserProfile(
            headless=True,
            user_data_dir=None,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--no-first-run',
            ]
        )
        
        browser = BrowserSession(browser_profile=profile)
        await browser.start()
        
        # Crear LLM
        llm = ChatOpenAI(model='gpt-4o-mini')
        
        # Crear y ejecutar agente
        agent = Agent(task=tasks[task_id]["task"], llm=llm, browser_session=browser)
        result = await agent.run()
        
        # Guardar resultado
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = {"success": True}
        
        print(f"✅ Task {task_id} completed")
        
        # Cerrar browser
        await browser.close()
        
    except Exception as e:
        print(f"❌ Task {task_id} failed: {e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)

# Arrancar servidor
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port) 