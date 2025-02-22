from fastapi import Depends
from app.services.auth import requires_auth

def get_current_user(payload: dict = Depends(requires_auth())):
    return payload 