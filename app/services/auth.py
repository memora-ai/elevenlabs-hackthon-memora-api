import uuid
from jose import jwt

import requests

from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

from app.core.config import settings

from app.services.user import UserService 


http_bearer = HTTPBearer(auto_error=False)

class AuthError(HTTPException):
    pass

def get_token_auth_header(
    credentials: HTTPAuthorizationCredentials = Security(http_bearer)
):
    if credentials:
        return credentials.credentials
    
    raise AuthError(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Authorization header is missing",
    )

def requires_auth(permission: str = None):
    async def decorator(
        token: str = Depends(get_token_auth_header)
    ):
        jsonurl = requests.get(f"{settings.AUTH0_DOMAIN}.well-known/jwks.json", timeout=10)
        jwks = jsonurl.json()

        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as exc:
            raise AuthError(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid token header",
            ) from exc

        rsa_key = {}
        if 'kid' not in unverified_header:
            raise AuthError(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid token header: 'kid' missing",
            )

        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key.get("kty"),
                    "kid": key.get("kid"),
                    "use": key.get("use"),
                    "n": key.get("n"),
                    "e": key.get("e"),
                }
                break

        if not rsa_key:
            raise AuthError(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key",
            )

        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=settings.ALGORITHMS,
                audience=settings.API_AUDIENCE,
                issuer=settings.AUTH0_DOMAIN
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthError(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            ) from exc
        except jwt.JWTClaimsError as exc:
            raise AuthError(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=f"Incorrect claims. {str(exc)}",
            ) from exc
        except Exception as exc:
            raise AuthError(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Unable to parse authentication token",
            ) from exc

        print(payload)
        # Extract user details from the token payload
        user_id = payload.get("sub", None)  # Use the 'sub' claim as the user ID
        email = payload.get("email", str(uuid.uuid4()) + '@memoras.ai')
        name = payload.get("name", "User Draiven")
        picture = None

        # Check if the user exists in the database
        user_service = UserService()
        user = await user_service.get_user_by_id(user_id)

        # If the user does not exist, create a new user
        if not user:
            try:
                userinfo_url = f"{settings.AUTH0_DOMAIN}userinfo"
                response = requests.get(
                    userinfo_url,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3000
                )

                if response.status_code == 200:
                    userinfo = response.json()
                    print(userinfo)

                    email = userinfo.get('email', email)
                    name = userinfo.get('name', name)
                    picture = userinfo.get('picture', picture)
            except Exception as ex:
                print('-> could not retrieve user info')
                print(ex)

            user_data = {
                "id": str(user_id),   # Store the 'sub' claim as user ID
                "email": email,
                "name": name,
                "permissions": [],
            }
            user = await user_service.create_user(user_data)

        # Permission check
        if permission:
            if "permissions" in payload and permission in payload["permissions"]:
                return user

            raise AuthError(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Permissions not included in token",
            )

        return user.to_dict()

    return decorator
