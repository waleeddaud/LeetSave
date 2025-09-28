from pydantic import BaseModel
class User(BaseModel):
    id : int
    username: str
    github_token: str