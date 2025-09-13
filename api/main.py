"""
High-performance FastAPI backend for stealer parser with async processing.
Supports millions of records with database storage and Redis job queue.
"""
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.background import BackgroundTasks
import uvicorn

# Import async processing modules
from .database import db_manager, ParseSession
from .async_processor import async_processor, BackgroundWorker

# Import existing stealer parser modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from stealer_parser.helpers import init_logger
from sqlalchemy.sql import text


# FastAPI app initialization with async support
app = FastAPI(
    title="Stealer Parser API - High Performance",
    description="Async REST API for parsing infostealer malware logs with database storage",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger setup
logger = init_logger("AsyncStealerParserAPI", 2)

# Background worker instance
background_worker = None


@app.on_event("startup")
async def startup_event():
    """Initialize database and async processing on startup."""
    logger.info("Initializing async stealer parser API...")
    
    try:
        # Initialize database
        await db_manager.init_database()
        logger.info("Database initialized successfully")
        
        # Initialize Redis and async processor
        await async_processor.init_redis()
        logger.info("Redis and async processor initialized")
        
        # Start background worker for job processing
        global background_worker
        background_worker = BackgroundWorker()
        
        # Note: In production, run workers as separate processes
        # For demo, we'll start one worker in background
        import asyncio
        asyncio.create_task(background_worker.start_worker())
        logger.info("Background worker started")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


@app.on_event("shutdown") 
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down async stealer parser API...")
    
    if background_worker:
        background_worker.stop_worker()
    
    await db_manager.close()
    logger.info("Cleanup completed")


@app.get("/api/health")
async def health_check():
    """Enhanced health check with database and Redis status."""
    try:
        # Check database connection
        async with db_manager.get_session() as session:
            await session.execute(text("SELECT 1"))
        db_status = "healthy"
        
        # Check Redis connection
        redis_status = await async_processor.get_job_status("health_check")
        redis_status = "healthy"
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "service": "async-stealer-parser-api",
            "error": str(e)
        }
    
    return {
        "status": "healthy",
        "service": "async-stealer-parser-api",
        "version": "2.0.0",
        "database": db_status,
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/upload")
async def upload_file_async(
    file: UploadFile = File(...),
    password: Optional[str] = None
):
    """
    Upload and queue stealer archive file for async processing.
    Supports millions of records with database storage.
    """
    
    # Validate file type
    allowed_extensions = ['.zip', '.rar', '.7z']
    file_extension = Path(file.filename or '').suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Only {', '.join(allowed_extensions)} files are supported."
        )
    
    # Validate file size (500MB limit for high-performance version)
    max_size = 500 * 1024 * 1024  # 500MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail="File size too large. Maximum allowed size is 500MB."
        )
    
    # Generate session ID and create temporary file
    session_id = str(uuid.uuid4())
    
    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=file_extension)
    
    try:
        # Write uploaded file to temporary location
        with os.fdopen(temp_fd, 'wb') as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        # Create parse session in database
        await db_manager.create_parse_session(
            session_id=session_id,
            filename=file.filename or "unknown",
            file_size=file_size,
            metadata={"upload_ip": "127.0.0.1", "user_agent": "stealer-parser-web"}
        )
        
        # Queue processing job
        await async_processor.queue_processing_job(
            session_id=session_id,
            file_path=temp_path,
            filename=file.filename or "unknown",
            password=password
        )
        
        logger.info(f"Queued processing for {file.filename} ({file_size} bytes)")
        
        return {
            "session_id": session_id,
            "status": "queued",
            "message": "File uploaded successfully and queued for processing",
            "file_size": file_size,
            "estimated_processing_time": f"{max(30, file_size // 1000000)} seconds"
        }
        
    except Exception as e:
        # Clean up on error
        try:
            os.unlink(temp_path)
        except:
            pass
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@app.get("/api/status/{session_id}")
async def get_processing_status(session_id: str):
    """Get real-time processing status from Redis and database."""
    
    try:
        # Get status from Redis (real-time)
        redis_status = await async_processor.get_job_status(session_id)
        
        if redis_status:
            return {
                "session_id": session_id,
                "status": redis_status["status"],
                "progress": redis_status["progress"], 
                "current_step": redis_status["current_step"],
                "updated_at": redis_status.get("updated_at"),
                "processing_time": redis_status.get("processing_time"),
                "error_message": redis_status.get("error_message")
            }
        
        # Fallback to database status
        async with db_manager.get_session() as session:
            result = await session.execute(
                text("SELECT status, progress, current_step, error_message "
                     "FROM parse_sessions WHERE id = :session_id"),
                {"session_id": session_id}
            )
            row = result.fetchone()
            
            if row:
                return {
                    "session_id": session_id,
                    "status": row.status,
                    "progress": row.progress or 0,
                    "current_step": row.current_step or "Unknown",
                    "error_message": row.error_message
                }
        
        raise HTTPException(status_code=404, detail="Session not found")
        
    except Exception as e:
        logger.error(f"Failed to get status for {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve status")


@app.get("/api/result/{session_id}")
async def get_processing_result(session_id: str):
    """Get comprehensive processing results from database."""
    
    try:
        # Get results from database
        results = await db_manager.get_session_results(session_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = results["session"]
        
        if session_data["status"] == "processing" or session_data["status"] == "pending":
            raise HTTPException(status_code=202, detail="Processing still in progress")
        
        if session_data["status"] == "failed":
            raise HTTPException(
                status_code=500, 
                detail=session_data.get("error_message", "Processing failed")
            )
        
        if session_data["status"] == "completed":
            # Format results for frontend compatibility
            formatted_results = {
                "filename": session_data["filename"],
                "systems_data": []
            }
            
            # Group data by system
            systems_by_id = {}
            for system in results["systems"]:
                systems_by_id[system["id"]] = {
                    "system": {
                        "machine_id": system["machine_id"],
                        "computer_name": system["computer_name"],
                        "hardware_id": system["hardware_id"],
                        "machine_user": system["machine_user"],
                        "ip_address": system["ip_address"],
                        "country": system["country"],
                        "log_date": system["log_date"]
                    },
                    "credentials": [],
                    "cookies": []
                }
            
            # Add credentials to systems
            for cred in results["credentials"]:
                if cred["system_id"] in systems_by_id:
                    systems_by_id[cred["system_id"]]["credentials"].append({
                        "software": cred["software"],
                        "host": cred["host"],
                        "domain": cred["domain"],
                        "username": cred["username"],
                        "password": "***HIDDEN***",  # Don't expose passwords
                        "email_domain": cred["email_domain"],
                        "local_part": cred["local_part"],
                        "filepath": cred["filepath"],
                        "stealer_name": cred["stealer_name"],
                        "risk_level": cred["risk_level"]
                    })
            
            # Add cookies to systems
            for cookie in results["cookies"]:
                if cookie["system_id"] in systems_by_id:
                    systems_by_id[cookie["system_id"]]["cookies"].append({
                        "domain": cookie["domain"],
                        "name": cookie["name"],
                        "value": "***HIDDEN***",  # Don't expose cookie values
                        "browser": cookie["browser"],
                        "secure": cookie["secure"],
                        "expiry": cookie["expiry"],
                        "filepath": cookie["filepath"],
                        "stealer_name": cookie["stealer_name"],
                        "risk_level": cookie["risk_level"]
                    })
            
            formatted_results["systems_data"] = list(systems_by_id.values())
            
            return JSONResponse(content=formatted_results)
        
        raise HTTPException(status_code=500, detail="Unknown session status")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve results")


@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """Get system-wide analytics and statistics."""
    
    try:
        analytics = await db_manager.get_analytics_summary(limit=50)
        return JSONResponse(content=analytics)
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


@app.get("/api/sessions")
async def list_recent_sessions(
    limit: int = Query(default=20, le=100),
    status: Optional[str] = Query(default=None)
):
    """List recent processing sessions with optional status filter."""
    
    try:
        async with db_manager.get_session() as session:
            query = """
                SELECT id, filename, file_size, upload_time, processing_start, 
                       processing_end, status, progress, total_systems, 
                       total_credentials, total_cookies
                FROM parse_sessions 
            """
            params = {}
            
            if status:
                query += " WHERE status = :status"
                params["status"] = status
            
            query += " ORDER BY upload_time DESC LIMIT :limit"
            params["limit"] = limit
            
            result = await session.execute(text(query), params)
            sessions = [dict(row._mapping) for row in result.fetchall()]
            
            return {"sessions": sessions}
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a processing session and all related data."""
    
    try:
        async with db_manager.get_session() as session:
            # Delete in order due to foreign key constraints
            await session.execute(
                text("DELETE FROM extracted_cookies WHERE session_id = :session_id"),
                {"session_id": session_id}
            )
            await session.execute(
                text("DELETE FROM extracted_credentials WHERE session_id = :session_id"),
                {"session_id": session_id}
            )
            await session.execute(
                text("DELETE FROM compromised_systems WHERE session_id = :session_id"),
                {"session_id": session_id}
            )
            await session.execute(
                text("DELETE FROM parse_sessions WHERE id = :session_id"),
                {"session_id": session_id}
            )
        
        return {"message": "Session deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@app.get("/api/export/{session_id}/csv")
async def export_session_csv(session_id: str):
    """Export session data as CSV file."""
    
    try:
        results = await db_manager.get_session_results(session_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate CSV content
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write credentials CSV
        writer.writerow([
            "Type", "Software", "Host", "Domain", "Username", "Risk Level", 
            "Stealer", "System", "Country", "IP Address"
        ])
        
        for cred in results["credentials"]:
            # Find matching system
            system = next(
                (s for s in results["systems"] if s["id"] == cred["system_id"]), 
                {}
            )
            
            writer.writerow([
                "Credential",
                cred.get("software", ""),
                cred.get("host", ""),
                cred.get("domain", ""),
                cred.get("username", ""),
                cred.get("risk_level", ""),
                cred.get("stealer_name", ""),
                system.get("computer_name", ""),
                system.get("country", ""),
                system.get("ip_address", "")
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        # Return as streaming response
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=stealer_data_{session_id}.csv"}
        )
        
    except Exception as e:
        logger.error(f"Failed to export CSV for {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )