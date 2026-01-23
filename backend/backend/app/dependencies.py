import json
import base64
import logging
from typing import Optional, Dict
from fastapi import Header, HTTPException, status
from .config import settings

logger = logging.getLogger("banking-auth")

async def get_current_user(x_amzn_oidc_data: Optional[str] = Header(None)) -> Dict:
    # Always require real auth in production; no DEV_MODE bypass allowed.

    # 2. PRODUCTION CHECK
    if not x_amzn_oidc_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Authentication Credentials Missing"
        )

    try:
        # Decode Token (Add verify_signature here for Prod)
        payload_part = x_amzn_oidc_data.split('.')[1]
        padded = payload_part + '=' * (4 - len(payload_part) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        
        raw_groups = data.get("cognito:groups", [])
        if isinstance(raw_groups, str): raw_groups = [raw_groups]
        
        return {
            "name": data.get("username", "Unknown"),
            "email": data.get("email", ""),
            "groups": [g.title() for g in raw_groups]
        }
    except Exception as e:
        logger.error(f"Token Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid Security Token")
