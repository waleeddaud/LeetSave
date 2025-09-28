import requests
import jwt
import os 
from dotenv import load_dotenv
load_dotenv()

def get_user(access_token  : str ):
    user_url = "https://api.github.com/user"
    headers = {"Authorization": f"token {access_token}"}
    user_res = requests.get(user_url, headers=headers)
    user_json = user_res.json()
    print("DATA of USER" , user_json)
    return user_json

def generate_custom_token(github_id: int) -> str:
    payload = {
        "sub" : github_id
    }
    jwt_secret = os.getenv("JWT_SECRET")
    jwt_algorithm = "HS256"
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
    return token
