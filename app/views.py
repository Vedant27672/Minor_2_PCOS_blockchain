import os
import json
import base64
import tempfile
import traceback
import urllib.parse
import re
import requests
from timeit import default_timer as timer
from bson.objectid import ObjectId
from flask import (
    render_template, redirect, request, send_file, flash, url_for, jsonify,
    send_from_directory, abort
)
from flask_login import (
    login_user, logout_user, current_user, login_required
)
from werkzeug.utils import secure_filename, safe_join

from app import app, public_files, file_encryptor, bcrypt, login_manager, users

# Constants
UPLOAD_FOLDER = os.path.abspath("app/static/Uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ADDR = "http://127.0.0.1:8800"

# Globals
request_tx = []
files = {}

# ------------------ User Model & Auth ------------------

class User:
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.password = user_data['password']
        self.is_master = user_data.get('is_master', False)

    @staticmethod
    def get(user_id):
        user_data = users.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None

    @staticmethod
    def get_by_username(username):
        user_data = users.find_one({'username': username})
        return User(user_data) if user_data else None

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# ------------------ Utility Functions ------------------

def insert_public_file(synthetic_file_path, model_name, uploader_username):
    """Insert a document into the public_files collection."""
    doc = {
        "synthetic_file_path": synthetic_file_path,
        "model_name": model_name,
        "uploader_username": uploader_username
    }
    app.logger.debug(f"Inserting document into public_files: {doc}")
    result = public_files.insert_one(doc)
    app.logger.debug(f"Document inserted with id: {result.inserted_id}")
    return result.inserted_id

def get_tx_req():
    """Fetch and sort transaction requests from the blockchain."""
    global request_tx
    chain_addr = f"{ADDR}/chain"
    resp = requests.get(chain_addr)
    if resp.status_code == 200:
        content = []
        chain = json.loads(resp.content.decode())
        for block in chain["chain"]:
            for trans in block["transactions"]:
                trans["index"] = block["index"]
                trans["hash"] = block["prev_hash"]
                content.append(trans)
        request_tx = sorted(content, key=lambda k: k["hash"], reverse=True)

def delete_temp_file(filepath):
    """Force delete file with multiple strategies."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            app.logger.debug(f"Deleted temp file: {filepath}")
            return
        app.logger.warning(f"Temp file not found: {filepath}")
    except Exception as e:
        app.logger.warning(f"First delete attempt failed: {str(e)}")
        import time
        time.sleep(1)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                app.logger.debug(f"Force deleted after delay: {filepath}")
                return
        except Exception as e:
            app.logger.warning(f"Force delete failed: {str(e)}")
            try:
                if os.path.exists(filepath):
                    temp_name = f"{filepath}.deleteme"
                    os.rename(filepath, temp_name)
                    os.remove(temp_name)
                    app.logger.debug(f"Used rename-and-delete for: {filepath}")
            except Exception as e:
                app.logger.error(f"All deletion attempts failed for {filepath}: {str(e)}")

# ------------------ Routes ------------------

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = users.find_one({'username': username})
        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login failed. Check username and password', 'danger')
    return render_template('new_login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        if users.find_one({'username': username}):
            flash('Username already exists', 'danger')
        else:
            users.insert_one({
                'username': username,
                'email': email,
                'password': hashed_password,
                'is_master': username == 'admin'
            })
            flash('Account created successfully! Please login', 'success')
            return redirect(url_for('login'))
    return render_template('new_signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/master/login', methods=['POST'])
def master_login():
    """Special master login endpoint."""
    from config import Config
    data = request.json
    if (data.get('username') == Config.MASTER_USERNAME and
        data.get('password') == Config.MASTER_PASSWORD and
        data.get('secret') == Config.MASTER_SECRET):
        user_data = users.find_one({'username': Config.MASTER_USERNAME})
        if user_data:
            user = User(user_data)
            login_user(user)
            return jsonify({'status': 'success'})
    return jsonify({'status': 'unauthorized'}), 401

@app.route('/upload')
@login_required
def upload():
    """Show upload page with filtered transactions."""
    get_tx_req()
    filtered_tx = [
        tx for tx in request_tx
        if 'v_file' in tx and (
            tx.get('owner') == 'anonymous' or
            (current_user.is_authenticated and (
                current_user.username == tx.get('owner') or current_user.is_master
            ))
        )
    ]
    return render_template(
        "new_index.html",
        title="FileStorage",
        subtitle="A Decentralized Network for File Storage/Sharing",
        node_address=ADDR,
        request_tx=filtered_tx
    )

@app.route('/view_public_datasets')
def view_public_datasets():
    try:
        public_datasets = list(public_files.find({}))
        for dataset in public_datasets:
            synthetic_path = dataset.get('synthetic_file_path', '')
            dataset['synthetic_filename'] = os.path.basename(synthetic_path)
            if synthetic_path:
                if os.path.isabs(synthetic_path):
                    try:
                        synthetic_path = os.path.relpath(synthetic_path, app.config['UPLOAD_FOLDER'])
                    except ValueError:
                        pass
                synthetic_path = synthetic_path.replace("\\", "/")
            dataset['synthetic_file_relpath'] = synthetic_path
            dataset['uploader_username'] = dataset.get('uploader_username', 'Unknown')
            dataset['model_filename'] = os.path.basename(dataset.get('model_name', ''))
    except Exception as e:
        app.logger.error(f"Failed to fetch public datasets: {e}")
        public_datasets = []
    return render_template('view_public_datasets_with_analyze.html', public_datasets=public_datasets)

@app.route('/analyze_dataset/<path:filename>')
def analyze_dataset(filename):
    """Display analysis results for a synthetic dataset file."""
    try:
        filename = urllib.parse.unquote(filename)
        escaped_filename = re.escape(filename)
        doc = public_files.find_one({"synthetic_file_path": {"$regex": escaped_filename}})
        if not doc or "analysis_results" not in doc:
            flash('Analysis results not found for the specified dataset.', 'danger')
            return redirect(url_for('view_public_datasets'))
        analysis_results = doc["analysis_results"]
        synthetic_csv_path = doc.get("synthetic_file_path", filename)
        synthetic_data_html = analysis_results.get("synthetic_data_html")
        if not synthetic_data_html:
            import pandas as pd
            synthetic_file_path = synthetic_csv_path
            if not synthetic_file_path.startswith("/"):
                synthetic_file_path = os.path.join(app.config['UPLOAD_FOLDER'], synthetic_csv_path)
            synthetic_data = pd.read_csv(synthetic_file_path)
            synthetic_data_html = synthetic_data.to_html(classes="table table-striped", index=False)
        return render_template(
            "analysis_results.html",
            analysis=analysis_results,
            filename=filename,
            synthetic_data_html=synthetic_data_html
        )
    except Exception as e:
        app.logger.error(f"Error displaying analysis results: {str(e)}")
        app.logger.error(traceback.format_exc())
        flash('An error occurred while displaying the analysis results.', 'danger')
        return redirect(url_for('view_public_datasets'))

@app.route("/generate_dataset/<filename>", methods=["POST"])
@login_required
def generate_dataset(filename):
    """Generate a synthetic dataset from the uploaded file."""
    try:
        enc_file_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            f"{os.path.splitext(filename)[0]}.enc"
        )
        password = current_user.password if current_user.is_authenticated else "anonymous"
        fd, decrypted_file_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            file_encryptor.decrypt_file(enc_file_path, decrypted_file_path, password)
            from app import gan
            synthetic_data, analysis_results = gan.generate_synthetic_data(
                decrypted_file_path, current_user.username, filename, output_dir=app.config['UPLOAD_FOLDER']
            )
            synthetic_data_html = synthetic_data.to_html(classes="table table-striped", index=False)
            synthetic_csv_path = analysis_results.get('synthetic_csv_path')
            if synthetic_csv_path and not os.path.isabs(synthetic_csv_path):
                synthetic_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], synthetic_csv_path)
            app.logger.debug(f"synthetic_csv_path (full): {synthetic_csv_path}")
            flash('Synthetic dataset generated successfully!', 'success')
            try:
                from app import model_mappings
                app.logger.debug(f"Upserting document with path {synthetic_csv_path} into public_files")
                if synthetic_csv_path:
                    mapping = model_mappings.find_one({
                        "username": current_user.username,
                        "filename": filename
                    })
                    model_path = mapping["model_path"] if mapping and "model_path" in mapping else "CTGAN"
                    update_doc = {
                        "model_name": model_path,
                        "uploader_username": current_user.username,
                        "analysis_results": analysis_results
                    }
                    result = public_files.update_one(
                        {"synthetic_file_path": synthetic_csv_path},
                        {"$set": update_doc},
                        upsert=True
                    )
                    if result.upserted_id:
                        app.logger.info(f"Inserted new public file document with id: {result.upserted_id}")
                    else:
                        app.logger.info(f"Updated existing public file document with path: {synthetic_csv_path}")
                else:
                    app.logger.warning("Synthetic CSV path is None or empty, skipping upsert into public_files.")
            except Exception as e:
                app.logger.error(f"Failed to upsert public file document: {e}")
            return render_template(
                "analysis_results.html",
                analysis=analysis_results,
                filename=filename,
                synthetic_data_html=synthetic_data_html,
                synthetic_csv_path=synthetic_csv_path
            )
        finally:
            if os.path.exists(decrypted_file_path):
                os.remove(decrypted_file_path)
    except Exception as e:
        app.logger.error(f"Error generating synthetic dataset: {str(e)}")
        app.logger.error(traceback.format_exc())
        flash('An error occurred while generating the synthetic dataset. Please try again.', 'danger')
        return redirect(url_for('upload'))

@app.route("/download_synthetic/<path:filepath>")
@login_required
def download_synthetic(filepath):
    """Serve the synthetic dataset CSV file for download, including subdirectories."""
    directory = app.config['UPLOAD_FOLDER']
    try:
        filepath = urllib.parse.unquote(filepath).replace("\\", "/")
        safe_path = safe_join(directory, filepath)
        app.logger.debug(f"Requested filepath (decoded): {filepath}")
        app.logger.debug(f"Safe joined path: {safe_path}")
        app.logger.debug(f"File exists: {os.path.isfile(safe_path) if safe_path else 'safe_path is None'}")
        if not safe_path or not os.path.isfile(safe_path):
            app.logger.error(f"File not found for download: {filepath} in {directory}")
            app.logger.error(f"Directory contents: {os.listdir(directory)}")
            for root, dirs, files in os.walk(directory):
                app.logger.error(f"Root: {root}")
                app.logger.error(f"Dirs: {dirs}")
                app.logger.error(f"Files: {files}")
            abort(404)
        return send_from_directory(directory, filepath, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Error serving file {filepath}: {str(e)}")
        abort(500)

@app.route("/submit", methods=["POST"])
def submit():
    """Handle file upload and transaction submission."""
    try:
        start = timer()
        user = current_user.username if current_user.is_authenticated else "anonymous"
        up_file = request.files.get("v_file")
        if not up_file or up_file.filename == '':
            flash('No file selected for uploading', 'danger')
            return redirect("/upload")
        allowed_extensions = {'.csv'}
        filename = secure_filename(up_file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            flash('Invalid file type. Only .csv files are allowed.', 'danger')
            return redirect("/upload")
        base_filename = os.path.splitext(filename)[0]
        enc_dir = os.path.join("app/static/Uploads/")
        if not os.path.exists(enc_dir):
            os.makedirs(enc_dir, exist_ok=True)
        enc_file_path = os.path.join(enc_dir, f"{base_filename}.enc")
        up_file.save(enc_file_path)
        file_states = os.stat(enc_file_path).st_size
        password = current_user.password if current_user.is_authenticated else "anonymous"
        file_encryptor.encrypt_file(enc_file_path, enc_file_path, password)
        files[up_file.filename] = enc_file_path
        with open(files[up_file.filename], 'rb') as f:
            file_data = base64.b64encode(f.read()).decode('utf-8')
        post_object = {
            "user": user,
            "v_file": up_file.filename,
            "file_data": file_data,
            "file_size": file_states,
            "owner": current_user.username if current_user.is_authenticated else "anonymous"
        }
        address = f"{ADDR}/new_transaction"
        requests.post(address, json=post_object)
        mine_address = f"{ADDR}/mine"
        try:
            mine_response = requests.get(mine_address)
            app.logger.info(f"Mining response: {mine_response.text}")
        except Exception as e:
            app.logger.error(f"Error requesting mining: {str(e)}")
        end = timer()
        print(end - start)
        return redirect("/upload")
    except Exception as e:
        app.logger.error(f"Error in submit: {str(e)}")
        app.logger.error(traceback.format_exc())
        flash('An error occurred during file upload. Please try again.', 'danger')
        return redirect("/upload")

@app.route("/submit/<string:variable>", methods=["GET"])
@login_required
def download_file(variable):
    """Download and decrypt a file from the blockchain."""
    chain_addr = f"{ADDR}/chain"
    resp = requests.get(chain_addr)
    if resp.status_code == 200:
        chain = json.loads(resp.content.decode())
        for block in chain["chain"]:
            for trans in block["transactions"]:
                if trans.get("v_file") == variable:
                    if (
                        (current_user.is_authenticated and (
                            current_user.username == trans.get("owner") or current_user.is_master
                        )) or trans.get("owner") == "anonymous"
                    ):
                        base_filename = os.path.splitext(variable)[0]
                        temp_path = os.path.join(
                            app.root_path, "static", "Uploads", f"temp_{base_filename}.csv"
                        )
                        password = current_user.password if current_user.is_authenticated else "anonymous"
                        file_encryptor.decrypt_file(files[variable], temp_path, password)
                        try:
                            response = send_file(temp_path, as_attachment=True)
                            response.call_on_close(lambda: delete_temp_file(temp_path))
                            return response
                        except Exception:
                            delete_temp_file(temp_path)
                            raise
                    else:
                        flash('You do not have permission to access this file', 'danger')
                        return redirect(url_for('index'))
    flash('File not found', 'danger')
    return redirect(url_for('index'))

@app.route('/view_block/<int:block_index>/<filename>')
@login_required
def view_block(block_index, filename):
    """Display block contents for authenticated user."""
    chain_addr = f"{ADDR}/chain"
    resp = requests.get(chain_addr)
    if resp.status_code == 200:
        chain = json.loads(resp.content.decode())
        for block in chain["chain"]:
            if block["index"] == block_index:
                for trans in block["transactions"]:
                    if (
                        trans.get("v_file") == filename and (
                            current_user.username == trans.get("owner") or current_user.is_master
                        )
                    ):
                        return render_template(
                            "new_view_block.html",
                            block=block,
                            transaction=trans,
                            filename=filename
                        )
        flash('Block or file not found', 'danger')
    return redirect(url_for('index'))
