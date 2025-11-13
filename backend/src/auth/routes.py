from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from ..db import get_db
from ..models.database import User
from ..models.schemas import UserCreate, UserLogin, PasswordChange, Token
from .security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()


@router.post("/signup")
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        existing = await db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered, please move to login")

        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            name=getattr(payload, "name", None),
            is_approved=False,
            is_active=True,
            role="user",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {"message": "Signup successful. Awaiting admin approval."}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Signup failed: {e}")
        # Ensure transaction is rolled back
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Signup failed")


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(payload.password, str(user.hashed_password)):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not getattr(user, "is_approved", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not approved by admin")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
        
        # Update last_login timestamp (convert to naive datetime for PostgreSQL)
        user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        
        token = create_access_token(subject=str(user.email))
        return Token(access_token=token, token_type="bearer")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Login failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed")


@router.get("/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_active": current_user.is_active,
        "is_approved": getattr(current_user, "is_approved", False),
        "role": getattr(current_user, "role", "user"),
    }


def require_admin_jwt(current_user: User = Depends(get_current_user)):
    if getattr(current_user, "role", "user") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return True


@router.get("/admin/users", dependencies=[Depends(require_admin_jwt)])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    # return minimal info
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "is_active": u.is_active,
            "is_approved": getattr(u, "is_approved", False),
            "role": getattr(u, "role", "user"),
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in users
    ]


@router.post("/admin/approve/{user_id}", dependencies=[Depends(require_admin_jwt)])
async def approve_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_approved = True
    await db.commit()
    return {"message": "User approved successfully."}


@router.post("/admin/activate/{user_id}", dependencies=[Depends(require_admin_jwt)])
async def activate_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = True
    await db.commit()
    return {"message": "User activated."}


@router.post("/admin/deactivate/{user_id}", dependencies=[Depends(require_admin_jwt)])
async def deactivate_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Prevent deactivating admin users
    if getattr(user, "role", "user") == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cannot deactivate admin users"
        )
    
    user.is_active = False
    await db.commit()
    return {"message": "User deactivated."}


@router.post("/admin/reset-password/{user_id}", dependencies=[Depends(require_admin_jwt)])
async def reset_password(user_id: int, new_password: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.hashed_password = hash_password(new_password)
    await db.commit()
    return {"message": "Password updated successfully."}


@router.post("/change-password")
async def change_password(
    payload: PasswordChange, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Allow users to change their own password"""
    try:
        # Verify current password
        if not verify_password(payload.current_password, str(current_user.hashed_password)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Current password is incorrect"
            )
        
        # Update password
        current_user.hashed_password = hash_password(payload.new_password)
        await db.commit()
        
        return {"message": "Password changed successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Password change failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Password change failed"
        )


