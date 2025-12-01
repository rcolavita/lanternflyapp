import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient, ContentSettings
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 1. SETUP AZURE CONNECTION
# We get the connection string from the Environment Variables (for security)
# If running locally, you might need to hardcode it or use a .env file, 
# but for deployment, we will set this in the Azure Portal later.
CONNECT_STR = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = "lanternfly-images"

# Initialize the Blob Service Client
try:
    blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
    
    # Try to create the container if it doesn't exist (and set public access)
    # Note: In production, you often do this manually, but this is a fail-safe.
    if not container_client.exists():
        container_client.create_container(public_access="container")
except Exception as e:
    print(f"Warning: Could not connect to Azure Storage. Check Connection String. {e}")

# 2. THE HOMEPAGE
@app.route("/")
def index():
    # This looks inside the 'templates' folder for index.html
    return render_template("index.html")

# 3. API: UPLOAD IMAGE
@app.route("/api/v1/upload", methods=["POST"])
def upload():
    try:
        # Check if file part is in request
        if 'file' not in request.files:
            return jsonify({"ok": False, "error": "No file part"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"ok": False, "error": "No selected file"}), 400

        # Sanitize filename and add timestamp (Requirements: YYYYMMDDThhmmss-original.ext)
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        safe_name = secure_filename(file.filename)
        new_filename = f"{timestamp}-{safe_name}"

        # Get the blob client for this specific new file
        blob_client = container_client.get_blob_client(new_filename)

        # Upload the file data
        # We must set content_type so the browser knows it's an image, not a downloaded file
        blob_client.upload_blob(
            file, 
            overwrite=True, 
            content_settings=ContentSettings(content_type=file.content_type)
        )

        return jsonify({"ok": True, "url": blob_client.url})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# 4. API: VIEW GALLERY
@app.route("/api/v1/gallery", methods=["GET"])
def gallery():
    try:
        image_urls = []
        # List all blobs in the container
        blob_list = container_client.list_blobs()
        
        for blob in blob_list:
            # Reconstruct the full URL
            # The URL format is usually: https://<account>.blob.core.windows.net/<container>/<blob_name>
            blob_url = f"{container_client.url}/{blob.name}"
            image_urls.append(blob_url)
            
        return jsonify({"ok": True, "gallery": image_urls})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# 5. HEALTH CHECK (Optional but good practice)
@app.route("/api/v1/health")
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(debug=True)



