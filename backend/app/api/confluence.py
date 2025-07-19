from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..services.confluence_service import confluence_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ConfluenceSearchRequest(BaseModel):
    query: str
    limit: int = 10
    space_key: Optional[str] = None

class ConfluenceSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int

class ConfluenceSpaceResponse(BaseModel):
    spaces: List[Dict[str, Any]]

class ConfluencePageResponse(BaseModel):
    page: Dict[str, Any]

@router.get("/status")
async def get_confluence_status():
    """Check Confluence connection status"""
    try:
        test_result = await confluence_service.test_connection()
        return test_result
    except Exception as e:
        logger.error(f"Confluence status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=ConfluenceSearchResponse)
async def search_confluence(request: ConfluenceSearchRequest):
    """Search Confluence content"""
    try:
        if not await confluence_service.is_configured():
            raise HTTPException(status_code=400, detail="Confluence not configured")
        
        results = await confluence_service.search_content(
            query=request.query,
            limit=request.limit,
            space_key=request.space_key
        )
        
        return ConfluenceSearchResponse(
            results=results,
            total=len(results)
        )
        
    except Exception as e:
        logger.error(f"Confluence search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/spaces", response_model=ConfluenceSpaceResponse)
async def get_confluence_spaces():
    """Get available Confluence spaces"""
    try:
        if not await confluence_service.is_configured():
            raise HTTPException(status_code=400, detail="Confluence not configured")
        
        spaces = await confluence_service.get_spaces()
        
        return ConfluenceSpaceResponse(spaces=spaces)
        
    except Exception as e:
        logger.error(f"Confluence spaces error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/spaces/{space_key}/content")
async def get_space_content(space_key: str, limit: int = Query(25, ge=1, le=100)):
    """Get content from a specific Confluence space"""
    try:
        if not await confluence_service.is_configured():
            raise HTTPException(status_code=400, detail="Confluence not configured")
        
        content = await confluence_service.get_space_content(space_key, limit)
        
        return {
            "space_key": space_key,
            "content": content,
            "total": len(content)
        }
        
    except Exception as e:
        logger.error(f"Confluence space content error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pages/{page_id}", response_model=ConfluencePageResponse)
async def get_confluence_page(page_id: str):
    """Get specific Confluence page content"""
    try:
        if not await confluence_service.is_configured():
            raise HTTPException(status_code=400, detail="Confluence not configured")
        
        page = await confluence_service.get_page_content(page_id)
        
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")
        
        return ConfluencePageResponse(page=page)
        
    except Exception as e:
        logger.error(f"Confluence page error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/context")
async def get_confluence_context(query: str = Query(..., description="Search query for context")):
    """Get Confluence content as context for AI queries"""
    try:
        if not await confluence_service.is_configured():
            return {"context": "", "configured": False}
        
        context = await confluence_service.get_context_for_query(query)
        
        return {
            "context": context,
            "configured": True,
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Confluence context error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))