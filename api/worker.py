#!/usr/bin/env python3
"""
Background worker script for processing stealer archives.
Runs independently to handle job queue processing.
"""
import asyncio
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api.async_processor import BackgroundWorker
from api.database import db_manager
from stealer_parser.helpers import init_logger


class WorkerManager:
    """Manages multiple background workers for high throughput."""
    
    def __init__(self, num_workers: int = 2, redis_url: str = "redis://localhost:6379"):
        self.num_workers = num_workers
        self.redis_url = redis_url
        self.workers = []
        self.logger = init_logger("WorkerManager", 2)
        self.running = False
    
    async def start_workers(self):
        """Start multiple background workers."""
        self.running = True
        
        # Initialize database
        await db_manager.init_database()
        self.logger.info("Database initialized for workers")
        
        # Create and start workers
        for i in range(self.num_workers):
            worker = BackgroundWorker(self.redis_url)
            self.workers.append(worker)
            
            # Start each worker in a separate task
            asyncio.create_task(
                self._run_worker(worker, i),
                name=f"worker-{i}"
            )
        
        self.logger.info(f"Started {self.num_workers} background workers")
        
        # Keep the main process alive
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
            await self.stop_workers()
    
    async def _run_worker(self, worker: BackgroundWorker, worker_id: int):
        """Run a single worker with error recovery."""
        self.logger.info(f"Starting worker {worker_id}")
        
        while self.running:
            try:
                await worker.start_worker()
            except Exception as e:
                self.logger.error(f"Worker {worker_id} failed: {e}")
                if self.running:
                    self.logger.info(f"Restarting worker {worker_id} in 5 seconds")
                    await asyncio.sleep(5)
                else:
                    break
    
    async def stop_workers(self):
        """Stop all background workers gracefully."""
        self.running = False
        
        for worker in self.workers:
            worker.stop_worker()
        
        await db_manager.close()
        self.logger.info("All workers stopped")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for worker process."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Stealer Parser Background Workers")
    parser.add_argument(
        "--workers", 
        type=int, 
        default=2, 
        help="Number of worker processes"
    )
    parser.add_argument(
        "--redis-url", 
        default="redis://localhost:6379", 
        help="Redis connection URL"
    )
    
    args = parser.parse_args()
    
    # Create and start worker manager
    manager = WorkerManager(args.workers, args.redis_url)
    manager.setup_signal_handlers()
    
    print(f"Starting {args.workers} stealer parser workers...")
    print(f"Redis URL: {args.redis_url}")
    print("Press Ctrl+C to stop")
    
    try:
        await manager.start_workers()
    except KeyboardInterrupt:
        print("\nShutdown initiated...")
    finally:
        await manager.stop_workers()
        print("Workers stopped")


if __name__ == "__main__":
    asyncio.run(main())