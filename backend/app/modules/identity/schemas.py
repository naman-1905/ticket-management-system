from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; email: EmailStr; full_name: str; role: str; is_active: bool
class RegisterIn(BaseModel): email: EmailStr; full_name: str = Field(min_length=1, max_length=200); password: str = Field(min_length=8)
class LoginIn(BaseModel): email: EmailStr; password: str
class TokenOut(BaseModel): access_token: str; refresh_token: str; token_type: str = "bearer"
class RefreshIn(BaseModel): refresh_token: str
