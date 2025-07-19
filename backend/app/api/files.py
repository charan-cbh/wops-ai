from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import aiofiles
import os
import hashlib
import pandas as pd
from pathlib import Path
from ..core.config import settings
from ..services.file_service import file_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    content_type: str
    processed: bool
    extracted_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class FileListResponse(BaseModel):
    files: List[Dict[str, Any]]
    total: int

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    context: Optional[str] = Form(None)
):
    """Upload a file for context processing"""
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.allowed_file_types_list:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_extension} not allowed. Allowed types: {settings.allowed_file_types_list}"
            )
        
        # Validate file size
        file_content = await file.read()
        if len(file_content) > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
            )
        
        # Process the file
        result = await file_service.process_uploaded_file(
            filename=file.filename,
            content=file_content,
            content_type=file.content_type,
            context=context
        )
        
        return FileUploadResponse(
            file_id=result["file_id"],
            filename=result["filename"],
            size=result["size"],
            content_type=result["content_type"],
            processed=result["processed"],
            extracted_text=result.get("extracted_text"),
            metadata=result.get("metadata")
        )
        
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=FileListResponse)
async def list_files(skip: int = 0, limit: int = 50):
    """List uploaded files"""
    try:
        files = await file_service.list_files(skip=skip, limit=limit)
        total = await file_service.count_files()
        
        return FileListResponse(files=files, total=total)
        
    except Exception as e:
        logger.error(f"File listing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{file_id}")
async def get_file(file_id: str):
    """Get file details and content"""
    try:
        file_info = await file_service.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        return file_info
        
    except Exception as e:
        logger.error(f"File retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """Delete a file"""
    try:
        success = await file_service.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"message": "File deleted successfully"}
        
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{file_id}/process")
async def process_file(file_id: str, context: Optional[Dict[str, Any]] = None):
    """Process a file with additional context"""
    try:
        result = await file_service.reprocess_file(file_id, context)
        return result
        
    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))