import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.schemas.auth import UserCreate, Token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
    
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, user_id: uuid.UUID) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.settings.jwt_expiration_minutes)
        to_encode = {"sub": str(user_id), "exp": expire}
        return jwt.encode(to_encode, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)
    
    def decode_token(self, token: str) -> Optional[str]:
        """Decode JWT token and return user_id string, or None if invalid."""
        try:
            payload = jwt.decode(token, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            return payload.get("sub")
        except JWTError:
            return None
    
    async def register(self, user_data: UserCreate) -> User:
        """Register a new user. Raises ValueError if username/email exists."""
        # Check if username exists
        result = await self.db.execute(select(User).where(User.username == user_data.username))
        if result.scalar_one_or_none():
            raise ValueError("Username already taken")
        
        # Check if email exists  
        result = await self.db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")
        
        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=self.hash_password(user_data.password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password. Returns User or None."""
        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by UUID string."""
        result = await self.db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        return result.scalar_one_or_none()
