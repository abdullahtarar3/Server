# Enhanced File Server 🚀

A powerful, feature-rich Flask-based file server with modern web interface, user authentication, and comprehensive file management capabilities.

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![Flask](https://img.shields.io/badge/flask-v2.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macos-lightgrey.svg)

## 📋 Table of Contents

- [Features](#-features)
- [Screenshots](#-screenshots)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Security](#-security)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [Developer Info](#-developer-info)
- [License](#-license)

## ✨ Features

### 🔒 Authentication & Security
- **Multi-user support** with role-based access control
- **Secure password hashing** using PBKDF2
- **Session management** with secure tokens
- **Admin panel** for user management

### 📁 File Management
- **Drag & drop uploads** with progress tracking
- **Bulk operations** (upload, download, delete)
- **File previews** for images, videos, audio, and PDFs
- **Search and filtering** capabilities
- **File statistics** tracking (downloads, views)

### 🎨 Modern Interface
- **Responsive Bootstrap 5** design
- **Dark/Light theme** toggle
- **Grid and list views** for file display
- **Real-time file operations**
- **Interactive notifications**

### ⚙️ Advanced Features
- **Configurable file size limits**
- **Extension filtering**
- **Comprehensive logging**
- **Network interface detection**
- **Auto-configuration**

## 📸 Screenshots

### Login Interface
Clean and secure authentication system with modern design.

### File Management Dashboard
Intuitive file browser with drag-and-drop functionality and bulk operations.

### Admin Panel
Comprehensive administration interface with user management and analytics.

## 🚀 Quick Start

### Windows Users (Recommended)
1. Download the project files
2. Double-click `server.bat`
3. Follow the interactive setup
4. Access the server at the displayed URL

### Manual Setup
```bash
# Clone the repository
git clone https://github.com/abdullahtarar3/enhanced-file-server.git
cd enhanced-file-server

# Install dependencies
pip install flask

# Run the server
python app.py
```

## 📦 Installation

### Prerequisites
- **Python 3.7+** installed and added to PATH
- **pip** package manager
- **Flask** framework

### Automatic Installation (Windows)
The `server.bat` script handles everything automatically:

1. **Python verification**
2. **Dependency installation**
3. **Network configuration**
4. **Server launch**

### Manual Installation
```bash
# Install required packages
pip install flask

# Optional: Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## 🔧 Usage

### Starting the Server

#### Method 1: Automated Script (Windows)
```batch
# Simply run the batch file
server.bat
```

#### Method 2: Direct Python Execution
```bash
python app.py
```

### Default Credentials
- **Username:** `admin`
- **Password:** `1234`

⚠️ **Change default password immediately in production!**

### Basic Operations

#### File Upload
1. **Drag and drop** files onto the upload zone
2. **Click** the upload zone to browse files
3. **Multiple files** supported
4. **Progress tracking** during upload

#### File Management
- **Preview:** Click on supported file types
- **Download:** Individual or bulk downloads
- **Delete:** Single or multiple file deletion
- **Search:** Real-time file filtering

#### User Management (Admin Only)
- **Add users** with custom roles
- **Delete users** (except admin)
- **View statistics** and analytics

## ⚙️ Configuration

### Server Configuration (`server_config.json`)
```json
{
  "host": "0.0.0.0",
  "port": 50588,
  "max_file_size": 5368709120,
  "allowed_extensions": ["txt", "pdf", "png", "jpg", "jpeg", "gif", "mp4", "mp3"],
  "enable_public_sharing": true,
  "theme": "light"
}
```

### Environment Variables
```bash
# Optional environment variables
export FLASK_HOST=0.0.0.0
export FLASK_PORT=50588
export FLASK_DEBUG=false
```

### Network Configuration
The server supports multiple network interfaces:
- **Localhost** (127.0.0.1)
- **Local network** (192.168.x.x)
- **Custom IP** addresses

## 📡 API Documentation

### Authentication Endpoints
```http
POST /              # Login
GET  /logout        # Logout
```

### File Operations
```http
GET    /files                    # List files
POST   /upload                   # Upload files
GET    /files/<filename>         # Download file
POST   /delete/<filename>        # Delete file
POST   /bulk-delete              # Delete multiple files
POST   /bulk-download            # Download multiple files
GET    /files_raw/<filename>     # View file in browser
```

### Administration
```http
GET  /admin         # Admin dashboard
POST /admin         # Admin actions (user management)
```

### Statistics
```http
POST /stats/<filename>  # Update file statistics
```

## 🔐 Security

### Authentication
- **PBKDF2** password hashing with salt
- **Session-based** authentication
- **Role-based** access control
- **Secure session** tokens

### File Security
- **Extension filtering** to prevent malicious uploads
- **File size limits** to prevent abuse
- **Directory traversal** protection
- **Input validation** on all endpoints

### Network Security
- **Configurable host binding**
- **Port customization**
- **Request logging** for monitoring

### Best Practices
1. **Change default credentials** immediately
2. **Use HTTPS** in production (reverse proxy recommended)
3. **Configure firewall** rules appropriately
4. **Regular security updates**
5. **Monitor logs** for suspicious activity

## 🐛 Troubleshooting

### Common Issues

#### Python Not Found
```bash
# Windows: Add Python to PATH
# Or use full path
C:\Python39\python.exe app.py
```

#### Port Already in Use
```bash
# Check what's using the port
netstat -ano | findstr :50588

# Kill the process or change port in config
```

#### Permission Denied
```bash
# Linux/Mac: Use higher port number (>1024)
# Or run with sudo (not recommended)
```

#### Flask Import Error
```bash
# Install Flask
pip install flask

# Check installation
python -c "import flask; print(flask.__version__)"
```

### Log Files
- **Location:** `logs/file_server.log`
- **Rotation:** Automatic with size limits
- **Level:** INFO, WARNING, ERROR

### Debug Mode
Enable debug mode by modifying `app.py`:
```python
app.run(host=host, port=port, debug=True)
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Getting Started
1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

### Development Setup
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/enhanced-file-server.git

# Create development environment
python -m venv dev-env
source dev-env/bin/activate

# Install development dependencies
pip install flask pytest black flake8

# Run tests
python -m pytest tests/
```

### Code Style
- **Follow PEP 8** Python style guide
- **Use Black** for code formatting
- **Add docstrings** to functions
- **Write tests** for new features

### Pull Request Guidelines
- **Clear description** of changes
- **Include tests** for new functionality
- **Update documentation** as needed
- **Follow commit** message conventions

## 👨‍💻 Developer Info

### About the Developer
**Abdullah Tarar** - Full Stack Developer & Open Source Enthusiast

### Connect With Me
- 🌐 **GitHub:** [@abdullahtarar3](https://github.com/abdullahtarar3)
- 📷 **Instagram:** [@abdullahtarar.3](https://instagram.com/abdullahtarar.3)
- 💼 **LinkedIn:** [Abdullah Tarar](https://linkedin.com/in/abdullah-tarar)
- 📧 **Email:** [Contact Me](mailto:your-email@example.com)

### Support the Project
If you find this project helpful:
- ⭐ **Star** the repository
- 🐛 **Report** bugs and issues
- 💡 **Suggest** new features
- 🤝 **Contribute** code improvements
- 📢 **Share** with others

### Other Projects
Check out my other open source projects:
- [Project 1](https://github.com/abdullahtarar3/project1)
- [Project 2](https://github.com/abdullahtarar3/project2)

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### MIT License Summary
- ✅ **Commercial use** allowed
- ✅ **Modification** allowed
- ✅ **Distribution** allowed
- ✅ **Private use** allowed
- ❌ **Liability** - Use at your own risk
- ❌ **Warranty** - No warranty provided

## 📊 Project Stats

![GitHub stars](https://img.shields.io/github/stars/abdullahtarar3/enhanced-file-server.svg)
![GitHub forks](https://img.shields.io/github/forks/abdullahtarar3/enhanced-file-server.svg)
![GitHub issues](https://img.shields.io/github/issues/abdullahtarar3/enhanced-file-server.svg)
![GitHub license](https://img.shields.io/github/license/abdullahtarar3/enhanced-file-server.svg)

## 🙏 Acknowledgments

- **Flask** community for the amazing framework
- **Bootstrap** team for the beautiful UI components
- **Open source** contributors worldwide
- **Beta testers** and early adopters

---

### 🎯 Future Plans

- [ ] **Docker** containerization
- [ ] **HTTPS** support
- [ ] **Cloud storage** integration
- [ ] **Real-time** collaboration
- [ ] **Mobile app** companion
- [ ] **Plugin** system

---

<div align="center">

**Made with ❤️ by [Abdullah Tarar](https://github.com/abdullahtarar3)**

*If you like this project, please consider giving it a ⭐*

</div>
