"""
Valkey (Redis-compatible) Job Store for FAL Gateway

Implements async Redis client with:
- Correction #2: redis.asyncio for non-blocking operations
- Correction #6: TTL refresh on every update
- Correction #3: TTL-only locks (no explicit release for simplicity)
"""

import os
import json
import uuid
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from redis.asyncio import Redis
from app.logger import log_error


# Environment configuration
VALKEY_URL = os.getenv("VALKEY_URL", "redis://localhost:6379/0")
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))  # 1 hour default


class ValkeyJobStore:
    """
    Async Valkey client for job state management.
    Uses Redis HASH for structured storage with TTL.
    """
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.ttl = JOB_TTL_SECONDS
    
    async def connect(self):
        """Initialize async Redis connection"""
        if not self.redis:
            self.redis = await Redis.from_url(
                VALKEY_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
    
    async def health_check(self) -> bool:
        """Check if Valkey is accessible"""
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
    
    def _job_key(self, job_id: str) -> str:
        """Generate Redis key for job"""
        return f"ms:job:{job_id}"
    
    def _lock_key(self, job_id: str) -> str:
        """Generate Redis key for job lock"""
        return f"ms:lock:{job_id}"
    
    async def create_job(
        self,
        job_id: str,
        provider: str,
        media_type: str,
        model: str,
        payload: Dict[str, Any],
        estimate: Dict[str, Any]
    ) -> bool:
        """
        Create a new job in Valkey.
        Returns True if successful.
        """
        try:
            key = self._job_key(job_id)
            now = datetime.now(timezone.utc).isoformat()
            
            job_data = {
                "status": "queued",
                "stage": "validated",
                "stage_history_json": json.dumps(["validated"]),
                "provider": provider,
                "media_type": media_type,
                "model": model,
                "payload_json": json.dumps(payload),
                "estimate_json": json.dumps(estimate),
                "provider_request_id": "",  # Set when submitted to provider
                "result_json": "",
                "destination_json": "",
                "transform_trace_json": "",
                "error": "",
                "created_at": now,
                "updated_at": now
            }
            
            # Store as Redis HASH
            await self.redis.hset(key, mapping=job_data)
            
            # Set TTL (Correction #6: refresh on every update)
            await self.redis.expire(key, self.ttl)
            
            return True
        
        except Exception as e:
            log_error(f"valkey_create_{job_id}", f"Failed to create job: {str(e)}")
            return False
    
    async def update_job(
        self,
        job_id: str,
        **fields
    ) -> bool:
        """
        Update job fields in Valkey.
        Automatically refreshes TTL on update (Correction #6).
        """
        try:
            key = self._job_key(job_id)
            
            # Add updated_at timestamp
            fields["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Convert complex objects to JSON strings
            for field_name, field_value in fields.items():
                if field_name.endswith("_json") and isinstance(field_value, (dict, list)):
                    fields[field_name] = json.dumps(field_value)
            
            # Update fields
            await self.redis.hset(key, mapping=fields)
            
            # Refresh TTL (Correction #6)
            await self.redis.expire(key, self.ttl)
            
            return True
        
        except Exception as e:
            log_error(f"valkey_update_{job_id}", f"Failed to update job: {str(e)}")
            return False
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve job from Valkey.
        Returns None if job not found.
        """
        try:
            key = self._job_key(job_id)
            job_data = await self.redis.hgetall(key)
            
            if not job_data:
                return None
            
            # Parse JSON fields
            if job_data.get("payload_json"):
                try:
                    job_data["payload"] = json.loads(job_data["payload_json"])
                except json.JSONDecodeError:
                    job_data["payload"] = {}
            
            if job_data.get("estimate_json"):
                try:
                    job_data["estimate"] = json.loads(job_data["estimate_json"])
                except json.JSONDecodeError:
                    job_data["estimate"] = {}
            
            if job_data.get("result_json"):
                try:
                    job_data["result"] = json.loads(job_data["result_json"])
                except json.JSONDecodeError:
                    job_data["result"] = None

            if job_data.get("stage_history_json"):
                try:
                    job_data["stage_history"] = json.loads(job_data["stage_history_json"])
                except json.JSONDecodeError:
                    job_data["stage_history"] = []

            if job_data.get("destination_json"):
                try:
                    job_data["destination"] = json.loads(job_data["destination_json"])
                except json.JSONDecodeError:
                    job_data["destination"] = {}

            if job_data.get("transform_trace_json"):
                try:
                    job_data["transform_trace"] = json.loads(job_data["transform_trace_json"])
                except json.JSONDecodeError:
                    job_data["transform_trace"] = {}
            
            return job_data
        
        except Exception as e:
            log_error(f"valkey_get_{job_id}", f"Failed to get job: {str(e)}")
            return None
    
    async def acquire_lock(self, job_id: str, timeout_seconds: int = 10) -> bool:
        """
        Acquire a TTL-only lock for job processing.
        Correction #3: No explicit release, relies on TTL expiry.
        
        Returns True if lock acquired, False if already locked.
        """
        try:
            key = self._lock_key(job_id)
            lock_token = str(uuid.uuid4())  # For future use if needed
            
            # SET key value NX EX timeout
            result = await self.redis.set(
                key,
                lock_token,
                nx=True,  # Only set if not exists
                ex=timeout_seconds  # Expiry time
            )
            
            return result is not None
        
        except Exception as e:
            log_error(f"valkey_lock_{job_id}", f"Failed to acquire lock: {str(e)}")
            return False
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete job from Valkey (cleanup)"""
        try:
            key = self._job_key(job_id)
            await self.redis.delete(key)
            return True
        except Exception:
            return False


# Singleton instance
_valkey_store: Optional[ValkeyJobStore] = None


async def get_valkey_store() -> ValkeyJobStore:
    """Get or create Valkey store singleton"""
    global _valkey_store
    if _valkey_store is None:
        _valkey_store = ValkeyJobStore()
        await _valkey_store.connect()
    return _valkey_store
