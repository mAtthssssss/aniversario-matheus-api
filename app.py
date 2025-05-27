from flask import Flask, request, send_file, jsonify
import os
import sys
import random
from PIL import Image, ImageOps
from io import BytesIO
import base64
import requests

app = Flask(__name__)

# Configurações
UPLOAD_FOLDER = '/tmp/aniversario_matheus'
TEMPLATES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Criar diretórios se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_and_crop_profile_image(image, output_size, output_shape="circle"):
    """
    Redimensiona e recorta a imagem do perfil para o tamanho desejado.
    
    Args:
        image (PIL.Image): Objeto de imagem PIL
        output_size (tuple): Tamanho desejado (largura, altura)
        output_shape (str): Formato de saída ("circle" ou "rounded_square")
        
    Returns:
        PIL.Image: Imagem processada
    """
    try:
        # Converter para RGB se for RGBA
        if image.mode == 'RGBA':
            image = image.convert('RGB')
            
        # Calcular proporção para manter o aspecto
        width, height = image.size
        if width > height:
            new_width = int(width * output_size[1] / height)
            new_height = output_size[1]
        else:
            new_height = int(height * output_size[0] / width)
            new_width = output_size[0]
            
        # Redimensionar mantendo a proporção
        img = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Recortar o centro
        left = (new_width - output_size[0]) // 2
        top = (new_height - output_size[1]) // 2
        right = left + output_size[0]
        bottom = top + output_size[1]
        img = img.crop((left, top, right, bottom))
        
        # Criar máscara para formato circular ou quadrado arredondado
        mask = Image.new('L', output_size, 0)
        if output_shape == "circle":
            # Criar máscara circular
            from PIL import ImageDraw
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, output_size[0], output_size[1]), fill=255)
        else:
            # Criar máscara de quadrado arredondado
            from PIL import ImageDraw
            radius = min(output_size) // 8  # Raio dos cantos arredondados
            draw = ImageDraw.Draw(mask)
            draw.rectangle((radius, 0, output_size[0] - radius, output_size[1]), fill=255)
            draw.rectangle((0, radius, output_size[0], output_size[1] - radius), fill=255)
            draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=255)
            draw.pieslice((output_size[0] - radius * 2, 0, output_size[0], radius * 2), 270, 360, fill=255)
            draw.pieslice((0, output_size[1] - radius * 2, radius * 2, output_size[1]), 90, 180, fill=255)
            draw.pieslice((output_size[0] - radius * 2, output_size[1] - radius * 2, 
                          output_size[0], output_size[1]), 0, 90, fill=255)
        
        # Aplicar máscara
        img.putalpha(mask)
        
        return img
    except Exception as e:
        print(f"Erro ao processar imagem de perfil: {e}")
        return None

def overlay_profile_on_template(profile_img, template_path, output_path=None):
    """
    Sobrepõe a imagem de perfil no template.
    
    Args:
        profile_img (PIL.Image): Imagem de perfil processada
        template_path (str): Caminho para o template
        output_path (str, optional): Caminho para salvar a imagem final
        
    Returns:
        PIL.Image: Imagem final processada
    """
    try:
        # Abrir o template
        template = Image.open(template_path)
        
        # Determinar a posição para a imagem de perfil com base no template
        if "template1" in template_path:
            # Posição para o template 1 (área quadrada no centro)
            position = (
                (template.width - profile_img.width) // 2,
                (template.height - profile_img.height) // 2 - 50  # Ajuste vertical
            )
        else:
            # Posição para o template 2 (área circular no centro)
            position = (
                (template.width - profile_img.width) // 2,
                (template.height - profile_img.height) // 2 - 100  # Ajuste vertical
            )
        
        # Criar uma cópia do template para não modificar o original
        result = template.copy()
        
        # Sobrepor a imagem de perfil
        result.paste(profile_img, position, profile_img)
        
        # Salvar o resultado se um caminho for fornecido
        if output_path:
            result.save(output_path, quality=95)
            
        return result
    except Exception as e:
        print(f"Erro ao sobrepor imagem no template: {e}")
        return None

def process_image(input_image, template_index=None):
    """
    Processa a imagem de entrada e gera a imagem personalizada.
    
    Args:
        input_image (PIL.Image): Objeto de imagem PIL
        template_index (int, optional): Índice do template a ser usado (1 ou 2)
        
    Returns:
        PIL.Image: Imagem processada
    """
    try:
        # Listar templates disponíveis
        templates = [f for f in os.listdir(TEMPLATES_FOLDER) if f.startswith("template") and f.endswith(".png")]
        
        if not templates:
            return None, "Erro: Nenhum template encontrado."
        
        # Selecionar template específico ou aleatório
        if template_index is not None and 1 <= template_index <= len(templates):
            template_file = f"template{template_index}.png"
        else:
            template_file = random.choice(templates)
        
        template_path = os.path.join(TEMPLATES_FOLDER, template_file)
        
        # Determinar tamanho e forma com base no template
        if "template1" in template_path:
            # Template 1 usa formato quadrado arredondado
            profile_size = (600, 600)
            profile_shape = "rounded_square"
        else:
            # Template 2 usa formato circular
            profile_size = (500, 500)
            profile_shape = "circle"
        
        # Processar imagem de perfil
        profile_img = resize_and_crop_profile_image(
            input_image, profile_size, profile_shape
        )
        
        if profile_img is None:
            return None, "Erro ao processar imagem de perfil."
        
        # Sobrepor no template
        result_img = overlay_profile_on_template(profile_img, template_path)
        
        if result_img is None:
            return None, "Erro ao sobrepor imagem no template."
        
        return result_img, None
    
    except Exception as e:
        return None, f"Erro ao processar imagem: {e}"

@app.route('/')
def index():
    return """
    <h1>API de Personalização de Fotos - Aniversário do Matheus</h1>
    <p>Use o endpoint /process para enviar uma imagem e receber a versão personalizada.</p>
    <form action="/process" method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <input type="submit" value="Processar">
    </form>
    """

@app.route('/process', methods=['POST'])
def process():
    # Verificar se há arquivo na requisição
    if 'file' not in request.files and 'image' not in request.form and 'image_url' not in request.form:
        return jsonify({'error': 'Nenhuma imagem enviada'}), 400
    
    template_index = request.form.get('template', None)
    if template_index:
        try:
            template_index = int(template_index)
        except ValueError:
            template_index = None
    
    # Processar imagem do arquivo
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        if file and allowed_file(file.filename):
            try:
                # Ler imagem diretamente do arquivo
                img = Image.open(file)
                
                # Processar imagem
                result_img, error = process_image(img, template_index)
                
                if error:
                    return jsonify({'error': error}), 500
                
                # Preparar resposta
                img_io = BytesIO()
                result_img.save(img_io, 'JPEG', quality=85)
                img_io.seek(0)
                
                # Verificar formato de resposta solicitado
                response_format = request.form.get('response_format', 'file')
                
                if response_format == 'base64':
                    # Retornar como base64
                    img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
                    return jsonify({
                        'success': True,
                        'image_base64': f"data:image/jpeg;base64,{img_base64}"
                    })
                else:
                    # Retornar como arquivo
                    return send_file(img_io, mimetype='image/jpeg')
            
            except Exception as e:
                return jsonify({'error': f'Erro ao processar imagem: {str(e)}'}), 500
        
        return jsonify({'error': 'Formato de arquivo não permitido'}), 400
    
    # Processar imagem de base64
    elif 'image' in request.form:
        try:
            # Decodificar base64
            image_data = request.form['image']
            
            # Remover prefixo de data URL se presente
            if 'data:image' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decodificar base64 para bytes
            image_bytes = base64.b64decode(image_data)
            
            # Criar objeto de imagem
            img = Image.open(BytesIO(image_bytes))
            
            # Processar imagem
            result_img, error = process_image(img, template_index)
            
            if error:
                return jsonify({'error': error}), 500
            
            # Preparar resposta
            img_io = BytesIO()
            result_img.save(img_io, 'JPEG', quality=85)
            img_io.seek(0)
            
            # Verificar formato de resposta solicitado
            response_format = request.form.get('response_format', 'file')
            
            if response_format == 'base64':
                # Retornar como base64
                img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
                return jsonify({
                    'success': True,
                    'image_base64': f"data:image/jpeg;base64,{img_base64}"
                })
            else:
                # Retornar como arquivo
                return send_file(img_io, mimetype='image/jpeg')
        
        except Exception as e:
            return jsonify({'error': f'Erro ao processar imagem base64: {str(e)}'}), 500
    
    # Processar imagem de URL
    elif 'image_url' in request.form:
        try:
            # Baixar imagem da URL
            image_url = request.form['image_url']
            response = requests.get(image_url)
            
            if response.status_code != 200:
                return jsonify({'error': f'Erro ao baixar imagem da URL: {response.status_code}'}), 400
            
            # Criar objeto de imagem
            img = Image.open(BytesIO(response.content))
            
            # Processar imagem
            result_img, error = process_image(img, template_index)
            
            if error:
                return jsonify({'error': error}), 500
            
            # Preparar resposta
            img_io = BytesIO()
            result_img.save(img_io, 'JPEG', quality=85)
            img_io.seek(0)
            
            # Verificar formato de resposta solicitado
            response_format = request.form.get('response_format', 'file')
            
            if response_format == 'base64':
                # Retornar como base64
                img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
                return jsonify({
                    'success': True,
                    'image_base64': f"data:image/jpeg;base64,{img_base64}"
                })
            else:
                # Retornar como arquivo
                return send_file(img_io, mimetype='image/jpeg')
        
        except Exception as e:
            return jsonify({'error': f'Erro ao processar imagem da URL: {str(e)}'}), 500
    
    return jsonify({'error': 'Método de envio de imagem não suportado'}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
