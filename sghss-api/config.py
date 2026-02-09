import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'telemed-super-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Arquivos JSON
    DATA_DIR = 'database'
    FILES = {
        'usuarios': os.path.join(DATA_DIR, 'usuarios.json'),
        'pacientes': os.path.join(DATA_DIR, 'pacientes.json'),
        'profissionais': os.path.join(DATA_DIR, 'profissionais.json'),
        'consultas': os.path.join(DATA_DIR, 'consultas.json'),
        'atendimentos': os.path.join(DATA_DIR, 'atendimentos.json'),
        'prontuarios': os.path.join(DATA_DIR, 'prontuarios.json'),
        'receitas': os.path.join(DATA_DIR, 'receitas.json'),
        'internacoes': os.path.join(DATA_DIR, 'internacoes.json'),
        'notificacoes': os.path.join(DATA_DIR, 'notificacoes.json')
    }