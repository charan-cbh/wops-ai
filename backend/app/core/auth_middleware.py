"""
Authentication and Authorization Middleware
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.local_user_management_service import UserRole

# Import appropriate user service based on environment
from app.core.config import settings
if settings.is_local:
    from app.services.local_user_management_service import local_user_management_service as user_management_service
else:
    from app.services.aws_user_management_service import aws_user_management_service as user_management_service

logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()

class AuthMiddleware:
    """Authentication and authorization middleware"""
    
    @staticmethod
    async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """Get current authenticated user from token"""
        try:
            token = credentials.credentials
            payload = user_management_service.verify_token(token)
            
            # Get fresh user data
            user = await user_management_service.get_user_by_id(payload['user_id'])
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            return {
                'user_id': user.user_id,
                'email': user.email,
                'role': user.role,
                'usage_plan': user.usage_plan,
                'usage_limits': user.usage_limits,
                'current_usage': user.current_usage
            }
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )

    @staticmethod
    async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
        """Get current user if authenticated, otherwise return None"""
        if not credentials:
            return None
        
        try:
            return await AuthMiddleware.get_current_user(credentials)
        except HTTPException:
            return None

    @staticmethod
    def require_role(allowed_roles: List[UserRole]):
        """Dependency to require specific roles"""
        async def role_checker(current_user: Dict[str, Any] = Depends(AuthMiddleware.get_current_user)) -> Dict[str, Any]:
            if UserRole(current_user['role']) not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return current_user
        return role_checker

    @staticmethod
    def require_admin():
        """Dependency to require admin role"""
        return AuthMiddleware.require_role([UserRole.ADMIN])

    @staticmethod
    async def check_usage_limits(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        """Check if user can perform actions based on usage limits"""
        user_id = current_user['user_id']
        
        # Check message limit
        if not await user_management_service.check_usage_limits(user_id, 'message'):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Usage limit exceeded. Please upgrade your plan or try again later."
            )
        
        return current_user

    @staticmethod
    async def check_model_access(model_name: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> bool:
        """Check if user can access a specific model"""
        user_id = current_user['user_id']
        
        if not await user_management_service.can_access_model(user_id, model_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to model '{model_name}' not available in your plan"
            )
        
        return True

# Convenience functions
get_current_user = AuthMiddleware.get_current_user
get_optional_user = AuthMiddleware.get_optional_user
require_admin = AuthMiddleware.require_admin
require_role = AuthMiddleware.require_role
check_usage_limits = AuthMiddleware.check_usage_limits
check_model_access = AuthMiddleware.check_model_access