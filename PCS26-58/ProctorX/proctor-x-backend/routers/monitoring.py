from fastapi import APIRouter, HTTPException
from datetime import datetime
import os
import psutil

router = APIRouter()

@router.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "exam-proctoring-platform"
    }

@router.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_usage_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.get("/logs")
async def get_recent_logs():
    """Get recent application logs"""
    try:
        log_file = "data/logs/app.log"
        if not os.path.exists(log_file):
            return {"logs": []}
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Return last 50 lines
            recent_lines = lines[-50:] if len(lines) > 50 else lines
            
        return {
            "logs": [line.strip() for line in recent_lines],
            "total_lines": len(lines),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")

@router.get("/stats")
async def get_platform_stats():
    """Get platform statistics"""
    try:
        # Count files in data directories
        users_count = len(os.listdir("data/users")) if os.path.exists("data/users") else 0
        exams_count = len(os.listdir("data/exams")) if os.path.exists("data/exams") else 0
        submissions_count = len(os.listdir("data/submissions")) if os.path.exists("data/submissions") else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_users": users_count,
            "total_exams": exams_count,
            "total_submissions": submissions_count,
            "uptime_seconds": int(datetime.now().timestamp() - 1640995200)  # Placeholder
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")