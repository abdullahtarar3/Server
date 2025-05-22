from flask import Flask, request, render_template_string, redirect, url_for, send_from_directory, session, jsonify, flash
import os
import datetime
import threading
import mimetypes
import json
import logging
import hashlib
import uuid
from functools import wraps
from logging.handlers import RotatingFileHandler
import secrets

# Configure structured logging
def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler('logs/file_server.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
    
    return logging.getLogger(__name__)

logger = setup_logging()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Generate secure secret key

# Configuration
UPLOAD_FOLDER = os.path.abspath('.')
CONFIG_FILE = os.path.join(UPLOAD_FOLDER, 'server_config.json')
USERS_FILE = os.path.join(UPLOAD_FOLDER, 'users.json')
STATS_FILE = os.path.join(UPLOAD_FOLDER, 'file_stats.json')

# Default configuration
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 50588,
    "max_file_size": 5 * 1024 * 1024 * 1024,  # 5GB
    "allowed_extensions": ["txt", "pdf", "png", "jpg", "jpeg", "gif", "mp4", "mp3", "doc", "docx", "xlsx"],
    "enable_public_sharing": True,
    "theme": "light"
}

# Default users
DEFAULT_USERS = {
    "admin": {
        "password_hash": hashlib.pbkdf2_hmac('sha256', '1234'.encode('utf-8'), b'salt', 100000).hex(),
        "role": "admin",
        "created": datetime.datetime.now().isoformat()
    }
}

# Load/Save functions
def load_json_file(filepath, default_data):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
    return default_data

def save_json_file(filepath, data):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        return False

# Load configuration and users
config = load_json_file(CONFIG_FILE, DEFAULT_CONFIG)
users = load_json_file(USERS_FILE, DEFAULT_USERS)
file_stats = load_json_file(STATS_FILE, {})

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('files'))
        return f(*args, **kwargs)
    return decorated_function

# Password hashing
def hash_password(password):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'salt', 100000).hex()

def verify_password(password, password_hash):
    return hash_password(password) == password_hash

# File statistics
def update_file_stats(filename, action):
    if filename not in file_stats:
        file_stats[filename] = {
            'downloads': 0,
            'views': 0,
            'uploaded': datetime.datetime.now().isoformat(),
            'last_accessed': None
        }
    
    if action == 'download':
        file_stats[filename]['downloads'] += 1
    elif action == 'view':
        file_stats[filename]['views'] += 1
    
    file_stats[filename]['last_accessed'] = datetime.datetime.now().isoformat()
    save_json_file(STATS_FILE, file_stats)

# Enhanced HTML Template
TEMPLATE = '''
<!doctype html>
<html lang="en" data-bs-theme="{{ theme }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Enhanced File Server</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
  <style>
    :root {
      --bs-primary: #007bff;
      --bs-secondary: #6c757d;
    }
    
    [data-bs-theme="dark"] {
      --bs-body-bg: #212529;
      --bs-body-color: #fff;
    }
    
    .drop-zone {
      border: 2px dashed #ccc;
      border-radius: 10px;
      padding: 20px;
      text-align: center;
      cursor: pointer;
      transition: all 0.3s ease;
      min-height: 120px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
    }
    
    .drop-zone:hover, .drop-zone.dragover {
      border-color: var(--bs-primary);
      background-color: rgba(0, 123, 255, 0.1);
    }
    
    .drop-zone.dragover {
      transform: scale(1.02);
    }
    
    .preview-modal {
      display: none;
      position: fixed;
      z-index: 1000;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.9);
    }
    
    .preview-content {
      margin: auto;
      display: block;
      max-width: 90%;
      max-height: 90%;
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
    }
    
    .close-preview {
      position: absolute;
      top: 15px;
      right: 35px;
      color: #f1f1f1;
      font-size: 40px;
      font-weight: bold;
      transition: 0.3s;
      cursor: pointer;
    }
    
    .file-icon {
      font-size: 1.5rem;
      margin-right: 10px;
    }
    
    .stats-card {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }
    
    .file-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 1rem;
    }
    
    .file-card {
      border: 1px solid #dee2e6;
      border-radius: 0.5rem;
      padding: 1rem;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .file-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .search-container {
      position: relative;
    }
    
    .search-container .bi-search {
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: #6c757d;
    }
    
    .search-input {
      padding-left: 40px !important;
    }
    
    .badge-file-type {
      font-size: 0.7rem;
      padding: 0.3rem 0.5rem;
    }
    
    .theme-toggle {
      cursor: pointer;
      transition: transform 0.2s;
    }
    
    .theme-toggle:hover {
      transform: scale(1.1);
    }
  </style>
</head>
<body>
<div id="previewModal" class="preview-modal">
  <span class="close-preview" onclick="closePreview()">&times;</span>
  <div id="previewContent" class="preview-content"></div>
</div>

<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
  <div class="container">
    <a class="navbar-brand" href="#">
      <i class="bi bi-hdd-network me-2"></i>Enhanced File Server
    </a>
    {% if session.logged_in %}
    <div class="navbar-nav ms-auto d-flex flex-row gap-3">
      <span class="navbar-text">Welcome, {{ session.username }}</span>
      <i class="bi bi-moon-fill theme-toggle" id="themeToggle" title="Toggle Theme"></i>
      {% if session.role == 'admin' %}
      <a class="nav-link" href="{{ url_for('admin') }}"><i class="bi bi-gear"></i> Admin</a>
      {% endif %}
      <a class="nav-link" href="{{ url_for('logout') }}"><i class="bi bi-box-arrow-right"></i> Logout</a>
    </div>
    {% endif %}
  </div>
</nav>

<div class="container py-4">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class="alert alert-{{ 'danger' if category == 'error' else 'success' if category == 'success' else 'info' }} alert-dismissible fade show">
          {{ message }}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  {% if not session.logged_in %}
    <div class="row justify-content-center">
      <div class="col-md-4">
        <div class="card shadow">
          <div class="card-body">
            <h4 class="card-title text-center mb-4">
              <i class="bi bi-shield-lock text-primary"></i> Login
            </h4>
            <form method="POST">
              <div class="mb-3">
                <label class="form-label">Username</label>
                <input name="username" class="form-control" required>
              </div>
              <div class="mb-3">
                <label class="form-label">Password</label>
                <input type="password" name="password" class="form-control" required>
              </div>
              <button type="submit" class="btn btn-primary w-100">
                <i class="bi bi-box-arrow-in-right me-2"></i>Login
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
    
  {% elif page == 'admin' %}
    <div class="row">
      <div class="col-12">
        <h2><i class="bi bi-gear me-2"></i>Admin Panel</h2>
        
        <!-- Statistics Cards -->
        <div class="row mb-4">
          <div class="col-md-3">
            <div class="card stats-card">
              <div class="card-body text-center">
                <i class="bi bi-files display-4 mb-2"></i>
                <h3>{{ total_files }}</h3>
                <p class="mb-0">Total Files</p>
              </div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="card stats-card">
              <div class="card-body text-center">
                <i class="bi bi-download display-4 mb-2"></i>
                <h3>{{ total_downloads }}</h3>
                <p class="mb-0">Downloads</p>
              </div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="card stats-card">
              <div class="card-body text-center">
                <i class="bi bi-people display-4 mb-2"></i>
                <h3>{{ total_users }}</h3>
                <p class="mb-0">Users</p>
              </div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="card stats-card">
              <div class="card-body text-center">
                <i class="bi bi-hdd display-4 mb-2"></i>
                <h3>{{ disk_usage }}</h3>
                <p class="mb-0">Disk Usage</p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- User Management -->
        <div class="card mb-4">
          <div class="card-header">
            <h5><i class="bi bi-people me-2"></i>User Management</h5>
          </div>
          <div class="card-body">
            <form method="POST" action="{{ url_for('admin') }}" class="row g-3 mb-3">
              <div class="col-md-4">
                <label class="form-label">Username</label>
                <input type="text" name="new_username" class="form-control" required>
              </div>
              <div class="col-md-4">
                <label class="form-label">Password</label>
                <input type="password" name="new_password" class="form-control" required>
              </div>
              <div class="col-md-2">
                <label class="form-label">Role</label>
                <select name="new_role" class="form-select">
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div class="col-md-2 d-flex align-items-end">
                <button type="submit" name="action" value="add_user" class="btn btn-success">
                  <i class="bi bi-person-plus"></i> Add User
                </button>
              </div>
            </form>
            
            <div class="table-responsive">
              <table class="table table-hover">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {% for username, user_data in users.items() %}
                  <tr>
                    <td>{{ username }}</td>
                    <td><span class="badge bg-{{ 'danger' if user_data.role == 'admin' else 'primary' }}">{{ user_data.role }}</span></td>
                    <td>{{ user_data.created.split('T')[0] }}</td>
                    <td>
                      {% if username != 'admin' %}
                      <form method="POST" action="{{ url_for('admin') }}" class="d-inline">
                        <input type="hidden" name="username" value="{{ username }}">
                        <button type="submit" name="action" value="delete_user" class="btn btn-sm btn-danger" 
                                onclick="return confirm('Delete user {{ username }}?')">
                          <i class="bi bi-trash"></i>
                        </button>
                      </form>
                      {% endif %}
                    </td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        
        <!-- File Statistics -->
        <div class="card">
          <div class="card-header">
            <h5><i class="bi bi-bar-chart me-2"></i>File Statistics</h5>
          </div>
          <div class="card-body">
            <div class="table-responsive">
              <table class="table table-hover">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Downloads</th>
                    <th>Views</th>
                    <th>Uploaded</th>
                    <th>Last Accessed</th>
                  </tr>
                </thead>
                <tbody>
                  {% for filename, stats in file_stats.items() %}
                  <tr>
                    <td>{{ filename }}</td>
                    <td><span class="badge bg-primary">{{ stats.downloads }}</span></td>
                    <td><span class="badge bg-info">{{ stats.views }}</span></td>
                    <td>{{ stats.uploaded.split('T')[0] if stats.uploaded else 'Unknown' }}</td>
                    <td>{{ stats.last_accessed.split('T')[0] if stats.last_accessed else 'Never' }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
    
  {% else %}
    <!-- File Management Interface -->
    <div class="row">
      <div class="col-12">
        <!-- Upload Section -->
        <div class="card mb-4">
          <div class="card-body">
            <h5 class="card-title"><i class="bi bi-cloud-upload me-2"></i>Upload Files</h5>
            <form id="uploadForm" method="POST" enctype="multipart/form-data" action="/upload">
              <div class="drop-zone mb-3" id="dropZone">
                <i class="bi bi-cloud-upload display-4 text-muted mb-2"></i>
                <p class="mb-2">Drag & drop files here or click to browse</p>
                <p class="text-muted small">Maximum file size: {{ max_file_size }}</p>
                <input type="file" id="fileInput" name="files" class="d-none" multiple>
              </div>
              
              <div id="fileList" class="mb-3"></div>
              
              <div class="progress mb-3 d-none" id="uploadProgress">
                <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
              </div>
              
              <div id="uploadStatus" class="mb-3"></div>
              
              <div class="d-flex gap-2">
                <button class="btn btn-success" type="submit" id="uploadBtn" disabled>
                  <i class="bi bi-cloud-upload me-2"></i>Upload Files
                </button>
                <button class="btn btn-outline-secondary" type="button" id="clearBtn" onclick="clearFiles()">
                  <i class="bi bi-x-circle me-2"></i>Clear
                </button>
              </div>
            </form>
          </div>
        </div>
        
        <!-- Search and Filter -->
        <div class="card mb-4">
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-6">
                <div class="search-container">
                  <i class="bi bi-search"></i>
                  <input type="text" id="searchInput" class="form-control search-input" placeholder="Search files...">
                </div>
              </div>
              <div class="col-md-3">
                <select id="typeFilter" class="form-select">
                  <option value="">All Types</option>
                  <option value="image">Images</option>
                  <option value="video">Videos</option>
                  <option value="audio">Audio</option>
                  <option value="pdf">PDFs</option>
                  <option value="text">Text</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div class="col-md-3">
                <div class="btn-group w-100" role="group">
                  <button type="button" class="btn btn-outline-primary active" id="gridView">
                    <i class="bi bi-grid"></i>
                  </button>
                  <button type="button" class="btn btn-outline-primary" id="listView">
                    <i class="bi bi-list"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Bulk Actions -->
        <div class="card mb-4 d-none" id="bulkActions">
          <div class="card-body">
            <div class="d-flex align-items-center gap-3">
              <span><span id="selectedCount">0</span> files selected</span>
              <button class="btn btn-danger btn-sm" onclick="bulkDelete()">
                <i class="bi bi-trash me-2"></i>Delete Selected
              </button>
              <button class="btn btn-primary btn-sm" onclick="bulkDownload()">
                <i class="bi bi-download me-2"></i>Download Selected
              </button>
              <button class="btn btn-outline-secondary btn-sm" onclick="clearSelection()">
                <i class="bi bi-x me-2"></i>Clear Selection
              </button>
            </div>
          </div>
        </div>
        
        <!-- Files Display -->
        <div class="card">
          <div class="card-body">
            <div id="filesGridView" class="file-grid">
              {% for file in files %}
                <div class="file-card" data-filename="{{ file.name }}" data-type="{{ file.type }}">
                  <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="form-check">
                      <input class="form-check-input file-checkbox" type="checkbox" value="{{ file.name }}">
                    </div>
                    <span class="badge badge-file-type bg-{{ 'primary' if file.type == 'image' else 'danger' if file.type == 'video' else 'success' if file.type == 'audio' else 'warning' if file.type == 'pdf' else 'secondary' }}">
                      {{ file.type }}
                    </span>
                  </div>
                  
                  <div class="text-center mb-3">
                    {% if file.type == 'image' %}
                      <i class="bi bi-file-image text-primary" style="font-size: 3rem;"></i>
                    {% elif file.type == 'video' %}
                      <i class="bi bi-file-play text-danger" style="font-size: 3rem;"></i>
                    {% elif file.type == 'audio' %}
                      <i class="bi bi-file-music text-success" style="font-size: 3rem;"></i>
                    {% elif file.type == 'pdf' %}
                      <i class="bi bi-file-pdf text-danger" style="font-size: 3rem;"></i>
                    {% elif file.type == 'text' %}
                      <i class="bi bi-file-text text-secondary" style="font-size: 3rem;"></i>
                    {% else %}
                      <i class="bi bi-file-earmark" style="font-size: 3rem;"></i>
                    {% endif %}
                  </div>
                  
                  <h6 class="card-title text-truncate" title="{{ file.name }}">{{ file.name }}</h6>
                  <p class="card-text small text-muted">
                    Size: {{ file.size }}<br>
                    Modified: {{ file.modified }}<br>
                    {% if file.name in file_stats %}
                    Downloads: {{ file_stats[file.name].downloads | default(0) }}
                    {% endif %}
                  </p>
                  
                  <div class="btn-group w-100" role="group">
                    {% if file.type in ['image', 'video', 'audio', 'pdf'] %}
                    <button class="btn btn-sm btn-info" onclick="previewFile('{{ file.type }}', '{{ url_for('files_raw', filename=file.name) }}', '{{ file.name }}')">
                      <i class="bi bi-eye"></i>
                    </button>
                    {% endif %}
                    <a href="{{ url_for('download', filename=file.name) }}" class="btn btn-sm btn-primary">
                      <i class="bi bi-download"></i>
                    </a>
                    <button class="btn btn-sm btn-danger" onclick="deleteFile('{{ file.name }}')">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </div>
              {% endfor %}
              {% if not files %}
                <div class="col-12 text-center py-5">
                  <i class="bi bi-inbox display-4 text-muted mb-3"></i>
                  <h5 class="text-muted">No files found</h5>
                  <p class="text-muted">Upload some files to get started</p>
                </div>
              {% endif %}
            </div>
            
            <!-- List View (Hidden by default) -->
            <div id="filesListView" class="d-none">
              <div class="table-responsive">
                <table class="table table-hover">
                  <thead>
                    <tr>
                      <th width="40">
                        <input type="checkbox" id="selectAll" class="form-check-input">
                      </th>
                      <th>Type</th>
                      <th>Filename</th>
                      <th>Size</th>
                      <th>Modified</th>
                      <th>Stats</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {% for file in files %}
                      <tr data-filename="{{ file.name }}" data-type="{{ file.type }}">
                        <td>
                          <input class="form-check-input file-checkbox" type="checkbox" value="{{ file.name }}">
                        </td>
                        <td>
                          {% if file.type == 'image' %}
                            <i class="bi bi-file-image text-primary file-icon"></i>
                          {% elif file.type == 'video' %}
                            <i class="bi bi-file-play text-danger file-icon"></i>
                          {% elif file.type == 'audio' %}
                            <i class="bi bi-file-music text-success file-icon"></i>
                          {% elif file.type == 'pdf' %}
                            <i class="bi bi-file-pdf text-danger file-icon"></i>
                          {% elif file.type == 'text' %}
                            <i class="bi bi-file-text text-secondary file-icon"></i>
                          {% else %}
                            <i class="bi bi-file-earmark file-icon"></i>
                          {% endif %}
                        </td>
                        <td>
                          {% if file.type in ['image', 'video', 'audio', 'pdf'] %}
                            <a href="#" onclick="previewFile('{{ file.type }}', '{{ url_for('files_raw', filename=file.name) }}', '{{ file.name }}'); return false;">{{ file.name }}</a>
                          {% else %}
                            {{ file.name }}
                          {% endif %}
                        </td>
                        <td>{{ file.size }}</td>
                        <td>{{ file.modified }}</td>
                        <td>
                          {% if file.name in file_stats %}
                          <small>
                            <i class="bi bi-download me-1"></i>{{ file_stats[file.name].downloads | default(0) }}
                            <i class="bi bi-eye ms-2 me-1"></i>{{ file_stats[file.name].views | default(0) }}
                          </small>
                          {% else %}
                          <small class="text-muted">No data</small>
                          {% endif %}
                        </td>
                        <td>
                          <div class="btn-group" role="group">
                            {% if file.type in ['image', 'video', 'audio', 'pdf'] %}
                            <button class="btn btn-sm btn-info" onclick="previewFile('{{ file.type }}', '{{ url_for('files_raw', filename=file.name) }}', '{{ file.name }}')">
                              <i class="bi bi-eye"></i>
                            </button>
                            {% endif %}
                            <a href="{{ url_for('download', filename=file.name) }}" class="btn btn-sm btn-primary">
                              <i class="bi bi-download"></i>
                            </a>
                            <button class="btn btn-sm btn-danger" onclick="deleteFile('{{ file.name }}')">
                              <i class="bi bi-trash"></i>
                            </button>
                          </div>
                        </td>
                      </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  {% endif %}
</div>

<!-- Hidden forms -->
<form id="deleteForm" method="POST" style="display:none;"></form>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
  // Theme toggle
  const themeToggle = document.getElementById('themeToggle');
  const html = document.documentElement;
  
  if (themeToggle) {
    themeToggle.addEventListener('click', function() {
      const currentTheme = html.getAttribute('data-bs-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-bs-theme', newTheme);
      themeToggle.className = newTheme === 'dark' ? 'bi bi-sun-fill theme-toggle' : 'bi bi-moon-fill theme-toggle';
      localStorage.setItem('theme', newTheme);
    });
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-bs-theme', savedTheme);
    themeToggle.className = savedTheme === 'dark' ? 'bi bi-sun-fill theme-toggle' : 'bi bi-moon-fill theme-toggle';
  }

  // Drag and drop functionality
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const fileList = document.getElementById('fileList');
  const uploadBtn = document.getElementById('uploadBtn');
  
  if (dropZone && fileInput) {
    // Click to select files
    dropZone.addEventListener('click', () => fileInput.click());
    
    // Drag and drop events
    dropZone.addEventListener('dragover', function(e) {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', function(e) {
      e.preventDefault();
      dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', function(e) {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      const files = e.dataTransfer.files;
      fileInput.files = files;
      displaySelectedFiles(files);
    });
    
    fileInput.addEventListener('change', function() {
      displaySelectedFiles(this.files);
    });
  }
  
  // Upload form handling
  const uploadForm = document.getElementById('uploadForm');
  if (uploadForm) {
    uploadForm.addEventListener('submit', function(e) {
      e.preventDefault();
      uploadFiles();
    });
  }
  
  // Search functionality
  const searchInput = document.getElementById('searchInput');
  const typeFilter = document.getElementById('typeFilter');
  
  if (searchInput) {
    searchInput.addEventListener('input', filterFiles);
  }
  
  if (typeFilter) {
    typeFilter.addEventListener('change', filterFiles);
  }
  
  // View toggle
  const gridView = document.getElementById('gridView');
  const listView = document.getElementById('listView');
  const gridContainer = document.getElementById('filesGridView');
  const listContainer = document.getElementById('filesListView');
  
  if (gridView && listView) {
    gridView.addEventListener('click', function() {
      gridView.classList.add('active');
      listView.classList.remove('active');
      gridContainer.classList.remove('d-none');
      listContainer.classList.add('d-none');
      localStorage.setItem('viewMode', 'grid');
    });
    
    listView.addEventListener('click', function() {
      listView.classList.add('active');
      gridView.classList.remove('active');
      listContainer.classList.remove('d-none');
      gridContainer.classList.add('d-none');
      localStorage.setItem('viewMode', 'list');
    });
    
    // Load saved view mode
    const savedView = localStorage.getItem('viewMode') || 'grid';
    if (savedView === 'list') {
      listView.click();
    }
  }
  
  // Bulk selection
  const selectAll = document.getElementById('selectAll');
  if (selectAll) {
    selectAll.addEventListener('change', function() {
      const checkboxes = document.querySelectorAll('.file-checkbox');
      checkboxes.forEach(cb => cb.checked = this.checked);
      updateBulkActions();
    });
  }
  
  // File checkboxes
  document.addEventListener('change', function(e) {
    if (e.target.classList.contains('file-checkbox')) {
      updateBulkActions();
    }
  });
});

function displaySelectedFiles(files) {
  const fileList = document.getElementById('fileList');
  const uploadBtn = document.getElementById('uploadBtn');
  
  if (files.length === 0) {
    fileList.innerHTML = '';
    uploadBtn.disabled = true;
    return;
  }
  
  let html = '<div class="border rounded p-3"><h6>Selected Files:</h6><ul class="list-unstyled mb-0">';
  
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const size = formatFileSize(file.size);
    html += `<li class="d-flex justify-content-between align-items-center">
      <span><i class="bi bi-file-earmark me-2"></i>${file.name}</span>
      <span class="text-muted">${size}</span>
    </li>`;
  }
  
  html += '</ul></div>';
  fileList.innerHTML = html;
  uploadBtn.disabled = false;
}

function uploadFiles() {
  const fileInput = document.getElementById('fileInput');
  const progressBar = document.querySelector('#uploadProgress .progress-bar');
  const progressContainer = document.getElementById('uploadProgress');
  const statusDiv = document.getElementById('uploadStatus');
  
  if (!fileInput.files.length) {
    statusDiv.innerHTML = '<div class="alert alert-warning">Please select files to upload</div>';
    return;
  }
  
  const formData = new FormData();
  for (let i = 0; i < fileInput.files.length; i++) {
    formData.append('files', fileInput.files[i]);
  }
  
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/upload', true);
  
  xhr.upload.addEventListener('progress', function(e) {
    if (e.lengthComputable) {
      const percentComplete = (e.loaded / e.total) * 100;
      progressBar.style.width = percentComplete + '%';
      progressBar.textContent = Math.round(percentComplete) + '%';
    }
  });
  
  xhr.onloadstart = function() {
    progressContainer.classList.remove('d-none');
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-upload me-2"></i>Uploading files...</div>';
  };
  
  xhr.onload = function() {
    if (xhr.status === 200) {
      const response = JSON.parse(xhr.responseText);
      statusDiv.innerHTML = `<div class="alert alert-success"><i class="bi bi-check-circle me-2"></i>${response.message}</div>`;
      setTimeout(() => window.location.reload(), 1500);
    } else {
      statusDiv.innerHTML = '<div class="alert alert-danger"><i class="bi bi-exclamation-triangle me-2"></i>Upload failed</div>';
    }
  };
  
  xhr.onerror = function() {
    statusDiv.innerHTML = '<div class="alert alert-danger"><i class="bi bi-exclamation-triangle me-2"></i>Upload failed</div>';
  };
  
  xhr.send(formData);
}

function clearFiles() {
  const fileInput = document.getElementById('fileInput');
  const fileList = document.getElementById('fileList');
  const uploadBtn = document.getElementById('uploadBtn');
  
  fileInput.value = '';
  fileList.innerHTML = '';
  uploadBtn.disabled = true;
}

function filterFiles() {
  const searchTerm = document.getElementById('searchInput').value.toLowerCase();
  const typeFilter = document.getElementById('typeFilter').value;
  const fileElements = document.querySelectorAll('[data-filename]');
  
  fileElements.forEach(element => {
    const filename = element.dataset.filename.toLowerCase();
    const filetype = element.dataset.type;
    
    const matchesSearch = filename.includes(searchTerm);
    const matchesType = !typeFilter || filetype === typeFilter;
    
    if (matchesSearch && matchesType) {
      element.style.display = '';
    } else {
      element.style.display = 'none';
    }
  });
}

function previewFile(fileType, url, filename) {
  const modal = document.getElementById('previewModal');
  const content = document.getElementById('previewContent');
  content.innerHTML = '';
  
  // Update file stats
  fetch(`/stats/${encodeURIComponent(filename)}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({action: 'view'})
  });
  
  if (fileType === 'image') {
    const img = document.createElement('img');
    img.src = url;
    img.className = 'img-fluid';
    img.style.maxHeight = '90vh';
    content.appendChild(img);
  } else if (fileType === 'video') {
    const video = document.createElement('video');
    video.src = url;
    video.controls = true;
    video.autoplay = true;
    video.className = 'w-100';
    video.style.maxHeight = '90vh';
    content.appendChild(video);
  } else if (fileType === 'audio') {
    const audio = document.createElement('audio');
    audio.src = url;
    audio.controls = true;
    audio.autoplay = true;
    audio.className = 'w-100';
    content.appendChild(audio);
  } else if (fileType === 'pdf') {
    const iframe = document.createElement('iframe');
    iframe.src = url;
    iframe.className = 'w-100';
    iframe.style.height = '90vh';
    content.appendChild(iframe);
  }
  
  modal.style.display = 'block';
}

function closePreview() {
  const modal = document.getElementById('previewModal');
  const content = document.getElementById('previewContent');
  modal.style.display = 'none';
  content.innerHTML = '';
}

function deleteFile(filename) {
  if (confirm(`Are you sure you want to delete "${filename}"?`)) {
    const form = document.getElementById('deleteForm');
    form.action = '/delete/' + encodeURIComponent(filename);
    form.submit();
  }
}

function updateBulkActions() {
  const checkboxes = document.querySelectorAll('.file-checkbox:checked');
  const bulkActions = document.getElementById('bulkActions');
  const selectedCount = document.getElementById('selectedCount');
  
  if (checkboxes.length > 0) {
    bulkActions.classList.remove('d-none');
    selectedCount.textContent = checkboxes.length;
  } else {
    bulkActions.classList.add('d-none');
  }
}

function bulkDelete() {
  const checkboxes = document.querySelectorAll('.file-checkbox:checked');
  const filenames = Array.from(checkboxes).map(cb => cb.value);
  
  if (filenames.length === 0) return;
  
  if (confirm(`Delete ${filenames.length} selected files?`)) {
    fetch('/bulk-delete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({files: filenames})
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        location.reload();
      } else {
        alert('Error deleting files: ' + data.message);
      }
    });
  }
}

function bulkDownload() {
  const checkboxes = document.querySelectorAll('.file-checkbox:checked');
  const filenames = Array.from(checkboxes).map(cb => cb.value);
  
  if (filenames.length === 0) return;
  
  // Create form to download files
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = '/bulk-download';
  
  filenames.forEach(filename => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'files[]';
    input.value = filename;
    form.appendChild(input);
  });
  
  document.body.appendChild(form);
  form.submit();
  document.body.removeChild(form);
}

function clearSelection() {
  const checkboxes = document.querySelectorAll('.file-checkbox');
  checkboxes.forEach(cb => cb.checked = false);
  updateBulkActions();
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Close modal on ESC key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closePreview();
  }
});

// Close modal on click outside
document.getElementById('previewModal').addEventListener('click', function(e) {
  if (e.target === this) {
    closePreview();
  }
});
</script>
</body>
</html>
'''

def get_file_type(filename):
    """Determine file type for UI display"""
    mime, _ = mimetypes.guess_type(filename)
    if mime:
        if mime.startswith('image/'):
            return 'image'
        elif mime.startswith('video/'):
            return 'video'
        elif mime.startswith('audio/'):
            return 'audio'
        elif mime == 'application/pdf':
            return 'pdf'
        elif mime.startswith('text/'):
            return 'text'
    return 'other'

def get_file_list():
    """Get list of files with metadata"""
    files = []
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, filename)
            # Skip system files
            if os.path.isfile(path) and not filename.startswith('.') and \
               filename not in ['server_config.json', 'users.json', 'file_stats.json'] and \
               not filename.endswith('.py') and \
               not filename.endswith('.pyc') and \
               not filename.endswith('.bat') and \
               not filename.endswith('.log'):
                
                size = os.path.getsize(path)
                size_str = format_file_size(size)
                modified = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
                
                files.append({
                    'name': filename,
                    'size': size_str,
                    'modified': modified,
                    'type': get_file_type(filename)
                })
        
        logger.info(f"Found {len(files)} files to display")
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        
    return sorted(files, key=lambda x: x['name'].lower())

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

def get_disk_usage():
    """Get disk usage statistics"""
    try:
        total_size = 0
        for filename in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(path):
                total_size += os.path.getsize(path)
        return format_file_size(total_size)
    except Exception as e:
        logger.error(f"Error calculating disk usage: {e}")
        return "Unknown"

@app.route('/', methods=['GET', 'POST'])
def login():
    """Handle login requests"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in users and verify_password(password, users[username]['password_hash']):
            session['logged_in'] = True
            session['username'] = username
            session['role'] = users[username]['role']
            logger.info(f"User {username} logged in successfully")
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('files'))
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            flash('Invalid username or password', 'error')
    
    return render_template_string(TEMPLATE, session=session, theme=config.get('theme', 'light'))

@app.route('/files')
@login_required
def files():
    """File listing page"""
    files_list = get_file_list()
    return render_template_string(
        TEMPLATE, 
        session=session, 
        files=files_list, 
        file_stats=file_stats,
        max_file_size=format_file_size(config.get('max_file_size', 100*1024*1024)),
        theme=config.get('theme', 'light')
    )

@app.route('/admin')
@admin_required
def admin():
    """Admin panel"""
    # Calculate statistics
    total_files = len(get_file_list())
    total_downloads = sum(stats.get('downloads', 0) for stats in file_stats.values())
    total_users = len(users)
    disk_usage = get_disk_usage()
    
    return render_template_string(
        TEMPLATE,
        session=session,
        page='admin',
        users=users,
        file_stats=file_stats,
        total_files=total_files,
        total_downloads=total_downloads,
        total_users=total_users,
        disk_usage=disk_usage,
        theme=config.get('theme', 'light')
    )

@app.route('/admin', methods=['POST'])
@admin_required
def admin_actions():
    """Handle admin actions"""
    action = request.form.get('action')
    
    if action == 'add_user':
        username = request.form.get('new_username')
        password = request.form.get('new_password')
        role = request.form.get('new_role', 'user')
        
        if username and password:
            if username not in users:
                users[username] = {
                    'password_hash': hash_password(password),
                    'role': role,
                    'created': datetime.datetime.now().isoformat()
                }
                save_json_file(USERS_FILE, users)
                logger.info(f"User {username} created by {session['username']}")
                flash(f'User {username} created successfully', 'success')
            else:
                flash('Username already exists', 'error')
        else:
            flash('Username and password required', 'error')
    
    elif action == 'delete_user':
        username = request.form.get('username')
        if username and username != 'admin' and username in users:
            del users[username]
            save_json_file(USERS_FILE, users)
            logger.info(f"User {username} deleted by {session['username']}")
            flash(f'User {username} deleted', 'success')
        else:
            flash('Cannot delete user', 'error')
    
    return redirect(url_for('admin'))

@app.route('/files_raw/<path:filename>')
@login_required
def files_raw(filename):
    """Serve files for in-browser viewing"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/files/<path:filename>')
@login_required
def download(filename):
    """Download files as attachments"""
    try:
        update_file_stats(filename, 'download')
        logger.info(f"File downloaded: {filename} by {session['username']}")
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        flash('Error downloading file', 'error')
        return redirect(url_for('files'))

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle file uploads"""
    try:
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or uploaded_files[0].filename == '':
            return jsonify({'status': 'error', 'message': 'No files selected'}), 400
        
        successful_uploads = 0
        max_size = config.get('max_file_size', 100*1024*1024)
        allowed_extensions = config.get('allowed_extensions', [])
        
        for file in uploaded_files:
            if file and file.filename:
                # Check file size
                if len(file.read()) > max_size:
                    logger.warning(f"File {file.filename} too large, skipped")
                    continue
                
                file.seek(0)  # Reset file pointer
                
                # Check file extension
                if allowed_extensions:
                    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                    if ext not in allowed_extensions:
                        logger.warning(f"File {file.filename} has disallowed extension, skipped")
                        continue
                
                # Save file
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)
                update_file_stats(file.filename, 'upload')
                successful_uploads += 1
                logger.info(f"File uploaded: {file.filename} by {session['username']}")
        
        return jsonify({
            'status': 'success', 
            'message': f'{successful_uploads} file(s) uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        return jsonify({'status': 'error', 'message': 'Upload failed'}), 500

@app.route('/delete/<path:filename>', methods=['POST'])
@login_required
def delete(filename):
    """Delete files"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            # Remove from stats
            if filename in file_stats:
                del file_stats[filename]
                save_json_file(STATS_FILE, file_stats)
            logger.info(f"File deleted: {filename} by {session['username']}")
            flash(f'File {filename} deleted successfully', 'success')
        else:
            flash('File not found', 'error')
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}")
        flash('Error deleting file', 'error')
    
    return redirect(url_for('files'))

@app.route('/bulk-delete', methods=['POST'])
@login_required
def bulk_delete():
    """Delete multiple files"""
    try:
        data = request.get_json()
        filenames = data.get('files', [])
        deleted_count = 0
        
        for filename in filenames:
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                if filename in file_stats:
                    del file_stats[filename]
                deleted_count += 1
                logger.info(f"File deleted: {filename} by {session['username']}")
        
        save_json_file(STATS_FILE, file_stats)
        return jsonify({'success': True, 'message': f'{deleted_count} files deleted'})
        
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/bulk-download', methods=['POST'])
@login_required
def bulk_download():
    """Download multiple files as zip"""
    try:
        import zipfile
        import io
        
        filenames = request.form.getlist('files[]')
        
        # Create zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename in filenames:
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.exists(file_path):
                    zip_file.write(file_path, filename)
                    update_file_stats(filename, 'download')
        
        zip_buffer.seek(0)
        
        logger.info(f"Bulk download of {len(filenames)} files by {session['username']}")
        
        from flask import Response
        return Response(
            zip_buffer.getvalue(),
            mimetype='application/zip',
            headers={'Content-Disposition': 'attachment; filename=files.zip'}
        )
        
    except Exception as e:
        logger.error(f"Error in bulk download: {e}")
        flash('Error creating download', 'error')
        return redirect(url_for('files'))

@app.route('/stats/<path:filename>', methods=['POST'])
@login_required
def update_stats(filename):
    """Update file statistics"""
    try:
        data = request.get_json()
        action = data.get('action')
        update_file_stats(filename, action)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating stats for {filename}: {e}")
        return jsonify({'success': False})

@app.route('/logout')
@login_required
def logout():
    """Handle logout"""
    username = session.get('username')
    session.clear()
    logger.info(f"User {username} logged out")
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.errorhandler(404)
def not_found(error):
    return render_template_string('''
    <div class="container mt-5">
        <div class="text-center">
            <h1>404 - Page Not Found</h1>
            <p>The page you're looking for doesn't exist.</p>
            <a href="{{ url_for('files') }}" class="btn btn-primary">Go Home</a>
        </div>
    </div>
    '''), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template_string('''
    <div class="container mt-5">
        <div class="text-center">
            <h1>500 - Internal Server Error</h1>
            <p>Something went wrong on our end.</p>
            <a href="{{ url_for('files') }}" class="btn btn-primary">Go Home</a>
        </div>
    </div>
    '''), 500

def run_server():
    """Run the Flask server"""
    host = config.get('host', '0.0.0.0')
    port = config.get('port', 50588)
    
    logger.info("=" * 60)
    logger.info("Enhanced File Server Starting")
    logger.info("=" * 60)
    logger.info(f"Username: admin")
    logger.info(f"Password: 1234")
    logger.info("-" * 60)
    
    if host == '0.0.0.0':
        logger.info("Server is available at:")
        logger.info(f"- Local: http://localhost:{port}")
        logger.info(f"- Network: http://<YOUR-IP>:{port}")
    else:
        logger.info(f"Server is available at: http://{host}:{port}")
    
    logger.info("=" * 60)
    
    app.run(host=host, port=port, debug=False, threaded=True)

def start_server_background():
    """Start the server in a background thread"""
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    return server_thread

if __name__ == '__main__':
    # Initialize mimetypes
    mimetypes.init()
    
    # Save default configuration if not exists
    if not os.path.exists(CONFIG_FILE):
        save_json_file(CONFIG_FILE, config)
    
    # Save default users if not exists
    if not os.path.exists(USERS_FILE):
        save_json_file(USERS_FILE, users)
    
    # Run server
    run_server()