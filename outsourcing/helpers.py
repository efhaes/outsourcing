# pip install Pillow (sudah pasti ada), django-imagekit

from PIL import Image
import io
from django.core.files.uploadedfile import InMemoryUploadedFile

def compress_image(image_field, max_size=(800, 800), quality=75):
    """
    Kompress gambar sebelum disimpan.
    max_size: resolusi maksimal (auto-resize, aspect ratio tetap terjaga)
    quality: 75 sudah cukup untuk foto lapangan
    """
    img = Image.open(image_field)
    
    # Convert RGBA/P ke RGB (JPEG tidak support transparency)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    img.thumbnail(max_size, Image.LANCZOS)  # resize, aspect ratio aman
    
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)
    
    return InMemoryUploadedFile(
        output, 'ImageField',
        f"{image_field.name.split('.')[0]}.jpg",
        'image/jpeg',
        output.getbuffer().nbytes,
        None
    )