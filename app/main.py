import requests
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from utils import get_user, generate_custom_token

import os
from dotenv import load_dotenv
from urllib.parse import quote
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # or ["*"] to allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET =  os.getenv("GITHUB_CLIENT_SECRET")
CHROME_EXTENSION_ID = os.getenv("CHROME_EXTENSION_ID")
print("GITHUB_CLIENT_ID =", os.getenv("GITHUB_CLIENT_ID"))
print("CALLBACK_URL =", os.getenv("CALLBACK_URL"))

@app.post("/login")
def github_login():
    print("Processing request for /login")
    scope = os.getenv("SCOPE", "repo")
    redirect_uri = os.getenv("CALLBACK_URL")  
    encoded_redirect_uri = quote(redirect_uri, safe="") 

    github_oauth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={encoded_redirect_uri}"
        f"&scope={scope}"
        f"&prompt=login"
    )
    return {"url": github_oauth_url}

@app.get("/github/callback")
def github_callback(code: str):
    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret":  GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": "http://localhost:8000/github/callback"
    }
    res = requests.post(token_url, headers=headers, data=data)
    token_json = res.json()
    print("Token Response:", token_json)
    access_token = token_json.get("access_token")
    print("Access Token:", access_token)
    user_data = get_user(access_token)
    
    # Anyone with this access token can push to github we need to store it securely
    # iNSTEAD OF GIVING THIS ACCESS CODE TO EXTENSION I WANT TO GIVE A CUSTOM TOKEN
    
    # Store access_token for this user (securely in DB) and generate custom token against it
    # return {"access_token": access_token}
    token = generate_custom_token(github_id=12345)  # Replace with actual GitHub user ID
    return RedirectResponse(
        url=f"chrome-extension://{CHROME_EXTENSION_ID}/success.html#token={access_token}"
    )


