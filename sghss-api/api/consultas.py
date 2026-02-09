from flask import Blueprint, request, jsonify
from datetime import datetime
import json
from auth.utils import token_required, admin_required, profissional_required
from config import Config

consultas_bp = Blueprint('consultas', __name__, url_prefix='/consultas')

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

def notificar(paciente_id, mensagem):
    notificacoes = carregar_dados('notificacoes')
    notificacoes.append({
        'paciente': paciente_id,
        'mensagem': mensagem,
        'data': datetime.now().isoformat()
    })
    salvar_dados('notificacoes', notificacoes)

# Endpoints
@consultas_bp.route('', methods=['GET'])
@token_required
def get_consultas():
    """Lista consultas conforme perfil"""
    consultas = carregar_dados('consultas')
    
    # Filtrar conforme perfil
    if request.user_perfil == 'PACIENTE':
        consultas_filtradas = [c for c in consultas if c['paciente'] == request.user_id]
    elif request.user_perfil == 'PROFISSIONAL':
        consultas_filtradas = [c for c in consultas if c['profissional'] == request.user_id]
    else:  # ADMIN
        consultas_filtradas = consultas
    
    # Adicionar informações
    usuarios = carregar_dados('usuarios')
    profissionais = carregar_dados('profissionais')
    
    for consulta in consultas_filtradas:
        # Nome do paciente
        paciente = next((u for u in usuarios if u['id'] == consulta['paciente']), None)
        if paciente:
            consulta['paciente_nome'] = paciente['nome']
        
        # Nome do profissional
        profissional = next((p for p in profissionais if p['id'] == consulta['profissional']), None)
        if profissional:
            consulta['profissional_nome'] = profissional.get('nome')
    
    return jsonify(consultas_filtradas), 200

@consultas_bp.route('', methods=['POST'])
@token_required
def create_consulta():
    """Cria uma nova consulta"""
    data = request.get_json()
    
    required_fields = ['profissional_id', 'data', 'tipo']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório faltando: {field}'}), 400
    
    # Verificar conflito de horário
    consultas = carregar_dados('consultas')
    conflito = any(
        c['profissional'] == data['profissional_id'] and 
        c['data'] == data['data'] and 
        c['status'] == 'AGENDADA'
        for c in consultas
    )
    
    if conflito:
        return jsonify({'error': 'Horário ocupado para este profissional'}), 409
    
    # Determinar paciente
    if request.user_perfil == 'PACIENTE':
        paciente_id = request.user_id
    elif 'paciente_id' in data:
        paciente_id = data['paciente_id']
    else:
        return jsonify({'error': 'ID do paciente é necessário'}), 400
    
    # Verificar permissão
    if request.user_perfil == 'PROFISSIONAL' and data['profissional_id'] != request.user_id:
        return jsonify({'error': 'Você só pode agendar consultas para si mesmo'}), 403
    
    # Gerar link para teleconsulta
    link = f"https://telemed.local/consulta/{gerar_id(consultas)}" if data['tipo'] == 'O' else ""
    
    # Criar consulta
    nova_consulta = {
        'id': gerar_id(consultas),
        'paciente': paciente_id,
        'profissional': data['profissional_id'],
        'data': data['data'],
        'status': 'AGENDADA',
        'tipo': data['tipo'],
        'link': link,
        'data_criacao': datetime.now().isoformat(),
        'criado_por': request.user_id
    }
    
    consultas.append(nova_consulta)
    salvar_dados('consultas', consultas)
    
    # Notificar
    notificar(paciente_id, f"Consulta agendada para {data['data']}")
    
    return jsonify({
        'message': 'Consulta agendada com sucesso',
        'consulta': nova_consulta
    }), 201

@consultas_bp.route('/<int:consulta_id>', methods=['PUT'])
@token_required
def update_consulta(consulta_id):
    """Atualiza uma consulta"""
    data = request.get_json()
    
    consultas = carregar_dados('consultas')
    consulta_index = next((i for i, c in enumerate(consultas) if c['id'] == consulta_id), None)
    
    if consulta_index is None:
        return jsonify({'error': 'Consulta não encontrada'}), 404
    
    consulta = consultas[consulta_index]
    
    # Verificar permissão
    if (request.user_perfil == 'PACIENTE' and consulta['paciente'] != request.user_id and 
        'paciente_id' not in data):
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    if (request.user_perfil == 'PROFISSIONAL' and consulta['profissional'] != request.user_id and 
        'profissional_id' not in data):
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    # Atualizar dados
    if 'data' in data:
        # Verificar conflito
        conflito = any(
            c['profissional'] == consulta['profissional'] and 
            c['data'] == data['data'] and 
            c['status'] == 'AGENDADA' and 
            c['id'] != consulta_id
            for c in consultas
        )
        
        if conflito:
            return jsonify({'error': 'Horário ocupado'}), 409
        
        consultas[consulta_index]['data'] = data['data']
        notificar(consulta['paciente'], f"Consulta reagendada para {data['data']}")
    
    if 'status' in data and data['status'] in ['AGENDADA', 'REALIZADA', 'CANCELADA']:
        consultas[consulta_index]['status'] = data['status']
        if data['status'] == 'CANCELADA':
            notificar(consulta['paciente'], 'Consulta cancelada')
    
    salvar_dados('consultas', consultas)
    
    return jsonify({
        'message': 'Consulta atualizada',
        'consulta': consultas[consulta_index]
    }), 200

# Endpoint DELETE 
@consultas_bp.route('/<int:consulta_id>', methods=['DELETE'])
@token_required
def delete_consulta(consulta_id):
    """Deleta uma consulta do sistema"""
    
    consultas = carregar_dados('consultas')
    
    # Encontrar consulta pelo ID
    consulta_index = next((i for i, c in enumerate(consultas) if c['id'] == consulta_id), None)
    
    if consulta_index is None:
        return jsonify({
            'error': 'Consulta não encontrada',
            'message': f'Não existe consulta com ID {consulta_id}'
        }), 404
    
    consulta = consultas[consulta_index]
    
    # VERIFICAR PERMISSÕES
    user_id = request.user_id
    user_perfil = request.user_perfil
    
    pode_deletar = False
    motivo = ""
    
    if user_perfil == 'ADMIN':
        pode_deletar = True
        motivo = 'Perfil ADMIN tem acesso total'
    
    elif user_perfil == 'PROFISSIONAL' and consulta['profissional'] == user_id:
        pode_deletar = True
        motivo = 'Profissional pode deletar seus próprios agendamentos'
    
    elif user_perfil == 'PACIENTE' and consulta['paciente'] == user_id:
        pode_deletar = True
        motivo = 'Paciente pode deletar seus próprios agendamentos'
    
    if not pode_deletar:
        return jsonify({
            'error': 'Permissão negada',
            'message': 'Você não tem permissão para deletar esta consulta',
            'detalhes': f'{user_perfil} só pode deletar suas próprias consultas'
        }), 403
    
    # VERIFICAR SE CONSULTA JÁ FOI REALIZADA
    if consulta['status'] == 'REALIZADA':
        return jsonify({
            'error': 'Não é possível deletar',
            'message': 'Consultas já realizadas não podem ser removidas',
            'sugestao': 'Altere o status para "CANCELADA" em vez de deletar'
        }), 400
    
    # REMOVER CONSULTA
    consulta_removida = consultas.pop(consulta_index)
    salvar_dados('consultas', consultas)
    
    # NOTIFICAR OS ENVOLVIDOS
    notificar(consulta['paciente'], f"Consulta do dia {consulta['data']} foi removida do sistema")
    
    # Se houver profissional, notificar também
    if consulta['profissional']:
        notificacoes = carregar_dados('notificacoes')
        notificacoes.append({
            'profissional': consulta['profissional'],
            'mensagem': f"Consulta com {consulta['paciente']} foi removida",
            'data': datetime.now().isoformat()
        })
        salvar_dados('notificacoes', notificacoes)
    
    return jsonify({
        'success': True,
        'message': 'Consulta deletada com sucesso',
        'deleted_id': consulta_id,
        'consulta': consulta_removida,
        'motivo': motivo,
        'timestamp': datetime.now().isoformat()
    }), 200

@consultas_bp.route('/<int:consulta_id>/atender', methods=['POST'])
@token_required
@profissional_required
def atender_consulta(consulta_id):
    """Registra atendimento"""
    data = request.get_json()
    
    if 'observacoes' not in data:
        return jsonify({'error': 'Observações são obrigatórias'}), 400
    
    consultas = carregar_dados('consultas')
    consulta_index = next((i for i, c in enumerate(consultas) if c['id'] == consulta_id), None)
    
    if consulta_index is None:
        return jsonify({'error': 'Consulta não encontrada'}), 404
    
    consulta = consultas[consulta_index]
    
    # Verificar se o profissional pode atender
    if consulta['profissional'] != request.user_id:
        return jsonify({'error': 'Esta consulta não é sua para atender'}), 403
    
    if consulta['status'] != 'AGENDADA':
        return jsonify({'error': 'Consulta não está agendada'}), 400
    
    # Atualizar status
    consultas[consulta_index]['status'] = 'REALIZADA'
    salvar_dados('consultas', consultas)
    
    # Criar atendimento
    atendimentos = carregar_dados('atendimentos')
    novo_atendimento = {
        'consulta': consulta_id,
        'profissional': request.user_id,
        'paciente': consulta['paciente'],
        'data': datetime.now().isoformat(),
        'observacoes': data['observacoes']
    }
    atendimentos.append(novo_atendimento)
    salvar_dados('atendimentos', atendimentos)
    
    # Adicionar ao prontuário
    prontuarios = carregar_dados('prontuarios')
    novo_prontuario = {
        'paciente': consulta['paciente'],
        'data': datetime.now().isoformat(),
        'descricao': data['observacoes'],
        'profissional': request.user_id,
        'consulta': consulta_id
    }
    prontuarios.append(novo_prontuario)
    salvar_dados('prontuarios', prontuarios)
    
    notificar(consulta['paciente'], 'Atendimento realizado')
    
    return jsonify({
        'message': 'Atendimento registrado',
        'atendimento': novo_atendimento
    }), 201