from functools import wraps
from typing import Tuple
import jwt
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

CLERK_PEM_PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsAKVaYtEgYM5sqxbg0PT
HQPEImZcKCoD5mrtAFSmMm8go7i9k4/r8DmIBFQ9yDV4U9m0eSv3x48GNClPyYHu
SmG/oCHwwDhZ3grgRW917ILmuuBGlIMCWEcMzqJFrU9JT3Bd+Md763oZwNu/nChH
D89vwSg9M5UCa6dKxt8mSAsKdJlh6izQD6CNN32PxawHc3KEqkxmT1fS3h67qECw
0/+lPjSfDXL1C6s2ZKRQGTmUsssBP7MnmXgyy5qy1M+uCKT7EsmIWegZkjCvc2j3
D/Buxg5XKrzFu2tyr4wyzQNqZCrQX2jqfUCa2levmuSEv2rCPm2/yRPbjLHz5lUZ
0wIDAQAB
-----END PUBLIC KEY-----
"""

def extract_user_id(decoded_token: dict) -> Tuple[str, bool]:
    """
    Extract the user ID from the decoded token
    
    Args:
        decoded_token (dict): The decoded JWT token
        
    Returns:
        Tuple[str, bool]: A tuple containing (user_id, is_valid)
    """
    user_id = decoded_token.get('sub')
    if not user_id:
        logger.error("No 'sub' field found in token")
        return None, False
    
    if not user_id.startswith('user_'):
        logger.error(f"Invalid user ID format: {user_id}")
        return None, False
        
    return user_id, True

def verify_token(token: str) -> Tuple[dict, str]:
    """
    Verify JWT token and return both decoded payload and user ID
    
    Returns:
        Tuple[dict, str]: A tuple containing (decoded_token, user_id)
    """
    logger.info("Entering verify_token function")
    logger.info(f"Received token: {token[:10]}...")

    try:
        decoded_token = jwt.decode(
            token, 
            key=CLERK_PEM_PUBLIC_KEY, 
            algorithms=['RS256'],
            options={"verify_iat": False}
        )
        logger.info("Token verified successfully")
        
        user_id, is_valid = extract_user_id(decoded_token)
        if not is_valid:
            return None, None
            
        logger.info(f"Extracted user ID: {user_id}")
        return decoded_token, user_id
        
    except jwt.exceptions.PyJWTError as e:
        logger.error(f"Error verifying token: {str(e)}")
        return None, None
    finally:
        logger.info("Exiting verify_token function")

def require_auth(f):
    """
    Decorator to protect routes with JWT authentication
    Adds both decoded_token and user_id to the route's kwargs
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"message": "Missing or invalid authorization header"}), 401
        
        token = auth_header.split(' ')[1]
        decoded_token, user_id = verify_token(token)
        
        if not decoded_token or not user_id:
            return jsonify({"message": "Invalid token"}), 401
            
        # Add both the full token and extracted user_id to kwargs
        return f(*args, token_data=decoded_token, user_id=user_id, **kwargs)
    return decorated

# Example usage in your Flask routes:
"""
from flask import Flask
app = Flask(__name__)

@app.route("/user/settings")
@require_auth
def get_user_settings(user_id=None, token_data=None):
    # user_id is directly available as "user_2nmMtvUVGrZNIDw4lpzq5nWAzQx"
    # token_data contains the full decoded token if needed
    return jsonify({
        "user_id": user_id,
        "settings": fetch_user_settings(user_id)  # Your database query function
    })

@app.route("/user/preferences", methods=['POST'])
@require_auth
def update_preferences(user_id=None):
    preferences = request.json
    # Direct access to user_id without having to extract it from the token
    return jsonify(update_user_preferences(user_id, preferences))
"""