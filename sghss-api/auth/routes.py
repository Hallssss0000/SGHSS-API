from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os
from auth.utils import hash_password, check_password, generate_token, token_required
from config import Config

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Funções auxiliares
def carregar_dados(nome):
    try:
        with open(Config.FILES[nome], 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def salvar_dados(nome, dados):
    with open(Config.FILES[nome], 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def gerar_id(lista):
    if not lista:
        return 1
    return max(item.get('id', 0) for item in lista) + 1

# Endpoints
@auth_bp.route('/login', methods=['POST'])
def login():
    """Login de usuário - retorna token JWT"""
    data = request.get_json()
    
    if not data or 'email' not in data or 'senha' not in data:
        return jsonify({'error': 'Email e senha são obrigatórios'}), 400
    
    usuarios = carregar_dados('usuarios')
    
    # Buscar usuário
    usuario = next((u for u in usuarios if u['email'] == data['email']), None)
    
    if not usuario:
        return jsonify({'error': 'Credenciais inválidas'}), 401
    
    # Verificar senha
    if not check_password(data['senha'], usuario['senha']):
        return jsonify({'error': 'Credenciais inválidas'}), 401
    
    # Gerar token JWT
    token = generate_token(usuario['id'], usuario['perfil'])
    
    # Resposta
    response_data = {
        'message': 'Login realizado com sucesso',
        'access_token': token,
        'token_type': 'Bearer',
        'user': {
            'id': usuario['id'],
            'nome': usuario['nome'],
            'email': usuario['email'],
            'perfil': usuario['perfil']
        }
    }
    
    # Adicionar informações específicas do perfil
    if usuario['perfil'] == 'PACIENTE':
        pacientes = carregar_dados('pacientes')
        paciente = next((p for p in pacientes if p['id'] == usuario['id']), None)
        if paciente:
            response_data['user']['telefone'] = paciente.get('telefone')
    
    elif usuario['perfil'] == 'PROFISSIONAL':
        profissionais = carregar_dados('profissionais')
        profissional = next((p for p in profissionais if p['id'] == usuario['id']), None)
        if profissional:
            response_data['user']['nome_completo'] = profissional.get('nome')
            response_data['user']['especialidade'] = profissional.get('especialidade', '')
    
    return jsonify(response_data), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registro de novo usuário"""
    data = request.get_json()
    
    # Validações básicas
    required_fields = ['nome', 'email', 'senha', 'perfil']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório faltando: {field}'}), 400
    
    if data['perfil'] not in ['PACIENTE', 'PROFISSIONAL', 'ADMIN']:
        return jsonify({'error': 'Perfil inválido'}), 400
    
    # Verificar se email já existe
    usuarios = carregar_dados('usuarios')
    if any(u['email'] == data['email'] for u in usuarios):
        return jsonify({'error': 'Email já cadastrado'}), 409
    
    # Criar novo usuário
    novo_id = gerar_id(usuarios)
    novo_usuario = {
        'id': novo_id,
        'nome': data['nome'],
        'email': data['email'],
        'senha': hash_password(data['senha']),  # Senha com hash
        'perfil': data['perfil'],
        'data_cadastro': datetime.now().isoformat()
    }
    
    usuarios.append(novo_usuario)
    salvar_dados('usuarios', usuarios)
    
    # Criar registro específico do perfil
    if data['perfil'] == 'PACIENTE':
        pacientes = carregar_dados('pacientes')
        novo_paciente = {
            'id': novo_id,
            'telefone': data.get('telefone', ''),
            'data_nascimento': data.get('data_nascimento', ''),
            'endereco': data.get('endereco', {}),
            'data_cadastro': datetime.now().isoformat()
        }
        pacientes.append(novo_paciente)
        salvar_dados('pacientes', pacientes)
    
    elif data['perfil'] == 'PROFISSIONAL':
        profissionais = carregar_dados('profissionais')
        novo_profissional = {
            'id': novo_id,
            'nome': data['nome'],
            'especialidade': data.get('especialidade', ''),
            'crm': data.get('crm', ''),
            'data_cadastro': datetime.now().isoformat()
        }
        profissionais.append(novo_profissional)
        salvar_dados('profissionais', profissionais)
    
    # Gerar token automaticamente após registro
    token = generate_token(novo_id, data['perfil'])
    
    return jsonify({
        'message': 'Usuário criado com sucesso',
        'access_token': token,
        'token_type': 'Bearer',
        'user': {
            'id': novo_id,
            'nome': data['nome'],
            'email': data['email'],
            'perfil': data['perfil']
        }
    }), 201

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_me():
    """Obtém informações do usuário logado"""
    usuarios = carregar_dados('usuarios')
    usuario = next((u for u in usuarios if u['id'] == request.user_id), None)
    
    if not usuario:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    response_data = {
        'id': usuario['id'],
        'nome': usuario['nome'],
        'email': usuario['email'],
        'perfil': usuario['perfil'],
        'data_cadastro': usuario.get('data_cadastro')
    }
    
    # Adicionar informações específicas do perfil
    if usuario['perfil'] == 'PACIENTE':
        pacientes = carregar_dados('pacientes')
        paciente = next((p for p in pacientes if p['id'] == usuario['id']), None)
        if paciente:
            response_data['telefone'] = paciente.get('telefone')
            response_data['data_nascimento'] = paciente.get('data_nascimento')
            response_data['endereco'] = paciente.get('endereco', {})
    
    elif usuario['perfil'] == 'PROFISSIONAL':
        profissionais = carregar_dados('profissionais')
        profissional = next((p for p in profissionais if p['id'] == usuario['id']), None)
        if profissional:
            response_data['nome_completo'] = profissional.get('nome')
            response_data['especialidade'] = profissional.get('especialidade')
            response_data['crm'] = profissional.get('crm')
    
    return jsonify(response_data), 200