import aiofiles
import hashlib
import json
import os
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
        
        # File metadata storage (in production, use a database)
        self.metadata_dir = Path("metadata")
        self.metadata_dir.mkdir(exist_ok=True)
    
    async def process_uploaded_file(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an uploaded file and extract relevant information"""
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Create file hash for deduplication
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Save file to disk
        file_path = self.upload_dir / f"{file_id}_{filename}"
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        # Extract text content based on file type
        extracted_text = await self._extract_text_content(file_path, content_type)
        
        # Create metadata
        metadata = {
            "file_id": file_id,
            "filename": filename,
            "original_filename": filename,
            "content_type": content_type,
            "size": len(content),
            "hash": file_hash,
            "upload_time": datetime.now().isoformat(),
            "file_path": str(file_path),
            "context": context,
            "extracted_text": extracted_text,
            "processed": True
        }
        
        # Save metadata
        await self._save_metadata(file_id, metadata)
        
        return metadata
    
    async def _extract_text_content(self, file_path: Path, content_type: str) -> Optional[str]:
        """Extract text content from uploaded file"""
        try:
            file_extension = file_path.suffix.lower()
            
            if file_extension == ".txt":
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    return await f.read()
            
            elif file_extension == ".csv":
                df = pd.read_csv(file_path)
                # Return first few rows as text representation
                return df.head(10).to_string()
            
            elif file_extension == ".json":
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)
                    return json.dumps(data, indent=2)
            
            elif file_extension == ".xlsx":
                df = pd.read_excel(file_path)
                # Return first few rows as text representation
                return df.head(10).to_string()
            
            elif file_extension == ".pdf":
                # For PDF processing, you'd need a library like PyPDF2 or pdfplumber
                # For now, return a placeholder
                return "PDF content extraction not yet implemented"
            
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return None
    
    async def _save_metadata(self, file_id: str, metadata: Dict[str, Any]):
        """Save file metadata to storage"""
        metadata_path = self.metadata_dir / f"{file_id}.json"
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata, indent=2))
    
    async def _load_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Load file metadata from storage"""
        metadata_path = self.metadata_dir / f"{file_id}.json"
        try:
            async with aiofiles.open(metadata_path, "r") as f:
                content = await f.read()
                return json.loads(content)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error loading metadata for {file_id}: {str(e)}")
            return None
    
    async def list_files(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List uploaded files with metadata"""
        files = []
        metadata_files = list(self.metadata_dir.glob("*.json"))
        
        # Sort by creation time (newest first)
        metadata_files.sort(key=lambda x: x.stat().st_ctime, reverse=True)
        
        for metadata_file in metadata_files[skip:skip+limit]:
            file_id = metadata_file.stem
            metadata = await self._load_metadata(file_id)
            if metadata:
                # Return summary info (not full content)
                files.append({
                    "file_id": metadata["file_id"],
                    "filename": metadata["filename"],
                    "content_type": metadata["content_type"],
                    "size": metadata["size"],
                    "upload_time": metadata["upload_time"],
                    "processed": metadata["processed"],
                    "has_text": bool(metadata.get("extracted_text"))
                })
        
        return files
    
    async def count_files(self) -> int:
        """Count total number of uploaded files"""
        return len(list(self.metadata_dir.glob("*.json")))
    
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed file information"""
        return await self._load_metadata(file_id)
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file and its metadata"""
        try:
            metadata = await self._load_metadata(file_id)
            if not metadata:
                return False
            
            # Delete file from disk
            file_path = Path(metadata["file_path"])
            if file_path.exists():
                file_path.unlink()
            
            # Delete metadata
            metadata_path = self.metadata_dir / f"{file_id}.json"
            if metadata_path.exists():
                metadata_path.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            return False
    
    async def reprocess_file(self, file_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Reprocess a file with additional context"""
        metadata = await self._load_metadata(file_id)
        if not metadata:
            raise ValueError(f"File {file_id} not found")
        
        # Update context if provided
        if context:
            metadata["context"] = context
            metadata["reprocessed_time"] = datetime.now().isoformat()
        
        # Re-extract text if needed
        file_path = Path(metadata["file_path"])
        if file_path.exists():
            extracted_text = await self._extract_text_content(file_path, metadata["content_type"])
            metadata["extracted_text"] = extracted_text
        
        # Save updated metadata
        await self._save_metadata(file_id, metadata)
        
        return metadata
    
    async def get_file_content_for_context(self, file_id: str) -> Optional[str]:
        """Get file content for use as context in AI queries"""
        metadata = await self._load_metadata(file_id)
        if not metadata:
            return None
        
        extracted_text = metadata.get("extracted_text")
        if extracted_text:
            return f"File: {metadata['filename']}\nContent:\n{extracted_text}"
        
        return None
    
    async def search_files(self, query: str) -> List[Dict[str, Any]]:
        """Search files by content or filename"""
        results = []
        metadata_files = list(self.metadata_dir.glob("*.json"))
        
        for metadata_file in metadata_files:
            file_id = metadata_file.stem
            metadata = await self._load_metadata(file_id)
            if metadata:
                # Search in filename
                if query.lower() in metadata["filename"].lower():
                    results.append(metadata)
                # Search in extracted text
                elif metadata.get("extracted_text") and query.lower() in metadata["extracted_text"].lower():
                    results.append(metadata)
        
        return results

# Global instance
file_service = FileService()