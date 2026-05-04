from PIL import Image, ImageOps
import io
from django.core.files.uploadedfile import InMemoryUploadedFile

def compress_image(image_field, max_size=(800, 800), quality=75):
    img = Image.open(image_field)
    
    # Fix orientasi dari EXIF (foto HP sering miring kalau tidak ini)
    img = ImageOps.exif_transpose(img)
    
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    img.thumbnail(max_size, Image.LANCZOS)
    
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