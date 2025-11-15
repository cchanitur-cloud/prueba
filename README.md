# Prueba

Aplicación Flask simple con autenticación basada en MongoDB, recuperación de contraseñas por correo y vistas protegidas. Este repositorio incluye estilos básicos para la pantalla de login/registro y una página principal.

## Requisitos

- Python 3.10+
- MongoDB (local o servicio compatible con MongoDB Atlas)
- Cuenta de SendGrid si quieres enviar correos reales

Instala las dependencias del proyecto:

```bash
pip install -r requirements.txt
```

## Configuración

1. Copia el archivo `.env.example` a `.env`:
   ```bash
   cp .env.example .env
   ```
2. Completa las variables de entorno:
   - `SECRET_KEY`: clave para las sesiones de Flask.
   - `MONGO_URI`: cadena de conexión completa a tu base de datos. Si la omites, se intentará usar una instancia local en `mongodb://localhost:27017/`.
   - `MONGO_DB_NAME` y `MONGO_COLLECTION_NAME`: nombres de la base de datos y la colección.
   - `SENDGRID_API_KEY` y `SENDGRID_FROM_EMAIL`: credenciales de SendGrid para enviar correos de recuperación (opcional, el sistema funciona sin correo enviando solo alertas en consola).

## Ejecución

```bash
flask --app app run --debug
```

La aplicación estará disponible en `http://127.0.0.1:5000/`.

## Solución de problemas de conexión a MongoDB

- Verifica que `MONGO_URI` sea correcto y accesible desde donde ejecutas la app.
- Si usas MongoDB Atlas, asegúrate de permitir la IP pública de tu máquina en la lista de IPs permitidas del clúster.
- El archivo `app.py` valida la conexión con `client.admin.command("ping")`. Si no puede conectarse, verás un mensaje en consola y en la interfaz aparecerá un aviso para el usuario.
