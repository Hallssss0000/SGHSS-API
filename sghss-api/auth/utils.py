import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from config import Config

def hash_password(password):
    """Gera hash da senha usando bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password, hashed):
    """Verifica se a senha corresponde ao hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_token(user_id, perfil, expires_in=3600):
    """Gera token JWT"""
    payload = {
        'user_id': user_id,
        'perfil': perfil,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verifica e decodifica token JWT"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expirado
    except jwt.InvalidTokenError:
        return None  # Token inválido

# Decorators para proteção de rotas
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Verificar token no header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token de autenticação ausente'}), 401
        
        # Verificar token
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token inválido ou expirado'}), 401
        
        # Adicionar informações do usuário 
        request.user_id = payload['user_id']
        request.user_perfil = payload['perfil']
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'user_perfil') or request.user_perfil != 'ADMIN':
            return jsonify({'error': 'Acesso não autorizado. Perfil ADMIN requerido.'}), 403
        return f(*args, **kwargs)
    return decorated

def profissional_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'user_perfil') or request.user_perfil not in ['PROFISSIONAL', 'ADMIN']:
            return jsonify({'error': 'Acesso não autorizado. Perfil PROFISSIONAL ou ADMIN requerido.'}), 403
        return f(*args, **kwargs)
    return decorated