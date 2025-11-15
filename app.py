import os
import logging

from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer as Serializer
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)

logging.basicConfig(level=logging.INFO)

# Clave secreta para sesiones
app.secret_key = os.getenv("SECRET_KEY", "advpjsh")


def create_user_collection():
    """Inicializa la conexión a MongoDB y devuelve la colección de usuarios."""
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        # Permite desarrollo local sin variables de entorno configuradas
        mongo_db = os.getenv("MONGO_DB_NAME", "cchanitur_db_user")
        mongo_uri = f"mongodb://localhost:27017/{mongo_db}"
        app.logger.warning(
            "MONGO_URI no está configurado. Se usará una instancia local de MongoDB (%s)",
            mongo_uri,
        )

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db_name = os.getenv("MONGO_DB_NAME", "cchanitur_db_user")
        collection_name = os.getenv("MONGO_COLLECTION_NAME", "USUARIOS")
        return client[db_name][collection_name]
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        app.logger.error("No se pudo conectar a MongoDB: %s", exc)
        return None


collection = create_user_collection()

# Configuración de SendGrid
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL')

# Serializador para crear y verificar tokens
serializer = Serializer(app.secret_key, salt='password-reset-salt')


def ensure_collection_available():
    """Verifica que la colección esté disponible antes de operar."""
    if collection is None:
        flash(
            "No se puede establecer conexión con la base de datos en este momento. Intenta nuevamente más tarde.",
            "error",
        )
        return False
    return True

# Función para enviar correos
def enviar_email(destinatario, asunto, cuerpo):
    if not SENDGRID_API_KEY or not SENDGRID_FROM_EMAIL:
        app.logger.warning("SendGrid no está configurado. Mensaje no enviado: %s", asunto)
        return

    mensaje = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=destinatario,
        subject=asunto,
        html_content=cuerpo
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(mensaje)
        print(f"Correo enviado con éxito! Status code: {response.status_code}")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

@app.route('/')
def home():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('pagina_principal'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        if not ensure_collection_available():
            return render_template('register.html')

        usuario = request.form['usuario']
        email = request.form['email']
        contrasena = request.form['contrasena']

        # Verificar si el correo ya está registrado
        if collection.find_one({'email': email}):
            flash("El correo electrónico ya está registrado.", "error")
            return redirect(url_for('registro'))

        # Hashear la contraseña
        hashed_password = bcrypt.generate_password_hash(contrasena).decode('utf-8')

        # Insertar usuario en la base de datos
        collection.insert_one({
            'usuario': usuario,
            'email': email,
            'contrasena': hashed_password
        })
        
        session['usuario'] = usuario
        return redirect(url_for('pagina_principal'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if not ensure_collection_available():
            return render_template('login.html')

        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        # Buscar al usuario en la base de datos
        user = collection.find_one({'usuario': usuario})
        
        # Verificar si las credenciales son correctas
        if user and bcrypt.check_password_hash(user['contrasena'], contrasena):
            session['usuario'] = usuario
            return redirect(url_for('pagina_principal'))
        else:
            flash("Usuario o contraseña incorrectos.", "error")
            return render_template('login.html')

    return render_template('login.html')

@app.route('/pagina_principal')
def pagina_principal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', usuario=session['usuario'])

@app.route('/mi_perfil')
def mi_perfil():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if not ensure_collection_available():
        return redirect(url_for('pagina_principal'))

    usuario = session['usuario']
    user_data = collection.find_one({'usuario': usuario})
    return render_template('mi_perfil.html', usuario=user_data['usuario'], email=user_data['email'])

@app.route('/recuperar_contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if request.method == 'POST':
        if not ensure_collection_available():
            return render_template('recuperar_contrasena.html')

        email = request.form['email']
        usuario = collection.find_one({'email': email})

        if usuario:
            token = serializer.dumps(email, salt='password-reset-salt')
            enlace = url_for('restablecer_contrasena', token=token, _external=True)
            asunto = "Recuperación de contraseña"
            cuerpo = f"""
            <p>Hola, hemos recibido una solicitud para restablecer tu contraseña.</p>
            <p>Si no has solicitado este cambio, ignora este mensaje.</p>
            <p>Para restablecer tu contraseña, haz clic en el siguiente enlace:</p>
            <a href="{enlace}">Restablecer contraseña</a>
            """
            enviar_email(email, asunto, cuerpo)
            flash("Te hemos enviado un correo para recuperar tu contraseña.", "success")
        else:
            flash("El correo electrónico no está registrado.", "error")

    return render_template('recuperar_contrasena.html')

@app.route('/restablecer_contrasena/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash("El enlace de restablecimiento ha caducado o es inválido.", "error")
        return redirect(url_for('recuperar_contrasena'))

    if request.method == 'POST':
        if not ensure_collection_available():
            return render_template('restablecer_contrasena.html')

        nueva_contrasena = request.form['nueva_contrasena']
        hashed_password = bcrypt.generate_password_hash(nueva_contrasena).decode('utf-8')
        collection.update_one({'email': email}, {'$set': {'contrasena': hashed_password}})
        flash("Tu contraseña ha sido restablecida con éxito.", "success")
        return redirect(url_for('login'))

    return render_template('restablecer_contrasena.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True) 