from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
from PIL import Image
import io
import base64
import os
import time

app = Flask(__name__)
Swagger(app)

# Function to get image data and size
def get_image_data_size(image_path):
  # Read the image data from the file in binary mode
  with open(image_path, 'rb') as file:
    image_data = file.read()
  
  image_size_kb = len(image_data) / 1024

  return image_data, image_size_kb

# Function to compress an image and return it as base64-encoded string
def compress_image(image_path, max_size_kb, target_dimension, quality):
  
  # Get image data and image size 
  image_data, current_size_kb = get_image_data_size(image_path)

  # Resize the image
  original_image = Image.open(io.BytesIO(image_data))
  resized_image = original_image.resize(target_dimension, Image.Resampling.LANCZOS)

  # Calculate the compression factor based on the target size
  compression_factor = (max_size_kb / current_size_kb) * 100

  # Adjust the quality parameter based on the compression factor
  quality = int(quality * compression_factor / 100)

  # Ensure the quality parameter is within a valid range
  quality = max(1, min(quality, 95))

    # Compress the image
  compressed_image = io.BytesIO()
  resized_image.save(compressed_image, format='JPEG', quality=quality)

  # Get the size of the compressed image in KB
  compressed_image_size = compressed_image.getbuffer().nbytes / 1024 

  compressed_image_base64 = base64.b64encode(compressed_image.getvalue()).decode('utf-8')

  return compressed_image_size, compressed_image_base64


@app.route('/get_compressed_image', methods=['GET'])
def get_compressed_image():
  """
  Endpoint to get a compressed image.
  ---
  parameters:
    - name: image_name
      in: query
      type: string
      description: Image name.
      required: true
    - name: max_size_kb
      in: query
      type: number
      description: Target size for the compressed image in kilobytes.
      required: true
    - name: quality
      in: query
      type: number
      description: Quality of the compressed image.
      required: true
    - name: target_width
      in: query
      type: number
      description: Target width for the compressed image.
      required: true
    - name: target_height
      in: query
      type: number
      description: Target height for the compressed image.
      required: true
  responses:
    200:
      description: Compressed image successfully retrieved.
      content:
        application/json:
          schema:
            type: object
            properties:
              compressed_image:
                type: string
                description: Base64-encoded compressed image.
    404:
      description: Image not found.
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
                description: Error message.
  """
  try:
    start_time = time.time()
    
    # Get the image name as a parameter
    image_name = request.args.get('image_name')

    # Get the target dimension as a parameter
    target_width = int(request.args.get('target_width'))
    target_height = int(request.args.get('target_height'))
    target_dimension = (target_width, target_height)

    # Construct the path to the image in the 'images' folder
    image_path = os.path.join('images', image_name)

    # Check if the image file exists
    if not os.path.exists(image_path):
        result = {'error': f'Image {image_name} not found'}, 404


    # Get the target size as a parameter (defaulting to 1024 KB if not provided)
    max_size_kb = int(request.args.get('max_size_kb', 1024))

    # Get image data and size
    image_data, image_size_kb = get_image_data_size(image_path)

    # Check if image size is less than max size
    if (image_size_kb <= max_size_kb):
        # Encode the binary data of the image
        encoded_image = base64.b64encode(image_data)
        
        # Convert the bytes to a UTF-8 string
        image_base64 = encoded_image.decode('utf-8')
        result = {"message":f"Image size is already less than {max_size_kb} KB", "image_base64": image_base64 }

    # Get the quality as a parameter (defaulting to 85 if not provided)
    quality = int(request.args.get('quality', 85))

    # Get the compressed image size, time taken and compressed image base64
    compressed_image_size, compressed_image_base64 = compress_image(image_path, max_size_kb, target_dimension, quality) 

    end_time = time.time()

    time_taken= (end_time - start_time) * 1000

    # Return the JSON response
    result = {'time_elapsed': f'{int(time_taken)} ms', 'compressed_image_size': f'{compressed_image_size:.2f} KB', 'compressed_image_base64': compressed_image_base64}, 200
    return jsonify(result)
  except Exception as e:
    result = {'error': f'An error occured: {str(e)}'}, 500
    return jsonify(result)


@app.route('/get_images', methods=['GET'])
@swag_from({
    'responses': {
        200: {
            'description': 'A successful response',
            'schema': {
                'type': 'object',
                'properties':
                  {
                    'image_name': {
                      'type': 'string',
                      'description': 'Image name'
                    },
                    'image_size': {
                      'type': 'string',
                      'description': 'Image size in KB'
                    }
                  }
              }
        }
    }
})
def get_images():
  """
  Get all the images name and size in images directory.
  """
  images = []

  try:
    # Iterate over all files in the images directory
    for filename in os.listdir("images"):
      if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        # Construct the path to the image in the 'images' folder
        image_path = os.path.join('images', filename)
        image_size_kb = int(os.path.getsize(image_path) / 1024)
        image_detail = {'image_name': filename, 'image_size': f'{image_size_kb} KB'}
        images.append(image_detail)

    return images    
  except Exception as e:
    return {'error': f'An error occured: {str(e)}'}, 500


if __name__ == '__main__':
  app.run(debug=True)
