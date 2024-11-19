from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://127.0.0.1:5500"}})

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://uuv6ikhjpysqbhud:c8MR2xZMJex3fl52ckIw@biuyxdngu1e0yt5ngk5f-mysql.services.clever-cloud.com:3306/biuyxdngu1e0yt5ngk5f'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(50), nullable=True)

class Login(db.Model):
    __tablename__ = 'login'
    id_login = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    usuario = db.Column(db.String(50), nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)

class Sensor(db.Model):
    __tablename__ = 'sensores'
    id_sensor = db.Column(db.Integer, primary_key=True)
    nombre_sensor = db.Column(db.String(50), nullable=False)
    tipo_sensor = db.Column(db.String(50), nullable=False)

class Lectura(db.Model):
    __tablename__ = 'lectura_gas'
    id_lectura = db.Column(db.Integer, primary_key=True)
    id_sensor = db.Column(db.Integer, db.ForeignKey('sensores.id_sensor'), nullable=False)
    valor_gas = db.Column(db.Float, nullable=False)
    estado_gas = db.Column(db.Enum('Normal', 'Peligro'), nullable=False)
    fecha = db.Column(db.DateTime, default=db.func.current_timestamp())

class LecturaLed(db.Model):
    __tablename__ = 'lecturas_led'
    id_lectura = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    id_sensor = db.Column(db.Integer, db.ForeignKey('sensores.id_sensor'), nullable=False)
    valor_led = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class UsuarioLogueado(db.Model):
    __tablename__ = 'usuarios_logueados'
    id_log = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    nombre_usuario = db.Column(db.String(50), nullable=False)
    hora_login = db.Column(db.DateTime, default=datetime.now)
    estado = db.Column(db.Enum('en línea', 'desconectado'), nullable=False)

# Routes
@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    usuarios = Usuario.query.all()
    return jsonify([{
        "id_usuario": u.id_usuario,
        "usuario": u.usuario,
        "nombre": u.nombre
    } for u in usuarios])

@app.route('/api/usuarios', methods=['POST'])
def add_usuario():
    if not request.json or 'usuario' not in request.json or 'contraseña' not in request.json:
        return jsonify({'error': 'Datos inválidos'}), 400

    nuevo_usuario = Usuario(
        usuario=request.json['usuario'],
        contraseña=request.json['contraseña'],
        nombre=request.json.get('nombre', '')
    )
    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({'id_usuario': nuevo_usuario.id_usuario}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    usuario = data.get('usuario')
    contraseña = data.get('contraseña')

    if not usuario or not contraseña:
        return jsonify({"message": "Faltan datos"}), 400

    login = Login.query.filter_by(usuario=usuario).first()

    if login and login.contraseña == contraseña:
        usuario_obj = Usuario.query.filter_by(id_usuario=login.id_usuario).first()
        
        nuevo_log = UsuarioLogueado(
            id_usuario=usuario_obj.id_usuario,
            nombre_usuario=usuario_obj.nombre,
            estado='en línea'
        )
        db.session.add(nuevo_log)
        db.session.commit()

        return jsonify({
            "id_usuario": usuario_obj.id_usuario,
            "nombre": usuario_obj.nombre,
            "message": "Login exitoso"
        }), 200
    else:
        return jsonify({"message": "Credenciales incorrectas"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    data = request.get_json()
    id_usuario = data.get('id_usuario')
    
    if not id_usuario:
        return jsonify({"message": "ID de usuario requerido"}), 400

    nuevo_log = UsuarioLogueado(
        id_usuario=id_usuario,
        nombre_usuario=Usuario.query.get(id_usuario).nombre,
        estado='desconectado'
    )
    db.session.add(nuevo_log)
    db.session.commit()

    return jsonify({"message": "Cierre de sesión exitoso"}), 200

@app.route('/api/estado_login', methods=['GET'])
def get_estado_login():
    ultimo_log = UsuarioLogueado.query.order_by(UsuarioLogueado.hora_login.desc()).first()
    if ultimo_log:
        return jsonify({
            "estado": ultimo_log.estado,
            "usuario": ultimo_log.nombre_usuario,
            "ultima_actualizacion": ultimo_log.hora_login.isoformat()
        })
    return jsonify({"estado": "desconectado"})

@app.route('/api/lectura_gas', methods=['POST'])
def registrar_lectura_gas():
    data = request.json
    valor_gas = data.get('valor_gas')
    estado_gas = data.get('estado_gas')

    if valor_gas is not None and estado_gas in ['Normal', 'Peligro']:
        nueva_lectura = Lectura(
            id_sensor=1,
            valor_gas=valor_gas,
            estado_gas=estado_gas
        )
        db.session.add(nueva_lectura)
        db.session.commit()
        return jsonify({'mensaje': 'Lectura registrada correctamente'}), 201
    return jsonify({'error': 'Datos inválidos'}), 400

@app.route('/api/lectura_gas', methods=['GET'])
def get_ultima_lectura_gas():
    ultima_lectura = Lectura.query.order_by(Lectura.fecha.desc()).first()
    if ultima_lectura:
        return jsonify({
            'valor_gas': ultima_lectura.valor_gas,
            'estado_gas': ultima_lectura.estado_gas,
            'fecha': ultima_lectura.fecha.isoformat()
        })
    return jsonify({'mensaje': 'No hay lecturas disponibles'}), 404

@app.route('/api/led', methods=['POST'])
def controlar_led():
    data = request.get_json()
    if 'estado' not in data or 'id_usuario' not in data:
        return jsonify({"error": "Faltan datos"}), 400

    nueva_lectura = LecturaLed(
        id_sensor=2,
        id_usuario=data['id_usuario'],
        valor_led=1 if data['estado'] else 0
    )
    db.session.add(nueva_lectura)
    db.session.commit()

    return jsonify({
        "mensaje": "Estado del LED actualizado",
        "estado": "encendido" if data['estado'] else "apagado"
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)