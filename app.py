from datetime import datetime,timedelta
from flask import Flask, jsonify, request , session
from flask_cors import CORS
import requests 
from flask_sqlalchemy import SQLAlchemy
import os 
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
#CORS(app)

CORS(app, resources={r"/api/*": {"origins": "http://127.0.0.1:5500"}})


# Configuración de la base de datos MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://uuv6ikhjpysqbhud:c8MR2xZMJex3fl52ckIw@biuyxdngu1e0yt5ngk5f-mysql.services.clever-cloud.com:3306/biuyxdngu1e0yt5ngk5f'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#JWT
app.config['JWT_SECRET_KEY'] = 'CONTROL'  # Cambia esto por una clave segura
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=4)  # Duración del token a 4 horas

jwt = JWTManager(app)

db = SQLAlchemy(app)


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


# Rutas de la API

# ... (todas las rutas anteriores sin cambios)

@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    current_user = get_jwt_identity()
    usuarios = Usuario.query.all()
    return jsonify([{"id_usuario": u.id_usuario,
                     "usuario": u.usuario,
                     "nombre": u.nombre} for u in usuarios])




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



@app.route('/api/login', methods=['GET'])
def get_login():
    login = Login.query.all()
    return jsonify([{"id_login":l.id_login,
                    "id_usuario": l.id_usuario,
                     "usuario": l.usuario,
                     "contraseña":l.contraseña} for l in login])
      


# Ruta de Login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    usuario = data.get('usuario')
    contraseña = data.get('contraseña')

    if not usuario or not contraseña:
        return jsonify({"message": "Faltan datos"}), 400

    # Busca el usuario en la base de datos
    login = Login.query.filter_by(usuario=usuario).first()

    if login and login.contraseña == contraseña:
        # Consulta el usuario en la tabla 'usuarios' usando el id_usuario del objeto 'login'
        usuario_obj = Usuario.query.filter_by(id_usuario=login.id_usuario).first()

        # Crear el token de acceso
        access_token = create_access_token(identity=usuario)

        # Registrar en la tabla `usuarios_logueados`
        nuevo_log = UsuarioLogueado(
            id_usuario=usuario_obj.id_usuario,
            nombre_usuario=usuario_obj.nombre,  # Almacenar el nombre del usuario
            estado='en línea'
        )
        db.session.add(nuevo_log)
        db.session.commit()

        return jsonify(token=access_token), 200
    else:
        return jsonify({"message": "Credenciales incorrectas"}), 401


# Ruta de Logout
@app.route('/api/logout', methods=['POST'])
def logout():
    # Obtener el nombre de usuario a partir del token de acceso
    usuario = get_jwt_identity()

    # Consultar el usuario en la tabla `Login` para obtener su ID
    login = Login.query.filter_by(usuario=usuario).first()
    if not login:
        return jsonify({"message": "Usuario no encontrado"}), 404

    # Crear un nuevo registro en `usuarios_logueados` con estado 'desconectado'
    nuevo_log = UsuarioLogueado(
        id_usuario=login.id_usuario,
        nombre_usuario=login.usuario,  # Asegúrate de que `usuario` contiene el nombre del usuario
        estado='desconectado'
    )
    db.session.add(nuevo_log)
    db.session.commit()

    return jsonify({"message": "Cierre de sesión exitoso"}), 200


@app.route('/api/sensores', methods=['GET'])
def get_sensores():
    sensores = Sensor.query.all()
    return jsonify([{"id_sensor": s.id_sensor,
                     "nombre_sensor": s.nombre_sensor} for s in sensores])

@app.route('/api/lectura_gas', methods=['GET'])
def get_lectura_gas():
    lecturas = Lectura.query.all()
    return jsonify([{"id_lectura": l.id_lectura,
                     "id_sensor": l.id_sensor,
                     "valor_gas": l.valor_gas,
                     "fecha": l.fecha,
                     "estado_gas": l.estado_gas} for l in lecturas])

@app.route('/api/lectura_led', methods=['GET'])
def get_lectura_get():
    lecturas = LecturaLed.query.all()
    return jsonify([{"id_lectura": l.id_lectura,
                     "id_usuario": l.id_usuario,
                     "id_sensor": l.id_sensor,
                     "fecha": l.fecha,
                     "valor_led": l.valor_led} for l in lecturas])



@app.route('/api/controlar_led', methods=['POST'])
def controlar_led():
    try:
        data = request.get_json()

        # Verificación de parámetros
        if 'state' not in data:
            return jsonify({"error": "Falta el parámetro 'state'"}), 400

        # Obtener el estado deseado del LED
        led_state = data['state']

        # Validación estricta del estado
        if led_state not in ["on", "off"]:
            return jsonify({"error": "El estado debe ser 'on' o 'off'"}), 400

        # Obtener el nombre del usuario desde el JWT
        nombre_usuario = get_jwt_identity()

        # Obtener el ID del usuario desde la base de datos
        usuario = Usuario.query.filter_by(usuario=nombre_usuario).first()
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        id_usuario = usuario.id_usuario
        valor_salida = 1 if led_state == "on" else 0
        id_sensor = 2  # Asumido que el LED tiene el ID de sensor 2
        
        # Registrar el estado del LED en la base de datos
        nueva_lectura = LecturaLed(
            id_sensor=id_sensor,
            id_usuario=id_usuario,
            valor_salida=valor_salida
        )
        db.session.add(nueva_lectura)
        db.session.commit()

        return jsonify({
            "message": f"LED {led_state} y lectura registrada",
            "estado_actual": valor_salida
        }), 200

    except Exception as e:
        return jsonify({"error": "Error al procesar la solicitud", "detalles": str(e)}), 500


@app.route('/api/lectura_sensor_gas', methods=['GET'])
def obtener_lectura_sensor_gas():
    try:
        # Aquí asumimos el id del sensor
        # si tienes varios sensores, puedes ajustar esta consulta
        sensor_gas_id = 1  # Cambia esto según tu configuración
        lecturas = Lectura.query.filter_by(id_sensor=sensor_gas_id).order_by(Lectura.fecha.desc()).first()
        
        if lecturas:
            return jsonify({
                'valor_gas': lecturas.valor_gas,
                'estado_gas': lecturas.estado_gas,
                'fecha': lecturas.fecha.strftime('%Y-%m-%d %H:%M:%S')
            }), 200
        else:
            return jsonify({'mensaje': 'No se encontraron lecturas para el sensor de gas.'}), 404

    except Exception as e:
        return jsonify({'mensaje': f'Error al obtener la lectura: {str(e)}'}), 500


@app.route('/api/lecturas', methods=['POST'])
def crear_lectura():
    data = request.get_json()
    if 'valor_led' not in data or 'id_sensor' not in data or 'id_usuario' not in data:
        return jsonify({"mensaje": "Faltan datos"}), 400

    try:
        valor_led = float(data['valor_led'])
        id_sensor = int(data['id_sensor'])
        id_usuario = int(data['id_usuario'])
    except (ValueError, TypeError) as e:
        return jsonify({"mensaje": "Formato incorrecto en los datos", "error": str(e)}), 400

    nueva_lectura = LecturaLed(
        valor_led=valor_led,
        fecha=datetime.now(),
        id_sensor=id_sensor,
        id_usuario=id_usuario
    )

    try:
        db.session.add(nueva_lectura)
        db.session.commit()
        return jsonify({"mensaje": "Lectura guardada exitosamente"}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar la lectura: {str(e)}")  # Agrega esta línea para depuración
        return jsonify({"mensaje": f"Error al guardar la lectura: {str(e)}"}), 500



@app.route('/api/lectura_gas', methods=['POST'])
def registrar_lectura_gas():
    # Obtener datos del cuerpo de la solicitud JSON
    print("Recibiendo datos...")
    data = request.json
    print(data)  # Ver qué se está recibiendo
    valor_gas = data.get('valor_gas')
    estado_gas = data.get('estado_gas')

    if valor_gas is not None and estado_gas in ['Normal', 'Peligro']:
        nueva_lectura = Lectura(id_sensor=1, valor_gas=valor_gas, estado_gas=estado_gas)  # Asumiendo que el id_sensor para gas es 1
        db.session.add(nueva_lectura)
        db.session.commit()

        return jsonify({'mensaje': 'Lectura registrada correctamente'}), 201
    else:
        return jsonify({'error': 'Datos inválidos'}), 400


@app.route('/api/led_app', methods=['POST'])
def led_registro():
    try:
        data = request.get_json()
        
        # Validar que el campo 'estado' esté presente y sea válido
        if 'estado' not in data or data['estado'] not in [0, 1, "0", "1"]:
            return jsonify({"error": "El parámetro 'estado' debe ser 0 o 1"}), 400
        
        # Convertir estado a entero (0 o 1)
        valor_salida = int(data['estado'])
        
        # Actualizar estado global del LED
        global led_state
        led_state = "on" if valor_salida == 1 else "off"
        
        # Crear una nueva lectura
        nueva_lectura = LecturaLed(
            id_sensor=2,  # ID 2 para el LED según tu esquema
            id_usuario=4,  # ID del usuario (ajústalo según corresponda)
            valor_salida=valor_salida
        )
        
        # Guardar en la base de datos
        db.session.add(nueva_lectura)
        db.session.commit()
        
        return jsonify({
            "mensaje": f"Estado del LED registrado correctamente ({led_state})",
            "valor": valor_salida
        }), 200
    
    except Exception as e:
        return jsonify({"error": "Error al registrar estado del LED", "detalles": str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
