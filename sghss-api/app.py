from flask import Flask, jsonify
from flask_cors import CORS
import os
from config import Config

# Importar blueprints
from auth.routes import auth_bp
from api.pacientes import pacientes_bp
from api.consultas import consultas_bp

app = Flask(__name__)
CORS(app)

# Configuração
app.config.from_object(Config)

# Criar diretório database se não existir
os.makedirs(Config.DATA_DIR, exist_ok=True)

# Inicializar arquivos JSON
for nome, arquivo in Config.FILES.items():
    if not os.path.exists(arquivo):
        with open(arquivo, 'w', encoding='utf-8') as f:
            import json
            json.dump([], f, indent=4, ensure_ascii=False)

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(pacientes_bp)
app.register_blueprint(consultas_bp)

# Health check
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'online',
        'timestamp': '2024-01-15T10:30:00',
        'version': '2.0.0',
        'endpoints': {
            'auth': [
                'POST /auth/login', 
                'POST /auth/register', 
                'GET /auth/me'
            ],
            'pacientes': [
                'GET /pacientes', 
                'POST /pacientes', 
                'GET /pacientes/{id}',
                'PUT /pacientes/{id}',
                'GET /pacientes/{id}/consultas'
            ],
            'consultas': [
                'GET /consultas', 
                'POST /consultas', 
                'PUT /consultas/{id}',
                'DELETE /consultas/{id}', 
                'POST /consultas/{id}/atender'
            ]
        },
        'notas': {
            'autenticacao': 'Todos os endpoints (exceto /auth/* e /health) requerem token JWT no header Authorization: Bearer {token}',
            'perfis': {
                'ADMIN': 'Acesso completo a todos os endpoints',
                'PROFISSIONAL': 'Pode gerenciar suas consultas e pacientes relacionados',
                'PACIENTE': 'Acesso apenas aos próprios dados e consultas'
            },
            'delete': ''
        }
    }), 200

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("API REST TELEMED - Versão 2.1") 
    print("=" * 50)
    print("\nEndpoints principais:")
    print("  POST   /auth/login        - Login (retorna JWT)")
    print("  POST   /auth/register     - Registro")
    print("  GET    /auth/me           - Meus dados")
    print("  GET    /pacientes         - Listar pacientes (ADMIN)")
    print("  POST   /pacientes         - Criar paciente (ADMIN)")
    print("  GET    /pacientes/{id}    - Ver paciente")
    print("  PUT    /pacientes/{id}    - Atualizar paciente")
    print("  GET    /consultas         - Listar consultas")
    print("  POST   /consultas         - Agendar consulta")
    print("  PUT    /consultas/{id}    - Atualizar consulta")
    print("  DELETE /consultas/{id}    - Deletar consulta (NOVO)") 
    print("  POST   /consultas/{id}/atender - Realizar atendimento")
    print("  GET    /health            - Health check")
    print("\nDocumentação completa: http://localhost:5000/health")
    print("=" * 50)
    
    app.run(debug=True, port=5000, host='0.0.0.0')