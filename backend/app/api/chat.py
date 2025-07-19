from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from ..services.bi_service import bi_service
from ..services.chat_history_service import chat_history_service
from ..services.scalable_chat_service import scalable_chat_service
from ..core.config import settings
from ..services.local_user_management_service import local_user_management_service, UserRole
from ..services.local_email_service import local_email_service

# Use local services in development, AWS services in production
if settings.is_local:
    user_service = local_user_management_service
    email_service = local_email_service
else:
    from ..services.aws_user_management_service import aws_user_management_service
    from ..services.email_verification_service import email_verification_service
    user_service = aws_user_management_service
    email_service = email_verification_service
# from ..services.weekly_digest_service import weekly_digest_service
from ..core.ai_provider import ai_manager
from ..core.auth import get_optional_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Authentication dependencies
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user from token"""
    try:
        token = credentials.credentials
        payload = user_service.verify_token(token)
        
        # Get fresh user data
        user = user_service._get_user_by_id(payload['user_id'])
        if not user or user.status.value != 'active':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return {
            'user_id': user.user_id,
            'email': user.email,
            'role': user.role.value,
            'usage_plan': user.usage_plan.value,
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

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require admin role"""
    if current_user['role'] != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def check_usage_limits(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Check if user can perform actions based on usage limits"""
    user_id = current_user['user_id']
    
    # Check message limit
    if not await user_service.check_usage_limits(user_id, 'message'):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Usage limit exceeded. Please upgrade your plan or try again later."
        )
    
    return current_user


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    context: Optional[Dict[str, Any]] = None
    ai_provider: Optional[str] = None
    model: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    query_results: Optional[List[Dict[str, Any]]] = None
    insights: Optional[List[str]] = None
    charts: Optional[List[Dict[str, Any]]] = None
    sql_query: Optional[str] = None
    ai_provider: str
    model: str
    success: bool
    session_info: Optional[Dict[str, str]] = None


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int  # 1-5
    comment: Optional[str] = None


class SessionRequest(BaseModel):
    session_id: Optional[str] = None


# Authentication request models
class RegisterRequest(BaseModel):
    email: str
    role: UserRole = UserRole.USER
    usage_plan: str = "free"


class SetPasswordRequest(BaseModel):
    email: str
    password: str
    verification_token: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ResetPasswordRequest(BaseModel):
    email: str


class ConfirmPasswordResetRequest(BaseModel):
    email: str
    token: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest, current_user: Dict[str, Any] = Depends(check_usage_limits)):
    """Main chat endpoint for business intelligence queries (requires authentication)"""
    try:
        user_id = current_user['user_id']
        
        # Check if user can access the requested model
        if request.model and not await user_service.can_access_model(user_id, request.model):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to model '{request.model}' not available in your plan"
            )
        
        # Increment usage counter
        await user_service.increment_usage(user_id, 'message')
        
        # Process the user's query through the BI service
        bi_result = await bi_service.process_natural_language_query(
            user_query=request.message,
            context=request.context,
            conversation_history=request.conversation_history,
            session_id=request.session_id
        )
        
        logger.info(f"BI result: {bi_result}")
        
        # Build response message
        response_parts = []
        
        if bi_result.get("explanation"):
            response_parts.append(bi_result["explanation"])
        
        if bi_result.get("business_context"):
            response_parts.append(f"\n**Business Context:** {bi_result['business_context']}")
        
        if bi_result.get("sql_query"):
            response_parts.append(f"\n**Executed SQL Query:**\n```sql\n{bi_result['sql_query']}\n```")
        
        if bi_result.get("success") and bi_result.get("data"):
            row_count = bi_result.get("row_count", 0)
            response_parts.append(f"\n**Query Results:** Found {row_count} records")
            
            # Add insights if available
            if bi_result.get("insights"):
                insights_text = "\n".join([f"• {insight}" for insight in bi_result["insights"]])
                response_parts.append(f"\n**Key Insights:**\n{insights_text}")
        
        if bi_result.get("error"):
            response_parts.append(f"\n**Error:** {bi_result['error']}")
        
        response_text = "\n".join(response_parts)
        
        # Get AI provider info
        provider_info = ai_manager.get_available_providers()
        current_provider = request.ai_provider or "openai"
        
        try:
            response_obj = ChatResponse(
                response=response_text,
                query_results=bi_result.get("data"),
                insights=bi_result.get("insights"),
                charts=bi_result.get("charts"),
                sql_query=bi_result.get("sql_query"),
                ai_provider=current_provider,
                model=request.model or "default",
                success=bi_result.get("success", False),
                session_info=bi_result.get("session_info")
            )
            logger.info(f"ChatResponse created successfully")
            return response_obj
        except Exception as e:
            logger.error(f"Error creating ChatResponse: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Response serialization error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/metrics")
async def get_dashboard_metrics():
    """Get dashboard metrics for the BI interface"""
    try:
        metrics = bi_service.get_dashboard_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Dashboard metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyses")
async def get_available_analyses():
    """Get list of available pre-built analyses"""
    try:
        analyses = bi_service.get_available_analyses()
        return {"analyses": analyses}
    except Exception as e:
        logger.error(f"Available analyses error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def get_ai_providers():
    """Get list of available AI providers"""
    try:
        providers = ai_manager.get_available_providers()
        provider_details = {}
        
        for provider in providers:
            ai_provider = ai_manager.get_provider(provider)
            provider_details[provider] = {
                "available_models": ai_provider.get_available_models(),
                "name": provider.title()
            }
        
        return {
            "providers": provider_details,
            "default": "openai"
        }
    except Exception as e:
        logger.error(f"AI providers error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables")
async def get_available_tables():
    """Get list of available database tables"""
    try:
        tables = bi_service.snowflake_db.get_available_tables()
        return {"tables": tables}
    except Exception as e:
        logger.error(f"Available tables error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/schema")
async def get_table_schema(table_name: str):
    """Get schema information for a specific table"""
    try:
        schema = bi_service.snowflake_db.get_table_schema(table_name)
        return {"table_name": table_name, "schema": schema}
    except Exception as e:
        logger.error(f"Table schema error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/sample")
async def get_table_sample(table_name: str, limit: int = 10):
    """Get sample data from a table"""
    try:
        sample_df = bi_service.snowflake_db.get_table_sample(table_name, limit)
        return {
            "table_name": table_name,
            "sample_data": sample_df.to_dict('records'),
            "columns": sample_df.columns.tolist()
        }
    except Exception as e:
        logger.error(f"Table sample error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Chat History and Session Management Endpoints

@router.post("/session")
async def create_or_get_session(request: SessionRequest):
    """Create a new session or get existing session info"""
    try:
        session_info = chat_history_service.get_or_create_user(request.session_id)
        return {
            "session_id": session_info["session_id"],
            "user_id": session_info["user_id"],
            "created": request.session_id is None
        }
    except Exception as e:
        logger.error(f"Session creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user"""
    try:
        sessions = chat_history_service.get_user_sessions(user_id)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Get sessions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}/{session_id}")
async def get_chat_history(user_id: str, session_id: str, limit: int = 50):
    """Get chat history for a specific session"""
    try:
        history = chat_history_service.get_chat_history(user_id, session_id, limit)
        return {"history": history}
    except Exception as e:
        logger.error(f"Get chat history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback for a message"""
    try:
        if request.rating < 1 or request.rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        chat_history_service.add_feedback(
            message_id=request.message_id,
            rating=request.rating,
            comment=request.comment
        )
        
        return {"success": True, "message": "Feedback submitted successfully"}
    except Exception as e:
        logger.error(f"Submit feedback error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats")
async def get_feedback_stats(days: int = 30):
    """Get feedback statistics"""
    try:
        stats = chat_history_service.get_feedback_stats(days)
        return {"stats": stats, "period_days": days}
    except Exception as e:
        logger.error(f"Get feedback stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/cleanup")
async def cleanup_old_sessions(days: int = 90):
    """Clean up old inactive sessions"""
    try:
        chat_history_service.cleanup_old_sessions(days)
        return {"success": True, "message": f"Cleaned up sessions older than {days} days"}
    except Exception as e:
        logger.error(f"Cleanup sessions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Weekly Digest Endpoints - DISABLED
# User requested to remove weekly digest functionality

# @router.get("/digest/weekly")
# async def get_weekly_digest(weeks_back: int = 1):
#     """Generate and return weekly business intelligence digest"""
#     try:
#         if weeks_back < 1 or weeks_back > 12:
#             raise HTTPException(status_code=400, detail="weeks_back must be between 1 and 12")
#         
#         digest = await weekly_digest_service.generate_weekly_digest(weeks_back)
#         return digest
#     except Exception as e:
#         logger.error(f"Weekly digest error: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/digest/preview")
# async def get_digest_preview():
#     """Get a preview of what would be included in the weekly digest"""
#     try:
#         # Generate digest for current week with minimal data processing
#         preview = await weekly_digest_service.generate_weekly_digest(1)
#         
#         # Return only key metrics and summary for preview
#         return {
#             "period": preview.get("period", {}),
#             "metrics": preview.get("metrics", {}),
#             "data_coverage": preview.get("data_coverage", {}),
#             "preview": True
#         }
#     except Exception as e:
#         logger.error(f"Digest preview error: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# Authentication Routes - Updated for Email Verification Flow

@router.post("/auth/register")
async def register(request: RegisterRequest):
    """Register a new user - sends email verification"""
    try:
        # Only admins can create admin accounts
        if request.role == UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create admin accounts through public registration"
            )
        
        result = await user_service.register_user(request.email, request.role, request.usage_plan)
        logger.info(f"User registration initiated: {request.email}")
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/auth/set-password", response_model=TokenResponse)
async def set_password(request: SetPasswordRequest):
    """Set password after email verification"""
    try:
        result = await user_service.set_password(request.email, request.password, request.verification_token)
        logger.info(f"Password set successfully for: {request.email}")
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Set password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set password"
        )

@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return tokens"""
    try:
        result = await user_service.login_user(request.email, request.password)
        logger.info(f"User logged in successfully: {request.email}")
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/auth/request-password-reset")
async def request_password_reset(request: ResetPasswordRequest):
    """Request password reset email"""
    try:
        # Get user to verify they exist
        user = user_service._get_user_by_email(request.email)
        if user:
            await email_service.send_password_reset_email(request.email, user.user_id)
        
        # Always return success to prevent email enumeration
        return {"message": "If an account with this email exists, a password reset link has been sent."}
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        # Don't expose internal errors
        return {"message": "If an account with this email exists, a password reset link has been sent."}

@router.post("/auth/confirm-password-reset", response_model=TokenResponse)
async def confirm_password_reset(request: ConfirmPasswordResetRequest):
    """Confirm password reset with new password"""
    try:
        # Verify reset token
        user_id = await email_service.verify_password_reset_token(request.email, request.token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Update password using the user service
        password_hash = user_service._hash_password(request.new_password)
        
        # Update user password in database
        if settings.is_local:
            # SQLite update
            with user_service._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET password_hash = ?, updated_at = ?
                    WHERE user_id = ?
                """, (password_hash, datetime.now(timezone.utc).isoformat(), user_id))
                conn.commit()
        else:
            # PostgreSQL or DynamoDB update
            if user_service.storage_type == "postgresql":
                with user_service._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (password_hash, user_id))
                    conn.commit()
            elif user_service.storage_type == "dynamodb":
                user_service.users_table.update_item(
                    Key={'user_id': user_id},
                    UpdateExpression='SET password_hash = :ph, updated_at = :updated',
                    ExpressionAttributeValues={
                        ':ph': password_hash,
                        ':updated': datetime.now(timezone.utc).isoformat()
                    }
                )
        
        # Mark token as used
        await email_service.mark_password_reset_token_used(request.email, request.token)
        
        # Get updated user and generate tokens
        user = user_service._get_user_by_email(request.email)
        if not user:
            raise HTTPException(status_code=500, detail="User not found after password reset")
        
        result = user_service._generate_tokens(user)
        logger.info(f"Password reset successfully for: {request.email}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )

@router.get("/auth/verify-email")
async def verify_email(email: str, token: str):
    """Verify email address"""
    try:
        is_verified = await email_service.verify_email_token(email, token)
        
        if is_verified:
            return {"message": "Email verified successfully. You can now set your password."}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

@router.get("/auth/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information"""
    user = user_service._get_user_by_id(current_user['user_id'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role.value,
        "usage_plan": user.usage_plan.value,
        "status": user.status.value,
        "is_email_verified": user.is_email_verified,
        "current_usage": user.current_usage,
        "usage_limits": {
            "monthly_messages": user.usage_limits.monthly_messages,
            "daily_messages": user.usage_limits.daily_messages,
            "model_access": user.usage_limits.model_access,
            "advanced_features": user.usage_limits.advanced_features
        }
    }

# Admin-only routes
@router.get("/auth/users")
async def get_all_users(
    page: int = 1,
    limit: int = 50,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """Get all users (admin only)"""
    try:
        result = await user_service.get_all_users(page, limit)
        return result
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )

@router.get("/auth/providers")
async def get_ai_providers_admin(admin_user: Dict[str, Any] = Depends(require_admin)):
    """Get AI providers - admin only now"""
    try:
        providers = ai_manager.get_available_providers()
        return providers
    except Exception as e:
        logger.error(f"AI providers error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))