# app/schemas/response/user.py
from pydantic import BaseModel


class UserData(BaseModel):
    id: str
    github_username: str
