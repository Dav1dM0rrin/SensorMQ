from datetime import datetime
from flask import Flask, jsonify, request , session
from flask_cors import CORS
import requests 
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
#CORS(app)

CORS(app, resources={r"/api/*": {"origins": "http://127.0.0.1:5500"}})


# Configuración de la base de datos MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://uuv6ikhjpysqbhud:c8MR2xZMJex3fl52ckIw@biuyxdngu1e0yt5ngk5f-mysql.services.clever-cloud.com:3306/biuyxdngu1e0yt5ngk5f'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
app.secret_key = 'control'  # Cambia esto por una clave secreta adecuada


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

# Rutas de la API

# ... (todas las rutas anteriores sin cambios)

@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
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
      

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    usuario = data.get('usuario')
    contraseña = data.get('contraseña')

    if not usuario or not contraseña:
        return jsonify({"message": "Faltan datos"}), 400

    # Consultar la base de datos para el usuario
    login = Login.query.filter_by(usuario=usuario).first()

    # Verificar credenciales
    if login and login.contraseña == contraseña:
        # Almacenar id_usuario en la sesión
        session['id_usuario'] = login.id_usuario
        
        # IP del ESP32
        esp32_ip = '192.168.1.75'  # Cambia esto si es necesario
        
        return jsonify({
            "message": "Login exitoso",
            "id_usuario": login.id_usuario,
            "esp32_ip": esp32_ip
        }), 200
    else:
        return jsonify({"message": "Credenciales incorrectas"}), 401

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
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'accion' not in data:
            return jsonify({"message": "No se recibió acción"}), 400
        
        accion = data['accion']
        esp32_ip = 'http://192.168.1.75/controlar'  # Cambia esto si es necesario

        if accion == 'encender':
            response = requests.post(esp32_ip, data={"comando": "LED_ON"})
            if response.status_code == 200:
                # Registra la acción en la base de datos
                return jsonify({"message": "LED Encendido"}), 200
            else:
                return jsonify({"message": "Error al encender el LED"}), 500
        elif accion == 'apagar':
            response = requests.post(esp32_ip, data={"comando": "LED_OFF"})
            if response.status_code == 200:
                # Registra la acción en la base de datos
                return jsonify({"message": "LED Apagado"}), 200
            else:
                return jsonify({"message": "Error al apagar el LED"}), 500
        else:
            return jsonify({"message": "Acción no reconocida"}), 400



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



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
