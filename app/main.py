from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI()

# MongoDB connection
import os

MONGO_USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
MONGO_PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "password")
MONGO_URL = f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@mongodb:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client.task_manager

# Task model
class Task(BaseModel):
    id: Optional[str]
    title: str
    description: str
    status: str = "pending"
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

# MongoDB collection
tasks_collection = db.tasks

@app.get("/")
async def read_root():
    return {"message": "Welcome to Task Manager API"}

@app.post("/tasks/", response_model=Task)
async def create_task(task: Task):
    task_dict = task.dict()
    task_dict.pop("id", None)  # Remove id if present as MongoDB will create one
    result = await tasks_collection.insert_one(task_dict)
    task_dict["id"] = str(result.inserted_id)
    return task_dict

@app.get("/tasks/", response_model=List[Task])
async def read_tasks():
    tasks = []
    cursor = tasks_collection.find({})
    async for document in cursor:
        document["id"] = str(document.pop("_id"))
        tasks.append(document)
    return tasks

@app.get("/tasks/{task_id}", response_model=Task)
async def read_task(task_id: str):
    from bson import ObjectId
    task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
    if task:
        task["id"] = str(task.pop("_id"))
        return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task: Task):
    from bson import ObjectId
    task_dict = task.dict(exclude_unset=True)
    task_dict.pop("id", None)  # Remove id from update data
    task_dict["updated_at"] = datetime.now()
    
    result = await tasks_collection.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": task_dict}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    updated_task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
    updated_task["id"] = str(updated_task.pop("_id"))
    return updated_task

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    from bson import ObjectId
    result = await tasks_collection.delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}