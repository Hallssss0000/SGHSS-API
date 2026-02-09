from flask import Blueprint, request, jsonify
from datetime import datetime
import json
from auth.utils import token_required, admin_required
from config import Config

pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')

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

# Endpoints
@pacientes_bp.route('', methods=['GET'])
@token_required
@admin_required
def get_pacientes():
    """Lista todos os pacientes (apenas ADMIN)"""
    pacientes = carregar_dados('pacientes')
    usuarios = carregar_dados('usuarios')
    
    # Combinar dados
    pacientes_completos = []
    for paciente in pacientes:
        usuario = next((u for u in usuarios if u['id'] == paciente['id']), None)
        if usuario:
            paciente_completo = {
                'id': paciente['id'],
                'nome': usuario['nome'],
                'email': usuario['email'],
                'telefone': paciente.get('telefone', ''),
                'data_nascimento': paciente.get('data_nascimento', ''),
                'endereco': paciente.get('endereco', {}),
                'data_cadastro': paciente.get('data_cadastro', '')
            }
            pacientes_completos.append(paciente_completo)
    
    return jsonify(pacientes_completos), 200

@pacientes_bp.route('', methods=['POST'])
@token_required
@admin_required
def create_paciente():
    """Cria um novo paciente (apenas ADMIN)"""
    data = request.get_json()
    
    required_fields = ['nome', 'email', 'senha', 'telefone']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório faltando: {field}'}), 400
    
    # Verificar se email já existe
    usuarios = carregar_dados('usuarios')
    if any(u['email'] == data['email'] for u in usuarios):
        return jsonify({'error': 'Email já cadastrado'}), 409
    
    from auth.utils import hash_password
    
    # Criar usuário
    novo_id = max([u['id'] for u in usuarios], default=0) + 1
    novo_usuario = {
        'id': novo_id,
        'nome': data['nome'],
        'email': data['email'],
        'senha': hash_password(data['senha']),
        'perfil': 'PACIENTE',
        'data_cadastro': datetime.now().isoformat()
    }
    
    usuarios.append(novo_usuario)
    salvar_dados('usuarios', usuarios)
    
    # Criar paciente
    pacientes = carregar_dados('pacientes')
    novo_paciente = {
        'id': novo_id,
        'telefone': data['telefone'],
        'data_nascimento': data.get('data_nascimento', ''),
        'endereco': data.get('endereco', {}),
        'data_cadastro': datetime.now().isoformat()
    }
    
    pacientes.append(novo_paciente)
    salvar_dados('pacientes', pacientes)
    
    return jsonify({
        'message': 'Paciente criado com sucesso',
        'paciente': {
            'id': novo_id,
            'nome': data['nome'],
            'email': data['email'],
            'telefone': data['telefone']
        }
    }), 201

@pacientes_bp.route('/<int:paciente_id>', methods=['GET'])
@token_required
def get_paciente(paciente_id):
    """Obtém dados de um paciente específico"""
    # Verificar permissão
    if request.user_perfil != 'ADMIN' and request.user_id != paciente_id:
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    pacientes = carregar_dados('pacientes')
    paciente = next((p for p in pacientes if p['id'] == paciente_id), None)
    
    if not paciente:
        return jsonify({'error': 'Paciente não encontrado'}), 404
    
    # Adicionar dados do usuário
    usuarios = carregar_dados('usuarios')
    usuario = next((u for u in usuarios if u['id'] == paciente_id), None)
    
    if usuario:
        paciente['nome'] = usuario['nome']
        paciente['email'] = usuario['email']
    
    return jsonify(paciente), 200

@pacientes_bp.route('/<int:paciente_id>', methods=['PUT'])
@token_required
def update_paciente(paciente_id):
    """Atualiza dados de um paciente"""
    # Verificar permissão
    if request.user_perfil != 'ADMIN' and request.user_id != paciente_id:
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    data = request.get_json()
    
    pacientes = carregar_dados('pacientes')
    paciente_index = next((i for i, p in enumerate(pacientes) if p['id'] == paciente_id), None)
    
    if paciente_index is None:
        return jsonify({'error': 'Paciente não encontrado'}), 404
    
    # Atualizar dados do paciente
    if 'telefone' in data:
        pacientes[paciente_index]['telefone'] = data['telefone']
    if 'data_nascimento' in data:
        pacientes[paciente_index]['data_nascimento'] = data['data_nascimento']
    if 'endereco' in data:
        pacientes[paciente_index]['endereco'] = data['endereco']
    
    salvar_dados('pacientes', pacientes)
    
    # Atualizar dados do usuário se fornecido
    if 'nome' in data or 'email' in data:
        usuarios = carregar_dados('usuarios')
        usuario_index = next((i for i, u in enumerate(usuarios) if u['id'] == paciente_id), None)
        
        if usuario_index is not None:
            if 'nome' in data:
                usuarios[usuario_index]['nome'] = data['nome']
            if 'email' in data:
                # Verificar se email já existe (exceto para o próprio usuário)
                if any(u['email'] == data['email'] for i, u in enumerate(usuarios) if i != usuario_index):
                    return jsonify({'error': 'Email já está em uso'}), 409
                usuarios[usuario_index]['email'] = data['email']
            salvar_dados('usuarios', usuarios)
    
    return jsonify({'message': 'Paciente atualizado com sucesso'}), 200

@pacientes_bp.route('/<int:paciente_id>/consultas', methods=['GET'])
@token_required
def get_consultas_paciente(paciente_id):
    """Lista consultas de um paciente"""
    # Verificar permissão
    if request.user_perfil != 'ADMIN' and request.user_id != paciente_id:
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    consultas = carregar_dados('consultas')
    consultas_paciente = [c for c in consultas if c['paciente'] == paciente_id]
    
    # Adicionar informações
    usuarios = carregar_dados('usuarios')
    profissionais = carregar_dados('profissionais')
    
    for consulta in consultas_paciente:
        # Nome do profissional
        profissional = next((p for p in profissionais if p['id'] == consulta['profissional']), None)
        if profissional:
            consulta['profissional_nome'] = profissional.get('nome')
    
    return jsonify(consultas_paciente), 200