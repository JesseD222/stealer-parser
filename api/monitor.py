#!/usr/bin/env python3
"""
Performance monitoring and metrics collection for the stealer parser API.
Provides real-time insights into processing performance and system health.
"""
import asyncio
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api.database import db_manager
from stealer_parser.helpers import init_logger
from sqlalchemy.sql import text


class PerformanceMonitor:
    """Real-time performance monitoring system."""
    
    def __init__(self, monitor_interval: int = 60):
        self.monitor_interval = monitor_interval
        self.logger = init_logger("PerformanceMonitor", 2)
        self.metrics_history = []
        
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics."""
        
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network (if available)
        try:
            network = psutil.net_io_counters()
            network_stats = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        except:
            network_stats = {}
        
        return {
            "timestamp": datetime.utcnow(),
            "cpu_percent": cpu_percent,
            "memory_total": memory.total,
            "memory_used": memory.used,
            "memory_percent": memory.percent,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "disk_percent": (disk.used / disk.total) * 100,
            "network": network_stats
        }
    
    async def collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database performance metrics."""
        
        try:
            async with db_manager.get_session() as session:
                # Session statistics
                session_stats = await session.execute(text("""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        AVG(CASE 
                            WHEN processing_end IS NOT NULL AND processing_start IS NOT NULL 
                            THEN (julianday(processing_end) - julianday(processing_start)) * 24 * 3600 
                        END) as avg_processing_time,
                        AVG(total_credentials) as avg_credentials,
                        AVG(total_cookies) as avg_cookies,
                        AVG(file_size) as avg_file_size
                    FROM parse_sessions 
                    WHERE upload_time > datetime('now', '-24 hours')
                    GROUP BY status
                """))
                
                status_metrics = {}
                for row in session_stats:
                    status_metrics[row.status] = {
                        "count": row.count,
                        "avg_processing_time": row.avg_processing_time or 0,
                        "avg_credentials": row.avg_credentials or 0,
                        "avg_cookies": row.avg_cookies or 0,
                        "avg_file_size": row.avg_file_size or 0
                    }
                
                # Total counts
                total_stats = await session.execute(text("""
                    SELECT 
                        COUNT(DISTINCT ps.id) as total_sessions,
                        COUNT(DISTINCT cs.id) as total_systems,
                        COUNT(DISTINCT ec.id) as total_credentials,
                        COUNT(DISTINCT eck.id) as total_cookies
                    FROM parse_sessions ps
                    LEFT JOIN compromised_systems cs ON ps.id = cs.session_id
                    LEFT JOIN extracted_credentials ec ON ps.id = ec.session_id
                    LEFT JOIN extracted_cookies eck ON ps.id = eck.session_id
                """))
                
                totals = total_stats.fetchone()
                
                # Recent activity (last hour)
                recent_activity = await session.execute(text("""
                    SELECT COUNT(*) as recent_sessions
                    FROM parse_sessions 
                    WHERE upload_time > datetime('now', '-1 hour')
                """))
                
                recent_count = recent_activity.scalar()
                
                return {
                    "status_breakdown": status_metrics,
                    "totals": {
                        "sessions": totals.total_sessions,
                        "systems": totals.total_systems,
                        "credentials": totals.total_credentials,
                        "cookies": totals.total_cookies
                    },
                    "recent_activity": {
                        "last_hour_sessions": recent_count
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to collect database metrics: {e}")
            return {"error": str(e)}
    
    async def collect_processing_queue_metrics(self) -> Dict[str, Any]:
        """Collect Redis queue and processing metrics."""
        
        try:
            from api.async_processor import async_processor
            
            # This would connect to Redis to get queue statistics
            # For demo, we'll return simulated metrics
            return {
                "queue_length": 0,  # Would get from Redis LLEN
                "active_workers": 2,  # Would get from Redis or worker registry
                "processed_today": 0,  # Would get from Redis counters
                "avg_job_time": 0,  # Would calculate from completed jobs
                "failed_jobs_today": 0  # Would get from failed job counter
            }
            
        except Exception as e:
            self.logger.error(f"Failed to collect queue metrics: {e}")
            return {"error": str(e)}
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        
        system_metrics = await self.collect_system_metrics()
        database_metrics = await self.collect_database_metrics()
        queue_metrics = await self.collect_processing_queue_metrics()
        
        # Calculate performance scores
        performance_score = self.calculate_performance_score(
            system_metrics, database_metrics, queue_metrics
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "performance_score": performance_score,
            "system": system_metrics,
            "database": database_metrics,
            "processing_queue": queue_metrics,
            "recommendations": self.generate_recommendations(
                system_metrics, database_metrics, queue_metrics
            )
        }
    
    def calculate_performance_score(
        self, 
        system_metrics: Dict, 
        database_metrics: Dict, 
        queue_metrics: Dict
    ) -> Dict[str, Any]:
        """Calculate overall performance score (0-100)."""
        
        scores = []
        
        # System performance score
        if system_metrics.get("cpu_percent", 0) < 80:
            scores.append(90)
        elif system_metrics.get("cpu_percent", 0) < 90:
            scores.append(70)
        else:
            scores.append(40)
        
        # Memory performance score  
        memory_percent = system_metrics.get("memory_percent", 0)
        if memory_percent < 70:
            scores.append(90)
        elif memory_percent < 85:
            scores.append(70)
        else:
            scores.append(40)
        
        # Database performance score
        if "error" not in database_metrics:
            # Check for failed sessions
            failed_sessions = database_metrics.get("status_breakdown", {}).get("failed", {}).get("count", 0)
            total_sessions = sum(
                status.get("count", 0) 
                for status in database_metrics.get("status_breakdown", {}).values()
            )
            
            if total_sessions > 0:
                failure_rate = failed_sessions / total_sessions
                if failure_rate < 0.05:  # Less than 5% failure
                    scores.append(90)
                elif failure_rate < 0.15:  # Less than 15% failure
                    scores.append(70)
                else:
                    scores.append(40)
            else:
                scores.append(80)  # No data yet
        else:
            scores.append(30)  # Database issues
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        return {
            "overall": round(overall_score, 1),
            "system": scores[0] if len(scores) > 0 else 0,
            "memory": scores[1] if len(scores) > 1 else 0,
            "database": scores[2] if len(scores) > 2 else 0,
            "status": "excellent" if overall_score >= 85 else 
                     "good" if overall_score >= 70 else
                     "fair" if overall_score >= 50 else "poor"
        }
    
    def generate_recommendations(
        self, 
        system_metrics: Dict, 
        database_metrics: Dict, 
        queue_metrics: Dict
    ) -> List[str]:
        """Generate performance improvement recommendations."""
        
        recommendations = []
        
        # System recommendations
        if system_metrics.get("cpu_percent", 0) > 85:
            recommendations.append("High CPU usage detected. Consider scaling horizontally or optimizing processing algorithms.")
        
        if system_metrics.get("memory_percent", 0) > 85:
            recommendations.append("High memory usage detected. Consider increasing memory or implementing batch processing.")
        
        if system_metrics.get("disk_percent", 0) > 90:
            recommendations.append("Low disk space. Clean up temporary files and old session data.")
        
        # Database recommendations
        if "status_breakdown" in database_metrics:
            failed_count = database_metrics["status_breakdown"].get("failed", {}).get("count", 0)
            if failed_count > 10:
                recommendations.append("High number of failed processing sessions. Check error logs and archive quality.")
        
        # Processing recommendations
        if database_metrics.get("recent_activity", {}).get("last_hour_sessions", 0) > 50:
            recommendations.append("High processing volume. Consider adding more worker processes.")
        
        if not recommendations:
            recommendations.append("System performance is optimal. Continue monitoring.")
        
        return recommendations
    
    async def start_monitoring(self):
        """Start continuous performance monitoring."""
        
        self.logger.info(f"Starting performance monitor (interval: {self.monitor_interval}s)")
        
        try:
            await db_manager.init_database()
            
            while True:
                try:
                    report = await self.generate_performance_report()
                    self.metrics_history.append(report)
                    
                    # Keep only last 24 hours of metrics
                    cutoff_time = datetime.utcnow() - timedelta(hours=24)
                    self.metrics_history = [
                        m for m in self.metrics_history 
                        if datetime.fromisoformat(m["timestamp"]) > cutoff_time
                    ]
                    
                    # Log summary
                    score = report["performance_score"]["overall"]
                    status = report["performance_score"]["status"]
                    
                    self.logger.info(
                        f"Performance Score: {score}/100 ({status.upper()}) - "
                        f"CPU: {report['system']['cpu_percent']:.1f}% - "
                        f"Memory: {report['system']['memory_percent']:.1f}% - "
                        f"Sessions: {report['database']['totals']['sessions']:,}"
                    )
                    
                    # Print recommendations if any issues
                    if score < 70:
                        for rec in report["recommendations"]:
                            self.logger.warning(f"RECOMMENDATION: {rec}")
                    
                except Exception as e:
                    self.logger.error(f"Monitoring cycle failed: {e}")
                
                await asyncio.sleep(self.monitor_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring failed: {e}")
        finally:
            await db_manager.close()
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return await self.generate_performance_report()


async def main():
    """Main entry point for performance monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Stealer Parser Performance Monitor")
    parser.add_argument(
        "--interval", 
        type=int, 
        default=60, 
        help="Monitoring interval in seconds"
    )
    parser.add_argument(
        "--once", 
        action="store_true", 
        help="Run once and show current metrics"
    )
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(args.interval)
    
    if args.once:
        # Show current metrics once
        await db_manager.init_database()
        report = await monitor.generate_performance_report()
        
        print("\n=== Performance Report ===")
        print(f"Timestamp: {report['timestamp']}")
        print(f"Overall Score: {report['performance_score']['overall']}/100 ({report['performance_score']['status'].upper()})")
        
        print(f"\n=== System Metrics ===")
        sys_metrics = report['system']
        print(f"CPU Usage: {sys_metrics['cpu_percent']:.1f}%")
        print(f"Memory Usage: {sys_metrics['memory_percent']:.1f}% ({sys_metrics['memory_used']:,} / {sys_metrics['memory_total']:,} bytes)")
        print(f"Disk Usage: {sys_metrics['disk_percent']:.1f}%")
        
        print(f"\n=== Database Metrics ===")
        db_metrics = report['database']
        if 'totals' in db_metrics:
            totals = db_metrics['totals']
            print(f"Total Sessions: {totals['sessions']:,}")
            print(f"Total Systems: {totals['systems']:,}")  
            print(f"Total Credentials: {totals['credentials']:,}")
            print(f"Total Cookies: {totals['cookies']:,}")
        
        print(f"\n=== Recommendations ===")
        for rec in report['recommendations']:
            print(f"• {rec}")
        
        await db_manager.close()
    else:
        # Start continuous monitoring
        print(f"Starting performance monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop")
        await monitor.start_monitoring()


if __name__ == "__main__":
    asyncio.run(main())