import httpx
import json
from typing import Dict, Any, List, Optional
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class ConfluenceService:
    def __init__(self):
        self.base_url = settings.confluence_base_url
        self.api_token = settings.confluence_api_token
        self.username = settings.confluence_username
        
        if not all([self.base_url, self.api_token, self.username]):
            logger.warning("Confluence configuration incomplete. Some features may not work.")
    
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Confluence API"""
        if not self.base_url or not self.api_token:
            raise ValueError("Confluence not configured")
        
        url = f"{self.base_url}/rest/api{endpoint}"
        
        auth = (self.username, self.api_token)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                auth=auth,
                headers=headers,
                params=params,
                json=data,
                timeout=30.0
            )
            
            response.raise_for_status()
            return response.json()
    
    async def search_content(self, query: str, limit: int = 10, space_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search Confluence content"""
        try:
            params = {
                'cql': f'text ~ "{query}"',
                'limit': limit,
                'expand': 'body.storage,space,version'
            }
            
            if space_key:
                params['cql'] += f' AND space = "{space_key}"'
            
            result = await self._make_request('GET', '/search', params=params)
            
            return [
                {
                    'id': item['id'],
                    'title': item['title'],
                    'type': item['type'],
                    'url': f"{self.base_url}/pages/viewpage.action?pageId={item['id']}",
                    'space': item.get('space', {}).get('name', ''),
                    'content': self._extract_text_from_html(item.get('body', {}).get('storage', {}).get('value', '')),
                    'last_modified': item.get('version', {}).get('when', '')
                }
                for item in result.get('results', [])
            ]
            
        except Exception as e:
            logger.error(f"Error searching Confluence: {str(e)}")
            return []
    
    async def get_page_content(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get specific page content"""
        try:
            params = {'expand': 'body.storage,space,version,ancestors'}
            result = await self._make_request('GET', f'/content/{page_id}', params=params)
            
            return {
                'id': result['id'],
                'title': result['title'],
                'type': result['type'],
                'url': f"{self.base_url}/pages/viewpage.action?pageId={result['id']}",
                'space': result.get('space', {}).get('name', ''),
                'content': self._extract_text_from_html(result.get('body', {}).get('storage', {}).get('value', '')),
                'last_modified': result.get('version', {}).get('when', ''),
                'ancestors': [
                    {
                        'id': ancestor['id'],
                        'title': ancestor['title']
                    }
                    for ancestor in result.get('ancestors', [])
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting page content: {str(e)}")
            return None
    
    async def get_spaces(self) -> List[Dict[str, Any]]:
        """Get available spaces"""
        try:
            result = await self._make_request('GET', '/space')
            
            return [
                {
                    'key': space['key'],
                    'name': space['name'],
                    'type': space['type'],
                    'url': f"{self.base_url}/display/{space['key']}"
                }
                for space in result.get('results', [])
            ]
            
        except Exception as e:
            logger.error(f"Error getting spaces: {str(e)}")
            return []
    
    async def get_space_content(self, space_key: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get content from a specific space"""
        try:
            params = {
                'spaceKey': space_key,
                'limit': limit,
                'expand': 'body.storage,version'
            }
            
            result = await self._make_request('GET', '/content', params=params)
            
            return [
                {
                    'id': item['id'],
                    'title': item['title'],
                    'type': item['type'],
                    'url': f"{self.base_url}/pages/viewpage.action?pageId={item['id']}",
                    'content': self._extract_text_from_html(item.get('body', {}).get('storage', {}).get('value', '')),
                    'last_modified': item.get('version', {}).get('when', '')
                }
                for item in result.get('results', [])
            ]
            
        except Exception as e:
            logger.error(f"Error getting space content: {str(e)}")
            return []
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract plain text from Confluence HTML content"""
        try:
            # Simple HTML tag removal - in production, use a proper HTML parser
            import re
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html_content)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from HTML: {str(e)}")
            return html_content
    
    async def get_context_for_query(self, query: str, max_results: int = 5) -> str:
        """Get relevant Confluence content as context for AI queries"""
        try:
            search_results = await self.search_content(query, limit=max_results)
            
            if not search_results:
                return ""
            
            context_parts = []
            for result in search_results:
                context_parts.append(f"**{result['title']}** (from {result['space']})")
                context_parts.append(result['content'][:500] + "..." if len(result['content']) > 500 else result['content'])
                context_parts.append(f"Source: {result['url']}")
                context_parts.append("---")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return ""
    
    async def is_configured(self) -> bool:
        """Check if Confluence is properly configured"""
        return all([self.base_url, self.api_token, self.username])
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the Confluence connection"""
        try:
            if not await self.is_configured():
                return {
                    "success": False,
                    "error": "Confluence not configured"
                }
            
            # Test by getting user info
            result = await self._make_request('GET', '/user/current')
            
            return {
                "success": True,
                "user": result.get('displayName', 'Unknown'),
                "base_url": self.base_url
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# Global instance
confluence_service = ConfluenceService()