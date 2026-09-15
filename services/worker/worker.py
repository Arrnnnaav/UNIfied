"""Redis-backed ingestion worker. Heavy parsing/chunking/embedding never runs in HTTP."""
from __future__ import annotations
import json, os, time
from typing import Any
try:
    import redis
except ModuleNotFoundError:  # local parsing tests can run without queue dependencies installed
    redis = None
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import make_engine
from app.core.ingestion import chunk_document, content_hash, parse_document
from app.core.models import IngestionJob, Resource, ResourceChunk, ResourceDocument
from app.core.storage import get_bytes
from app.core.web_ingestion import fetch_github_text, fetch_web_text, fetch_youtube_transcript
QUEUE=os.getenv("REDIS_QUEUE","learning-platform:jobs")
def enqueue(kind:str,payload:dict[str,Any])->str:
    if redis is None: raise RuntimeError("redis package is required to enqueue jobs")
    job={"id":f"{kind}-{time.time_ns()}","kind":kind,"payload":payload,"queued_at":time.time()}
    redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379/0")).rpush(QUEUE,json.dumps(job))
    return job["id"]
def process_job(message:dict[str,Any])->None:
    engine=make_engine(get_settings().database_url)
    with Session(engine) as db:
        record=db.get(IngestionJob, message["id"])
        if not record: return
        try:
            record.status="processing"; record.progress=10; db.commit()
            payload=message["payload"]; resource=db.get(Resource,record.resource_id); filename=payload.get("filename", resource.title)
            if message.get("kind") == "ingest_url":
                text=fetch_web_text(resource.url)
                if not text: raise ValueError("no readable text found")
                parsed=type("Parsed", (), {"filename": resource.title, "content": text, "pages": (text,)})()
            elif message.get("kind") == "ingest_github":
                text=fetch_github_text(resource.url)
                if not text: raise ValueError("repository README is empty")
                parsed=type("Parsed", (), {"filename": resource.title, "content": text, "pages": (text,)})()
            elif message.get("kind") == "ingest_youtube":
                text=fetch_youtube_transcript(resource.url)
                parsed=type("Parsed", (), {"filename": resource.title, "content": text, "pages": (text,)})()
            else:
                parsed=parse_document(filename,get_bytes(payload["storage_key"]))
            record.progress=45; db.commit()
            resource.content=parsed.content; resource.status="ready"
            digest=content_hash(parsed.content)
            existing_global=db.query(ResourceDocument).join(Resource).filter(Resource.goal_id == resource.goal_id, ResourceDocument.content_hash == digest, ResourceDocument.resource_id != resource.id).first()
            if existing_global:
                resource.status="duplicate"; record.status="completed"; record.progress=100; record.error=f"duplicate_of:{existing_global.resource_id}"; db.commit()
                print(json.dumps({"event":"job_completed","job_id":message["id"],"deduplicated":True,"duplicate_of":str(existing_global.resource_id)}),flush=True)
                return
            document=db.query(ResourceDocument).filter(ResourceDocument.resource_id == resource.id, ResourceDocument.content_hash == digest).first()
            if document and document.status == "ready":
                record.status="completed"; record.progress=100; record.error=""; db.commit()
                print(json.dumps({"event":"job_completed","job_id":message["id"],"deduplicated":True}),flush=True)
                return
            document=ResourceDocument(resource_id=resource.id,filename=filename,content_hash=digest,word_count=len(parsed.content.split()),status="processing")
            db.add(document); db.flush()
            for item in chunk_document(parsed): db.add(ResourceChunk(document_id=document.id,**item))
            document.status="ready"; record.status="completed"; record.progress=100; record.error=""; db.commit()
            print(json.dumps({"event":"job_completed","job_id":message["id"]}),flush=True)
        except Exception as exc:
            resource = db.get(Resource, record.resource_id)
            if resource:
                resource.status = "failed"
            record.status="failed"; record.error=str(exc)[:1000]; db.commit()
            print(json.dumps({"event":"job_failed","job_id":message["id"],"error":record.error}),flush=True)
def run_forever()->None:
    if redis is None: raise RuntimeError("redis package is required to run the worker")
    client=redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379/0"))
    while True:
        _,raw=client.blpop(QUEUE,timeout=5) or (None,None)
        if raw: process_job(json.loads(raw))
if __name__=="__main__": run_forever()
