from pydantic import EmailStr,BaseModel

class AdminLoginRequest(BaseModel):

    email: EmailStr
    password: str
