"""
Asynchronous processing engine for stealer parser with Redis job queue.
Handles millions of records efficiently with background processing.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid

import redis.asyncio as redis
from rq import Worker, Queue, Connection
from rq.job import Job

# Import existing stealer parser modules
from stealer_parser.main import read_archive, process_archive
from stealer_parser.models import Leak
from stealer_parser.helpers import init_logger

from .database import db_manager, CompromisedSystem, ExtractedCredential, ExtractedCookie


class AsyncStealerProcessor:
    """High-performance async processor for stealer archives."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_pool = None
        self.logger = init_logger("AsyncStealerProcessor", 2)
        
    async def init_redis(self):
        """Initialize Redis connection pool."""
        self.redis_pool = redis.ConnectionPool.from_url(
            self.redis_url, 
            decode_responses=True,
            max_connections=50
        )
    
    async def queue_processing_job(
        self, 
        session_id: str, 
        file_path: str, 
        filename: str, 
        password: Optional[str] = None
    ) -> str:
        """Queue a file processing job for background execution."""
        
        # Create job data
        job_data = {
            "session_id": session_id,
            "file_path": file_path,
            "filename": filename,
            "password": password,
            "queued_at": datetime.utcnow().isoformat()
        }
        
        # Add to Redis queue
        async with redis.Redis(connection_pool=self.redis_pool) as r:
            await r.lpush("stealer_processing_queue", json.dumps(job_data))
            await r.set(f"job_status:{session_id}", json.dumps({
                "status": "queued",
                "progress": 0,
                "current_step": "Queued for processing",
                "queued_at": job_data["queued_at"]
            }))
        
        self.logger.info(f"Queued processing job for session {session_id}")
        return session_id
    
    async def process_archive_async(
        self, 
        session_id: str, 
        file_path: str, 
        filename: str, 
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Asynchronously process stealer archive with database storage.
        Optimized for handling large archives with millions of records.
        """
        start_time = time.time()
        
        try:
            # Update status to processing
            await self._update_job_status(
                session_id, 
                "processing", 
                5, 
                "Initializing processing"
            )
            
            # Initialize database session
            await db_manager.update_session_status(
                session_id=session_id,
                status="processing",
                progress=10,
                current_step="Reading archive"
            )
            
            # Read and process archive using existing parser
            self.logger.info(f"Processing archive: {filename}")
            
            leak = Leak(filename=filename)
            
            # Process archive in chunks for memory efficiency
            with open(file_path, "rb") as file_handle:
                with BytesIO(file_handle.read()) as buffer:
                    archive = read_archive(buffer, filename, password)
                    
                    await self._update_job_status(
                        session_id, 
                        "processing", 
                        20, 
                        "Extracting archive contents"
                    )
                    
                    # Process with enhanced logging and progress tracking
                    await self._process_archive_with_progress(
                        session_id, leak, archive
                    )
                    
                    archive.close()
            
            # Store results in database
            await self._store_results_in_database(session_id, leak)
            
            # Calculate processing statistics
            processing_time = time.time() - start_time
            
            # Update final status
            await db_manager.update_session_status(
                session_id=session_id,
                status="completed",
                progress=100,
                current_step="Processing complete"
            )
            
            await self._update_job_status(
                session_id, 
                "completed", 
                100, 
                "Processing complete",
                processing_time=processing_time
            )
            
            self.logger.info(
                f"Successfully processed {filename} in {processing_time:.2f}s"
            )
            
            return {
                "session_id": session_id,
                "status": "completed",
                "processing_time": processing_time,
                "systems_count": len(leak.systems_data),
                "total_credentials": sum(len(s.credentials) for s in leak.systems_data),
                "total_cookies": sum(len(s.cookies) for s in leak.systems_data)
            }
            
        except Exception as e:
            error_msg = f"Failed processing {filename}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            await db_manager.update_session_status(
                session_id=session_id,
                status="failed",
                error_message=error_msg
            )
            
            await self._update_job_status(
                session_id, 
                "failed", 
                0, 
                "Processing failed",
                error_message=error_msg
            )
            
            raise
        
        finally:
            # Clean up temporary file
            try:
                Path(file_path).unlink()
            except:
                pass
    
    async def _process_archive_with_progress(
        self, 
        session_id: str, 
        leak: Leak, 
        archive
    ):
        """Process archive with detailed progress tracking."""
        
        # Import processing modules
        from stealer_parser.processing import generate_file_list, process_system_dir
        
        await self._update_job_status(
            session_id, "processing", 30, "Scanning for log files"
        )
        
        # Generate file list
        files = generate_file_list(archive)
        total_files = len(files)
        
        if total_files == 0:
            await self._update_job_status(
                session_id, "processing", 40, "No log files found"
            )
            return
        
        self.logger.info(f"Found {total_files} files to process")
        
        # Process files in batches for better progress tracking
        batch_size = max(1, total_files // 10)  # 10% increments
        processed = 0
        
        index = 0
        while index < len(files):
            batch_end = min(index + batch_size, len(files))
            batch_files = files[index:batch_end]
            
            # Process batch
            processed_count = process_system_dir(
                self.logger, leak, archive, batch_files
            )
            
            processed += processed_count
            index = batch_end
            
            # Update progress
            progress = 30 + int((processed / total_files) * 50)  # 30-80%
            await self._update_job_status(
                session_id, 
                "processing", 
                progress, 
                f"Processed {processed}/{total_files} files"
            )
        
        await self._update_job_status(
            session_id, "processing", 85, "Storing results in database"
        )
    
    async def _store_results_in_database(self, session_id: str, leak: Leak):
        """Store processing results in database with bulk operations."""
        
        total_systems = len(leak.systems_data)
        total_credentials = 0
        total_cookies = 0
        
        # Process each system
        for system_data in leak.systems_data:
            # Store system info
            system_record = CompromisedSystem(
                session_id=session_id,
                machine_id=system_data.system.machine_id if system_data.system else None,
                computer_name=system_data.system.computer_name if system_data.system else None,
                hardware_id=system_data.system.hardware_id if system_data.system else None,
                machine_user=system_data.system.machine_user if system_data.system else None,
                ip_address=system_data.system.ip_address if system_data.system else None,
                country=system_data.system.country if system_data.system else None,
                log_date=self._parse_datetime(
                    system_data.system.log_date if system_data.system else None
                ),
                stealer_name=self._get_stealer_name(system_data)
            )
            
            # Store system in database and get ID
            async with db_manager.get_session() as session:
                session.add(system_record)
                await session.flush()
                system_id = system_record.id
            
            # Bulk insert credentials
            if system_data.credentials:
                credential_dicts = [
                    self._credential_to_dict(cred) for cred in system_data.credentials
                ]
                await db_manager.bulk_insert_credentials(
                    session_id, system_id, credential_dicts
                )
                total_credentials += len(system_data.credentials)
            
            # Bulk insert cookies
            if system_data.cookies:
                cookie_dicts = [
                    self._cookie_to_dict(cookie) for cookie in system_data.cookies
                ]
                await db_manager.bulk_insert_cookies(
                    session_id, system_id, cookie_dicts
                )
                total_cookies += len(system_data.cookies)
        
        # Update session totals
        await db_manager.update_session_status(
            session_id=session_id,
            status="processing",
            progress=95,
            current_step="Finalizing database storage"
        )
        
        # Update session record with totals
        from sqlalchemy.sql import text
        async with db_manager.get_session() as session:
            await session.execute(
                text("UPDATE parse_sessions SET total_systems = :total_systems, "
                     "total_credentials = :total_credentials, total_cookies = :total_cookies "
                     "WHERE id = :session_id"),
                {
                    "total_systems": total_systems,
                    "total_credentials": total_credentials,
                    "total_cookies": total_cookies,
                    "session_id": session_id
                }
            )
        
        self.logger.info(
            f"Stored {total_systems} systems, {total_credentials} credentials, "
            f"{total_cookies} cookies for session {session_id}"
        )
    
    async def _update_job_status(
        self, 
        session_id: str, 
        status: str, 
        progress: int, 
        current_step: str,
        processing_time: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Update job status in Redis."""
        
        status_data = {
            "status": status,
            "progress": progress,
            "current_step": current_step,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if processing_time:
            status_data["processing_time"] = processing_time
        
        if error_message:
            status_data["error_message"] = error_message
        
        async with redis.Redis(connection_pool=self.redis_pool) as r:
            await r.set(
                f"job_status:{session_id}", 
                json.dumps(status_data),
                ex=3600  # Expire after 1 hour
            )
    
    async def get_job_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current job status from Redis."""
        
        async with redis.Redis(connection_pool=self.redis_pool) as r:
            status_data = await r.get(f"job_status:{session_id}")
            
            if status_data:
                return json.loads(status_data)
            
            return None
    
    def _credential_to_dict(self, credential) -> Dict[str, Any]:
        """Convert credential object to dictionary."""
        return {
            "software": credential.software,
            "host": credential.host,
            "domain": credential.domain,
            "username": credential.username,
            "password": credential.password,
            "email_domain": credential.email_domain,
            "local_part": credential.local_part,
            "filepath": credential.filepath,
            "stealer_name": credential.stealer_name
        }
    
    def _cookie_to_dict(self, cookie) -> Dict[str, Any]:
        """Convert cookie object to dictionary."""
        return {
            "domain": cookie.domain,
            "name": cookie.name,
            "value": cookie.value,
            "browser": cookie.browser,
            "secure": cookie.secure,
            "http_only": getattr(cookie, "http_only", False),
            "expiry": cookie.expiry,
            "filepath": cookie.filepath,
            "stealer_name": cookie.stealer_name
        }
    
    def _parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """Parse datetime string safely."""
        if not dt_string:
            return None
        
        try:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            return None
    
    def _get_stealer_name(self, system_data) -> Optional[str]:
        """Extract stealer name from system data."""
        if system_data.credentials:
            for cred in system_data.credentials:
                if cred.stealer_name:
                    return cred.stealer_name
        
        if system_data.cookies:
            for cookie in system_data.cookies:
                if cookie.stealer_name:
                    return cookie.stealer_name
        
        return None


class BackgroundWorker:
    """Background worker for processing queued jobs."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.processor = AsyncStealerProcessor(redis_url)
        self.logger = init_logger("BackgroundWorker", 2)
        self.running = False
    
    async def start_worker(self):
        """Start the background worker to process jobs."""
        await self.processor.init_redis()
        await db_manager.init_database()
        
        self.running = True
        self.logger.info("Background worker started")
        
        async with redis.Redis.from_url(self.redis_url, decode_responses=True) as r:
            while self.running:
                try:
                    # Wait for job from queue (blocking pop with timeout)
                    result = await r.brpop("stealer_processing_queue", timeout=5)
                    
                    if result:
                        queue_name, job_data = result
                        job_info = json.loads(job_data)
                        
                        self.logger.info(f"Processing job: {job_info['session_id']}")
                        
                        # Process the job
                        await self.processor.process_archive_async(
                            session_id=job_info["session_id"],
                            file_path=job_info["file_path"],
                            filename=job_info["filename"],
                            password=job_info.get("password")
                        )
                        
                except asyncio.CancelledError:
                    self.logger.info("Worker cancelled")
                    break
                except Exception as e:
                    self.logger.error(f"Worker error: {e}", exc_info=True)
                    await asyncio.sleep(5)  # Wait before retrying
    
    def stop_worker(self):
        """Stop the background worker."""
        self.running = False
        self.logger.info("Background worker stopped")


# Global processor instance
async_processor = AsyncStealerProcessor()