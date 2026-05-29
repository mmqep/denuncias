# cloud_storage.py
import boto3
import uuid
import io
from botocore.client import Config
from botocore.exceptions import ClientError
from flask import current_app
from PIL import Image

def get_b2_client():
    """Retorna cliente configurado para Backblaze B2"""
    return boto3.client(
        's3',
        endpoint_url=current_app.config['B2_ENDPOINT_URL'],
        aws_access_key_id=current_app.config['B2_ACCOUNT_ID'],
        aws_secret_access_key=current_app.config['B2_APPLICATION_KEY'],
        config=Config(signature_version='s3v4')
    )

def comprimir_imagen(archivo_bytes, nombre_original, calidad=75, max_width=1500):
    """Comprime una imagen antes de subirla a B2"""
    extension = nombre_original.rsplit('.', 1)[1].lower() if '.' in nombre_original else ''
    
    if extension not in ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif']:
        return archivo_bytes, extension
    
    try:
        img = Image.open(io.BytesIO(archivo_bytes))
        
        # Convertir a RGB si tiene transparencia
        if img.mode in ('RGBA', 'LA', 'P'):
            fondo = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            fondo.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = fondo
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Redimensionar si es necesario
        if img.width > max_width:
            ratio = max_width / img.width
            nuevo_alto = int(img.height * ratio)
            img = img.resize((max_width, nuevo_alto), Image.Resampling.LANCZOS)
        
        # Guardar comprimido
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=calidad, optimize=True)
        
        return output.getvalue(), 'jpg'
        
    except Exception:
        return archivo_bytes, extension

def subir_archivo_b2(archivo, nombre_original):
    """Sube un archivo a Backblaze B2 con compresión automática de imágenes"""
    archivo.seek(0)
    archivo_bytes = archivo.read()
    
    archivo_comprimido, extension_salida = comprimir_imagen(archivo_bytes, nombre_original)
    
    s3_client = get_b2_client()
    
    nombre_archivo = uuid.uuid4().hex
    extension_original = nombre_original.rsplit('.', 1)[1].lower() if '.' in nombre_original else ''
    
    if extension_salida == 'jpg':
        nombre_archivo += ".jpg"
        content_type = 'image/jpeg'
    else:
        nombre_archivo += f".{extension_original}"
        content_type = 'application/pdf' if extension_original == 'pdf' else 'application/octet-stream'
    
    try:
        s3_client.upload_fileobj(
            io.BytesIO(archivo_comprimido),
            current_app.config['B2_BUCKET_NAME'],
            nombre_archivo,
            ExtraArgs={'ContentType': content_type, 'ACL': 'private'}
        )
        
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': current_app.config['B2_BUCKET_NAME'], 'Key': nombre_archivo},
            ExpiresIn=3600
        )
        
        return url, nombre_archivo
        
    except ClientError:
        return None, None

def obtener_url_archivo_b2(nombre_archivo, expiracion_segundos=3600):
    """Genera URL prefirmada para acceder a un archivo privado"""
    try:
        s3_client = get_b2_client()
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': current_app.config['B2_BUCKET_NAME'], 'Key': nombre_archivo},
            ExpiresIn=expiracion_segundos
        )
    except ClientError:
        return None