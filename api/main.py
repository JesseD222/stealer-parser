"""
FastAPI backend for stealer parser web interface.
Provides REST API endpoints for file upload, processing, and result retrieval.
"""
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import the existing stealer parser modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from stealer_parser.main import read_archive, process_archive
from stealer_parser.models import Leak
from stealer_parser.helpers import init_logger, EnhancedJSONEncoder
import json


# FastAPI app initialization
app = FastAPI(
    title="Stealer Parser API",
    description="REST API for parsing infostealer malware logs",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage for processing jobs (in production, use Redis or database)
processing_jobs = {}

# Logger setup
logger = init_logger("StealerParserAPI", 1)


class ProcessingStatus:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = "pending"  # pending, processing, completed, failed
        self.progress = 0
        self.current_step = ""
        self.result = None
        self.error = None


async def process_file_background(
    job_id: str, 
    file_path: str, 
    filename: str, 
    password: Optional[str] = None
):
    """Background task to process uploaded archive file."""
    job = processing_jobs[job_id]
    
    try:
        job.status = "processing"
        job.current_step = "Reading archive"
        job.progress = 10
        
        # Create leak object
        leak = Leak(filename=filename)
        
        # Read and process archive
        with open(file_path, "rb") as file_handle:
            from io import BytesIO
            with BytesIO(file_handle.read()) as buffer:
                job.current_step = "Opening archive"
                job.progress = 20
                
                archive = read_archive(buffer, filename, password)
                
                job.current_step = "Processing archive contents"
                job.progress = 40
                
                process_archive(logger, leak, archive)
                
                job.current_step = "Finalizing results"
                job.progress = 90
                
                # Convert result to JSON-serializable format
                job.result = json.loads(
                    json.dumps(leak, cls=EnhancedJSONEncoder, ensure_ascii=False)
                )
                
                job.progress = 100
                job.status = "completed"
                job.current_step = "Complete"
                
                archive.close()
                
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        logger.error(f"Failed processing job {job_id}: {e}")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(file_path)
        except:
            pass


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "stealer-parser-api"}


@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    password: Optional[str] = None
):
    """Upload and process stealer archive file."""
    
    # Validate file type
    allowed_extensions = ['.zip', '.rar', '.7z']
    file_extension = Path(file.filename or '').suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Only {', '.join(allowed_extensions)} files are supported."
        )
    
    # Validate file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail="File size too large. Maximum allowed size is 100MB."
        )
    
    # Generate job ID and create temporary file
    job_id = str(uuid.uuid4())
    
    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=file_extension)
    
    try:
        # Write uploaded file to temporary location
        with os.fdopen(temp_fd, 'wb') as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        # Initialize processing job
        processing_jobs[job_id] = ProcessingStatus(job_id)
        
        # Start background processing
        background_tasks.add_task(
            process_file_background,
            job_id,
            temp_path,
            file.filename or "unknown",
            password
        )
        
        return {
            "job_id": job_id,
            "status": "accepted",
            "message": "File uploaded successfully and processing started"
        }
        
    except Exception as e:
        # Clean up on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """Get processing status for a job."""
    
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
    response = {
        "job_id": job_id,
        "status": job.status,
        "progress": job.progress,
        "current_step": job.current_step
    }
    
    if job.error:
        response["error"] = job.error
    
    return response


@app.get("/api/result/{job_id}")
async def get_job_result(job_id: str):
    """Get processing result for a completed job."""
    
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
    if job.status == "processing" or job.status == "pending":
        raise HTTPException(status_code=202, detail="Job still processing")
    
    if job.status == "failed":
        raise HTTPException(status_code=500, detail=job.error or "Processing failed")
    
    if job.status == "completed" and job.result:
        return JSONResponse(content=job.result)
    
    raise HTTPException(status_code=500, detail="No result available")


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a processing job and clean up resources."""
    
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del processing_jobs[job_id]
    
    return {"message": "Job deleted successfully"}


@app.get("/api/jobs")
async def list_jobs():
    """List all processing jobs (for admin/debugging)."""
    
    jobs = []
    for job_id, job in processing_jobs.items():
        jobs.append({
            "job_id": job_id,
            "status": job.status,
            "progress": job.progress,
            "current_step": job.current_step
        })
    
    return {"jobs": jobs}


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )