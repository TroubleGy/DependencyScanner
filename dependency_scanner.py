# dependency_scanner.py

import os
import sys
import ast # Import the Abstract Syntax Tree module
import re
import logging
import json
import toml  # For pyproject.toml parsing
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QFileDialog, QMessageBox, QFrame, QSizePolicy,
                             QStatusBar, QComboBox, QTabWidget) # Import QStatusBar, QComboBox, and QTabWidget
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QDir, Qt, QUrl # Import Qt for alignment, QUrl for opening links
from PyQt6.QtGui import QColor, QPalette, QFont, QIcon, QPixmap, QDesktopServices # Import QFont, QIcon, QPixmap, QDesktopServices
from pathlib import Path
from stdlib_list import stdlib_list # Import stdlib_list
import platform # Import platform to get Python version
import importlib.util # For checking installed modules
import subprocess # For opening links
import pkg_resources

# Setup logging
logging.basicConfig(
    filename='scanner.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Default directories to exclude
DEFAULT_EXCLUDE_DIRS = ['.git', '__pycache__', 'venv', '.venv', 'build', 'dist', 'tests', 'node_modules']

# --- Worker Thread for Scanning ---
class DependencyScannerWorker(QObject):
    # Signals to communicate with the main GUI thread
    status_update = pyqtSignal(str)
    scan_finished = pyqtSignal(set)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str) # Signal for status bar updates
    dependency_found = pyqtSignal(str) # Add new signal for live updates

    def __init__(self, folder_path, language, exclude_dirs=None):
        super().__init__()
        self.folder_path = folder_path
        self.language = language # Store selected language
        self._is_running = True # Flag to potentially stop the scan
        self.exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS
        logging.info(f"Initialized scanner for {folder_path} ({language})")

    def run(self):
        """Main function for the worker thread."""
        self.status_update.emit(f"Starting scan in folder: {self.folder_path} for {self.language}...")
        self.progress_update.emit(f"Scanning {self.language} project...")
        potential_dependencies = set()
        logging.info(f"Worker: Starting scan in {self.folder_path} for {self.language}")

        if not os.path.isdir(self.folder_path):
            error_msg = f"Error: Folder not found at '{self.folder_path}'"
            self.error_occurred.emit(error_msg)
            self.scan_finished.emit(potential_dependencies)
            self.progress_update.emit("Scan failed.")
            logging.error(f"Worker: {error_msg}")
            return

        if self.language == "Python":
            logging.info("Worker: Initiating Python project scan.")
            potential_dependencies = self.scan_python_project()
        elif self.language == "Node.js":
            logging.info("Worker: Initiating Node.js project scan.")
            potential_dependencies = self.scan_nodejs_project()
        else:
            logging.warning(f"Worker: Unknown language selected: {self.language}")
            self.status_update.emit(f"Unknown language: {self.language}")

        logging.info(f"Worker: Scan finished. Found {len(potential_dependencies)} dependencies.")
        self.scan_finished.emit(potential_dependencies)
        self.progress_update.emit("Scan complete.")

    def _is_installed(self, pkg_name):
        """Checks if a Python package is installed."""
        try:
            spec = importlib.util.find_spec(pkg_name)
            return spec is not None
        except Exception as e:
            logging.error(f"Error checking if {pkg_name} is installed: {e}")
            return False

    def scan_python_project(self):
        """Scans Python files and configuration files for dependencies."""
        logging.info("Python scanner: Starting Python project scan.")
        potential_dependencies = set()
        
        # First scan configuration files
        logging.info("Python scanner: Scanning Python configuration files.")
        config_deps = self.scan_python_config_files()
        potential_dependencies.update(config_deps)
        logging.info(f"Python scanner: Found {len(config_deps)} dependencies from config files.")
        
        # Then scan Python files
        logging.info("Python scanner: Scanning Python code files.")
        code_deps = self._scan_python_files()
        potential_dependencies.update(code_deps)
        logging.info(f"Python scanner: Found {len(code_deps)} dependencies from code files.")
        
        return potential_dependencies

    def scan_python_config_files(self):
        """Scans Python configuration files for dependencies."""
        deps = set()
        project_root = Path(self.folder_path)

        # Scan requirements.txt
        req_files = list(project_root.glob('**/requirements*.txt'))
        if not req_files:
            logging.info("Python config: No requirements.txt files found.")
        for req_file in req_files:
            logging.info(f"Python config: Scanning requirements file: {req_file}")
            self.status_update.emit(f"Scanning requirements file: {req_file}")
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            pkg_name = re.match(r'^([A-Za-z0-9_\-\.]+)', line)
                            if pkg_name:
                                dep_name = pkg_name.group(1)
                                deps.add(dep_name)
                                self.dependency_found.emit(dep_name)
                                logging.info(f"Python config: Found dependency in requirements.txt: {dep_name}")
            except Exception as e:
                logging.error(f"Python config: Error reading {req_file}: {e}")
                self.status_update.emit(f"Error reading {req_file}: {e}")

        # Scan pyproject.toml
        pyproject_path = project_root / 'pyproject.toml'
        if pyproject_path.exists():
            logging.info(f"Python config: Scanning pyproject.toml: {pyproject_path}")
            self.status_update.emit(f"Scanning pyproject.toml: {pyproject_path}")
            try:
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    data = toml.load(f)
                    if 'project' in data:
                        if 'dependencies' in data['project']:
                            for dep in data['project']['dependencies']:
                                pkg_name = re.match(r'^([A-Za-z0-9_\-\.]+)', dep)
                                if pkg_name:
                                    dep_name = pkg_name.group(1)
                                    deps.add(dep_name)
                                    self.dependency_found.emit(dep_name)
                                    logging.info(f"Python config: Found dependency in pyproject.toml (dependencies): {dep_name}")
                        if 'optional-dependencies' in data['project']:
                            for group_name, group_deps in data['project']['optional-dependencies'].items():
                                for dep in group_deps:
                                    pkg_name = re.match(r'^([A-Za-z0-9_\-\.]+)', dep)
                                    if pkg_name:
                                        dep_name = pkg_name.group(1)
                                        deps.add(dep_name)
                                        self.dependency_found.emit(dep_name)
                                        logging.info(f"Python config: Found dependency in pyproject.toml (optional-dependencies - {group_name}): {dep_name}")
            except Exception as e:
                logging.error(f"Python config: Error reading pyproject.toml: {e}")
                self.status_update.emit(f"Error reading pyproject.toml: {e}")
        else:
            logging.info("Python config: No pyproject.toml found.")

        return deps

    def _scan_python_files(self):
        """Internal method to scan Python files using AST and regex."""
        potential_dependencies = set()
        built_in_modules = set(sys.builtin_module_names)

        try:
            python_version = platform.python_version().rsplit('.', 1)[0]
            logging.info(f"Python code: Using Python version {python_version}")
            
            try:
                # Get available versions from stdlib_list module
                import pkg_resources
                
                # Get all available versions from the package
                available_versions = []
                for version in pkg_resources.working_set:
                    if version.key == 'stdlib-list':
                        available_versions = [v for v in version.parsed_version]
                        break
                
                if not available_versions:
                    # If we can't get versions, try to use the current Python version
                    try:
                        standard_library_modules = set(stdlib_list(python_version))
                    except Exception:
                        # If that fails, use a known working version
                        standard_library_modules = set(stdlib_list('3.11'))
                else:
                    # Find the closest available version
                    closest_version = max([v for v in available_versions if v < python_version], default='3.11')
                    logging.info(f"Python code: Using stdlib_list version {closest_version}")
                    standard_library_modules = set(stdlib_list(closest_version))
                
                logging.info(f"Python code: Successfully loaded stdlib_list")
            except Exception as e:
                logging.warning(f"Python code: Error loading stdlib_list: {e}. Using fallback list.")
                standard_library_modules = {
                    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio", "asyncore",
                    "atexit", "base64", "bdb", "binascii", "binhex", "bisect", "builtins", "bz2",
                    "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code", "codecs", "codeop",
                    "collections", "colorsys", "compileall", "concurrent", "configparser", "contextlib",
                    "copy", "copyreg", "csv", "ctypes", "cProfile", "dataclasses", "datetime", "dbm",
                    "decimal", "difflib", "dis", "distutils", "doctest", "email", "encodings", "errno",
                    "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch", "formatter", "fractions",
                    "ftplib", "functools", "gc", "getopt", "getpass", "gettext", "glob", "graphlib",
                    "grp", "gzip", "hashlib", "heapq", "hmac", "html", "http", "imaplib", "imghdr",
                    "imp", "importlib", "inspect", "io", "ipaddress", "itertools", "json", "keyword",
                    "lib2to3", "linecache", "locale", "logging", "lzma", "mailbox", "mailcap", "marshal",
                    "math", "mimetypes", "mmap", "modulefinder", "msvcrt", "multiprocessing", "netrc",
                    "nis", "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev", "parser",
                    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
                    "poplib", "posix", "pprint", "profile", "pstats", "pty", "pwd", "py_compile",
                    "pyclbr", "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
                    "resource", "rlcompleter", "runpy", "sched", "secrets", "select", "selectors",
                    "shelve", "shlex", "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr",
                    "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat", "statistics", "string",
                    "stringprep", "struct", "subprocess", "sunau", "symtable", "sys", "sysconfig",
                    "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile", "textwrap", "this", "threading", "time", "timeit", "tkinter", "token", "tokenize",
                    "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing",
                    "unicodedata", "unittest", "urllib", "uu", "uuid", "venv", "warnings", "wave",
                    "weakref", "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib", "xml",
                    "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib", "pkg_resources" # pkg_resources, because it's part of setuptools
                }

            excluded_modules = built_in_modules.union(standard_library_modules)
            logging.info(f"Python code: Excluded modules count: {len(excluded_modules)}")

            for root, dirs, files in os.walk(self.folder_path):
                try:
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                    if any(exclude_dir in root for exclude_dir in self.exclude_dirs):
                        logging.info(f"Python code: Skipping excluded directory: {root}")
                        continue

                    if not self._is_running:
                        logging.info("Python code: Scan interrupted by user")
                        break

                    for file in files:
                        if not self._is_running:
                            break
                            
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            logging.info(f"Python code: Processing file: {file_path}")
                            self.status_update.emit(f"  Parsing: {file_path}")
                            self.progress_update.emit(f"Parsing: {file}")

                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()

                                try:
                                    tree = ast.parse(content)
                                except SyntaxError as e:
                                    logging.warning(f"Python code: Syntax error in {file_path}: {e}")
                                    self.status_update.emit(f"Warning: Syntax error in {file_path}")
                                    continue
                                except Exception as e:
                                    logging.error(f"Python code: Error parsing AST in {file_path}: {e}")
                                    self.status_update.emit(f"Error parsing {file_path}")
                                    continue

                                for node in ast.walk(tree):
                                    try:
                                        if isinstance(node, ast.Import):
                                            for alias in node.names:
                                                try:
                                                    package_name = alias.name.split('.')[0]
                                                    if self._is_valid_package(package_name, excluded_modules):
                                                        potential_dependencies.add(package_name)
                                                        self.dependency_found.emit(package_name)
                                                        logging.info(f"Python code: Found static import: {package_name}")
                                                    else:
                                                        logging.debug(f"Python code: Skipping standard/builtin import: {package_name}")
                                                except Exception as e:
                                                    logging.error(f"Python code: Error processing import alias {alias.name}: {e}")
                                        elif isinstance(node, ast.ImportFrom):
                                            if node.module:
                                                try:
                                                    package_name = node.module.split('.')[0]
                                                    if self._is_valid_package(package_name, excluded_modules):
                                                        potential_dependencies.add(package_name)
                                                        self.dependency_found.emit(package_name)
                                                        logging.info(f"Python code: Found from-import: {package_name}")
                                                    else:
                                                        logging.debug(f"Python code: Skipping standard/builtin from-import: {package_name}")
                                                except Exception as e:
                                                    logging.error(f"Python code: Error processing from-import {node.module}: {e}")
                                    except Exception as e:
                                        logging.error(f"Python code: Error processing AST node in {file_path}: {e}")

                                try:
                                    dynamic_imports = re.findall(r'importlib\.import_module\(["\']([\w\.]+)["\']\)', content)
                                    for module_name in dynamic_imports:
                                        try:
                                            package_name = module_name.split('.')[0]
                                            if self._is_valid_package(package_name, excluded_modules):
                                                potential_dependencies.add(package_name)
                                                self.dependency_found.emit(package_name)
                                                logging.info(f"Python code: Found dynamic import (importlib): {package_name}")
                                            else:
                                                logging.debug(f"Python code: Skipping dynamic import (importlib - standard/builtin): {package_name}")
                                        except Exception as e:
                                            logging.error(f"Python code: Error processing dynamic import {module_name}: {e}")
                                except Exception as e:
                                    logging.error(f"Python code: Error processing dynamic imports in {file_path}: {e}")

                            except UnicodeDecodeError as e:
                                logging.error(f"Python code: Unicode decode error in {file_path}: {e}")
                                self.status_update.emit(f"Error: Cannot read {file_path} (encoding issue)")
                            except Exception as e:
                                logging.error(f"Python code: Error processing file {file_path}: {e}")
                                self.status_update.emit(f"Error processing {file_path}")

                except Exception as e:
                    logging.error(f"Python code: Error processing directory {root}: {e}")
                    continue

            logging.info(f"Python code: Finished scanning Python files. Total unique dependencies found: {len(potential_dependencies)}")
            return potential_dependencies

        except Exception as e:
            logging.error(f"Python code: Critical error in _scan_python_files: {e}")
            self.error_occurred.emit(f"Critical error during Python file scanning: {e}")
            return potential_dependencies

    def _is_valid_package(self, package_name, excluded_modules):
        """Helper method to validate package names."""
        return (package_name and 
                package_name.isidentifier() and 
                package_name not in excluded_modules)

    def scan_nodejs_project(self):
        """Scans Node.js files for dependencies."""
        logging.info("Node.js scanner: Starting Node.js project scan.")
        potential_dependencies = set()
        
        # First scan package.json
        logging.info("Node.js scanner: Scanning package.json.")
        package_json_deps = self._scan_package_json()
        potential_dependencies.update(package_json_deps)
        logging.info(f"Node.js scanner: Found {len(package_json_deps)} dependencies from package.json.")
        
        # Then scan JS/TS files
        logging.info("Node.js scanner: Scanning JS/TS files.")
        code_deps = self._scan_js_ts_files()
        potential_dependencies.update(code_deps)
        logging.info(f"Node.js scanner: Found {len(code_deps)} dependencies from JS/TS code files.")
        
        return potential_dependencies

    def _scan_package_json(self):
        """Internal method to scan package.json file."""
        deps = set()
        package_json_path = os.path.join(self.folder_path, 'package.json')

        if not os.path.exists(package_json_path):
            logging.info("Node.js package.json: No package.json found.")
            self.status_update.emit("No package.json found")
            return deps

        logging.info(f"Node.js package.json: Scanning {package_json_path}")
        self.status_update.emit(f"Scanning package.json: {package_json_path}")

        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)

            for dep_type in ['dependencies', 'devDependencies', 'peerDependencies']:
                if dep_type in package_data:
                    for dep in package_data[dep_type]:
                        deps.add(dep)
                        self.dependency_found.emit(dep)
                        logging.info(f"Node.js package.json: Found {dep_type} dependency: {dep}")

        except json.JSONDecodeError as e:
            error_msg = f"Error parsing package.json: {e}"
            logging.error(f"Node.js package.json: {error_msg}")
            self.status_update.emit(error_msg)
        except Exception as e:
            error_msg = f"Error reading package.json: {e}"
            logging.error(f"Node.js package.json: {error_msg}")
            self.status_update.emit(error_msg)

        return deps

    def _scan_js_ts_files(self):
        """Internal method to scan JS/TS files for imports."""
        deps = set()
        
        for root, dirs, files in os.walk(self.folder_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            if any(exclude_dir in root for exclude_dir in self.exclude_dirs):
                logging.info(f"Node.js code: Skipping excluded directory: {root}")
                continue

            if not self._is_running:
                logging.info("Node.js code: Scan interrupted by user")
                break

            for file in files:
                if not self._is_running:
                    break
                    
                if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    file_path = os.path.join(root, file)
                    logging.info(f"Node.js code: Processing file: {file_path}")
                    self.status_update.emit(f"Scanning: {file_path}")

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        es6_imports = re.findall(r'import\s+(?:\*\s+as\s+\w+\s+from\s+)?[\'"]([\w\-_/]+)[\'"]', content)
                        commonjs_imports = re.findall(r'require\([\'"]([\w\-_/]+)[\'"]\)', content)
                        dynamic_js_imports = re.findall(r'import\([\'"]([\w\-_/]+)[\'"]\)', content)
                        
                        for dep in es6_imports + commonjs_imports + dynamic_js_imports:
                            pkg_name = dep.split('/')[0]

                            if pkg_name and not pkg_name.startswith('.'):
                                logging.info(f"Node.js code: Found JS/TS dependency: {pkg_name}")
                                deps.add(pkg_name)
                                self.dependency_found.emit(pkg_name)
                            else:
                                logging.debug(f"Node.js code: Skipping local/empty import: {pkg_name}")

                    except Exception as e:
                        error_msg = f"Error processing {file_path}: {e}"
                        logging.error(f"Node.js code: {error_msg}")
                        self.status_update.emit(error_msg)

        logging.info(f"Node.js code: Finished scanning JS/TS files. Total unique dependencies found: {len(deps)}")
        return deps

    def stop(self):
        """Method to stop the scanner gracefully."""
        self._is_running = False
        self.progress_update.emit("Scan interrupted.")


# --- Main Application Window ---
class DependencyScannerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.found_dependencies = set()
        self.worker = None
        self.thread = None
        self.current_scan_folder = None
        self.current_language = None
        self.translations = {}
        self.current_locale = "en"
        self.app_version = "1.1" # Define application version

        self.load_translations()
        self.init_ui()
        self.apply_translations()

    def load_translations(self):
        """Loads translations from a JSON file."""
        try:
            script_dir = os.path.dirname(__file__)
            translation_file = os.path.join(script_dir, 'assets', 'translations.json')
            logging.info(f"Attempting to load translations from: {translation_file}")
            with open(translation_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            logging.info("Translations loaded successfully.")
        except FileNotFoundError:
            logging.error(f"Translations file not found at {translation_file}. Please ensure it exists.")
            self.translations = {} # Fallback to empty if loading fails
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding translations.json at {translation_file}: {e}. Check JSON format.")
            self.translations = {} # Fallback to empty if loading fails
        except Exception as e:
            logging.error(f"Unexpected error loading translations from {translation_file}: {e}")
            self.translations = {} # Fallback to empty if loading fails

    def get_text(self, key):
        """Retrieves translated text for a given key and current locale."""
        return self.translations.get(self.current_locale, {}).get(key, key) # Fallback to key if not found

    def init_ui(self):
        """Sets up the user interface."""
        self.setWindowTitle(self.get_text("window_title"))
        self.setGeometry(100, 100, 700, 600)
        self.setAcceptDrops(True)

        # Set application icon
        script_dir = os.path.dirname(__file__)
        icon_path = os.path.join(script_dir, 'assets', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logging.warning(f"Application icon not found at {icon_path}")

        # Central widget is now a QTabWidget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # --- Main Tab ---
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Input Frame (Folder Selection)
        input_frame = QFrame(self)
        input_frame.setFrameShape(QFrame.Shape.StyledPanel)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(input_frame)

        self.folder_label = QLabel(self.get_text("project_folder_label"))
        self.folder_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        input_layout.addWidget(self.folder_label)

        self.folder_path_entry = QLineEdit(self)
        self.folder_path_entry.setPlaceholderText(self.get_text("folder_path_placeholder"))
        input_layout.addWidget(self.folder_path_entry, 1)

        self.browse_button = QPushButton(self.get_text("browse_button"))
        self.browse_button.clicked.connect(self.browse_folder)
        input_layout.addWidget(self.browse_button)

        # Project Language Selection Frame
        project_lang_frame = QFrame(self)
        project_lang_frame.setFrameShape(QFrame.Shape.StyledPanel)
        project_lang_layout = QHBoxLayout(project_lang_frame)
        project_lang_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(project_lang_frame)

        self.project_language_label = QLabel(self.get_text("select_project_language_label"))
        self.project_language_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        project_lang_layout.addWidget(self.project_language_label)

        self.project_language_combo = QComboBox(self)
        self.project_language_combo.addItems(["Python", "Node.js"])
        self.project_language_combo.setCurrentText("Python") # Set initial selection for project language

        # Connect project language combo box signal to update button text and disable create/install buttons
        self.project_language_combo.currentIndexChanged.connect(self.update_create_button_text)
        self.project_language_combo.currentIndexChanged.connect(lambda: self.create_req_button.setEnabled(False))
        self.project_language_combo.currentIndexChanged.connect(lambda: self.install_button.setEnabled(False))
        project_lang_layout.addWidget(self.project_language_combo, 1)

        # Buttons Frame
        button_frame = QFrame(self)
        button_layout = QHBoxLayout(button_frame)
        main_layout.addWidget(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.scan_button = QPushButton(self.get_text("scan_button"))
        self.scan_button.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_button)

        self.create_req_button = QPushButton(self.get_text("create_req_button"))
        self.create_req_button.clicked.connect(self.create_requirements_file)
        self.create_req_button.setEnabled(False)
        button_layout.addWidget(self.create_req_button)

        self.install_button = QPushButton(self.get_text("install_button"))
        self.install_button.clicked.connect(self.install_dependencies)
        self.install_button.setEnabled(False)
        button_layout.addWidget(self.install_button)

        self.stop_button = QPushButton(self.get_text("stop_button"))
        self.stop_button.clicked.connect(self.stop_scan)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        button_layout.addStretch(1)

        # Set initial button text based on default project language (will be called by apply_translations)
        self.update_create_button_text()

        # Results Text Area
        self.results_text = QTextEdit(self)
        self.results_text.setReadOnly(True)
        self.results_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.results_text.setFont(QFont('Courier New', 10))
        main_layout.addWidget(self.results_text)

        # Add main tab to the tab widget
        self.tab_widget.addTab(main_tab, self.get_text("main_tab_title"))

        # --- Settings Tab ---
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        settings_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # UI Language Selection Frame (Moved to settings tab)
        ui_lang_frame = QFrame(self)
        ui_lang_frame.setFrameShape(QFrame.Shape.StyledPanel)
        ui_lang_layout = QHBoxLayout(ui_lang_frame)
        ui_lang_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.addWidget(ui_lang_frame)

        self.ui_language_label = QLabel(self.get_text("select_ui_language_label"))
        self.ui_language_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ui_lang_layout.addWidget(self.ui_language_label)

        self.ui_language_combo = QComboBox(self)
        self.ui_language_combo.addItem("English", "en") # Store locale data
        self.ui_language_combo.addItem("Русский", "ru")
        
        # Set initial UI language to English
        index = self.ui_language_combo.findData("en")
        if index != -1:
            self.ui_language_combo.setCurrentIndex(index)

        self.ui_language_combo.currentIndexChanged.connect(self.change_ui_language)
        ui_lang_layout.addWidget(self.ui_language_combo, 1)

        # GitHub Profile Link Button
        github_button_layout = QHBoxLayout()
        github_button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_layout.addLayout(github_button_layout)

        self.github_button = QPushButton(self.get_text("github_link_text"))
        self.github_button.clicked.connect(self.open_github_profile)
        github_icon_path = os.path.join(script_dir, 'assets', 'github.png')
        if os.path.exists(github_icon_path):
            self.github_button.setIcon(QIcon(github_icon_path))
        else:
            logging.warning(f"GitHub icon not found at {github_icon_path}")
        
        self.github_button.setStyleSheet("""
            QPushButton {
                background-color: #333333; /* Darker background for GitHub button */
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #111111;
            }
        """)
        github_button_layout.addWidget(self.github_button)

        settings_layout.addStretch(1) # Push content to top

        # Add settings tab to the tab widget
        self.tab_widget.addTab(settings_tab, self.get_text("settings_tab_title"))

        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.update_status_bar_message(self.get_text("status_ready"))

        # --- Basic Styling with QSS (Qt Style Sheets) ---
        self.setStyleSheet("""
            QMainWindow {
                background-color: #202020;
                color: #e0e0e0;
            }
            QWidget {
                 color: #e0e0e0;
            }
            QFrame {
                border: 1px solid #404040;
                border-radius: 8px;
                background-color: #303030;
                margin: 4px;
                padding: 5px;
            }
            QLabel {
                font-weight: bold;
                color: #e0e0e0;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #5090ff;
                border-radius: 6px;
                background-color: #ffffff;
                color: #333333;
            }
             QLineEdit:focus {
                border: 1px solid #3070e0;
             }
            QPushButton {
                background-color: #5090ff;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3070e0;
            }
            QPushButton:pressed {
                background-color: #0050a0;
            }
            QPushButton:disabled {
                background-color: #606060;
                color: #b0b0b0;
            }
            QTextEdit {
                padding: 15px;
                border: 1px solid #404040;
                border-radius: 8px;
                background-color: #303030;
                color: #e0e0e0;
                selection-background-color: #5090ff;
                selection-color: white;
            }
            QStatusBar {
                background-color: #303030;
                color: #e0e0e0;
                padding: 5px;
                border-top: 1px solid #404040;
            }
            QStatusBar QLabel { /* Style for the message in status bar */
                font-weight: normal;
                color: #e0e0e0;
            }
            QComboBox {
                padding: 8px;
                border: 1px solid #5090ff;
                border-radius: 6px;
                background-color: #ffffff;
                color: #333333;
            }
            QComboBox::drop-down {
                border-left: 1px solid #5090ff;
                background-color: #5090ff;
            }
            QTabWidget::pane { /* The tab widget frame */
                border: 1px solid #404040;
                background-color: #282828;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #303030;
                color: #e0e0e0;
                padding: 10px 20px;
                border: 1px solid #404040;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #282828;
                border-color: #5090ff;
                border-bottom-color: #282828; /* make the selected tab look like it's connected to the pane */
            }
            QTabBar::tab:hover {
                background: #383838;
            }
        """)

    def update_status_bar_message(self, base_message):
        """Updates the status bar with the base message and application info."""
        full_message = f"{base_message} - Made by TroubleGy v{self.app_version}"
        self.statusBar.showMessage(full_message)

    def change_ui_language(self, index):
        """Changes the application UI language based on combo box selection."""
        new_locale = self.ui_language_combo.itemData(index)
        if new_locale and new_locale != self.current_locale:
            self.current_locale = new_locale
            logging.info(f"UI Language changed to: {self.current_locale}")
            self.apply_translations()
            # Disable create/install buttons on language change
            self.create_req_button.setEnabled(False)
            self.install_button.setEnabled(False)

    def apply_translations(self):
        """Applies the current locale's translations to UI elements."""
        self.setWindowTitle(self.get_text("window_title"))
        self.folder_label.setText(self.get_text("project_folder_label"))
        self.folder_path_entry.setPlaceholderText(self.get_text("folder_path_placeholder"))
        self.browse_button.setText(self.get_text("browse_button"))
        # Update for new project language label
        self.project_language_label.setText(self.get_text("select_project_language_label"))
        # Update UI language label (now in settings tab)
        self.ui_language_label.setText(self.get_text("select_ui_language_label"))
        self.scan_button.setText(self.get_text("scan_button"))
        self.install_button.setText(self.get_text("install_button"))
        self.stop_button.setText(self.get_text("stop_button"))
        self.update_create_button_text()
        self.update_status_bar_message(self.get_text("status_ready")) # Use new status bar update method

        # Update tab titles
        self.tab_widget.setTabText(0, self.get_text("main_tab_title"))
        self.tab_widget.setTabText(1, self.get_text("settings_tab_title"))

        # Update GitHub button text
        self.github_button.setText(self.get_text("github_link_text"))

    def open_github_profile(self):
        """Opens the GitHub profile URL in the default web browser."""
        github_url = "https://github.com/TroubleGy"
        logging.info(f"Opening GitHub profile: {github_url}")
        QDesktopServices.openUrl(QUrl(github_url))

    def browse_folder(self):
        """Opens a dialog to select a folder."""
        folder_selected = QFileDialog.getExistingDirectory(self, self.get_text("project_folder_label"))
        if folder_selected:
            self.folder_path_entry.setText(folder_selected)
            self.current_scan_folder = folder_selected
            self.update_status_bar_message(self.get_text("status_selected_folder").format(folder_path=folder_selected))

    def dragEnterEvent(self, event):
        """Handles drag enter event for folder drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handles drop event for folder drops."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    self.folder_path_entry.setText(path)
                    self.current_scan_folder = path
                    self.update_status_bar_message(self.get_text("status_selected_folder_drag_drop").format(folder_path=path))
                    event.acceptProposedAction()
                    return
            event.ignore()
        else:
            event.ignore()

    def start_scan(self):
        """Starts the dependency scanning process."""
        try:
            folder_path = self.folder_path_entry.text()
            selected_project_language = self.project_language_combo.currentText()

            if not folder_path:
                QMessageBox.warning(self, self.get_text("msg_input_error_title"), self.get_text("msg_input_error_text"))
                return

            # Clear previous results and lock UI
            self.results_text.clear()
            self.lock_ui(True)
            self.results_text.append(self.get_text("results_starting_scan") + "\n")
            self.update_status_bar_message(self.get_text("status_scan_in_progress"))
            logging.info(self.get_text("status_starting_scan").format(folder_path=folder_path, language=selected_project_language))

            # Create and setup worker thread, passing the selected project language
            self.thread = QThread()
            self.worker = DependencyScannerWorker(folder_path, selected_project_language)
            self.worker.moveToThread(self.thread)

            # Connect signals
            self.thread.started.connect(self.worker.run)
            self.worker.status_update.connect(self.update_status_text)
            self.worker.scan_finished.connect(self.handle_scan_finished)
            self.worker.error_occurred.connect(self.handle_error)
            self.worker.progress_update.connect(self.update_status_bar_message)
            self.worker.dependency_found.connect(self.live_update)

            # Cleanup connections
            self.worker.scan_finished.connect(self.thread.quit)
            self.worker.scan_finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.finished.connect(lambda: self.lock_ui(False))

            # Start the thread
            self.thread.start()
        except Exception as e:
            logging.error(f"Error in start_scan: {e}")
            self.handle_error(str(e))
            self.lock_ui(False)

    def stop_scan(self):
        """Stops the current scan operation."""
        if self.worker:
            logging.info(self.get_text("status_stopping_scan"))
            self.worker.stop()
            self.update_status_bar_message(self.get_text("status_stopping_scan")) # Use new status bar update method
            self.stop_button.setEnabled(False)

    def live_update(self, dependency):
        """Updates the UI in real-time as dependencies are found."""
        self.results_text.append(self.get_text("found_prefix") + dependency)
        self.results_text.verticalScrollBar().setValue(
            self.results_text.verticalScrollBar().maximum()
        )

    def update_status_text(self, message):
        """Appends status messages to the results text area."""
        message = message.replace("\n", "\n")
        self.results_text.append(message)
        self.results_text.verticalScrollBar().setValue(self.results_text.verticalScrollBar().maximum())

    def handle_scan_finished(self, dependencies):
        """Handles the results after the scanning thread finishes."""
        try:
            self.found_dependencies = dependencies
            # Store the project language used for the scan, not UI locale
            self.current_language = self.project_language_combo.currentText()

            self.results_text.append(self.get_text("results_scan_complete"))
            self.results_text.append(self.get_text("results_potential_dependencies"))

            if self.found_dependencies:
                sorted_dependencies = sorted(list(self.found_dependencies))
                for dep in sorted_dependencies:
                    status = "" # Default empty status
                    try:
                        # Check installed only for Python projects
                        if self.current_language == "Python" and self.worker and hasattr(self.worker, '_is_installed'):
                            status = self.get_text("installed_suffix") if self.worker._is_installed(dep) else ""
                    except Exception as e:
                        logging.error(f"Error checking if {dep} is installed: {e}")
                        status = ""
                    self.results_text.append(f"- {dep}{status}")
                
                self.create_req_button.setEnabled(True)
                if self.current_language == "Python": # Check the actual project language for Python
                    self.install_button.setEnabled(True)
                
                self.update_status_bar_message(self.get_text("status_scan_complete_found"))
            else:
                self.results_text.append(self.get_text("results_no_potential_dependencies"))
                self.update_status_bar_message(self.get_text("status_scan_complete_no_found"))

            self.results_text.append(self.get_text("results_review_note"))
            self.scan_button.setEnabled(True)
            self.update_create_button_text()
        except Exception as e:
            logging.error(f"Error in handle_scan_finished: {e}")
            self.handle_error(str(e))
        finally:
            # Ensure UI is unlocked even if there was an error
            self.lock_ui(False)
            
            # Store references to worker and thread
            worker = getattr(self, 'worker', None)
            thread = getattr(self, 'thread', None)
            
            # Clear references first
            self.worker = None
            self.thread = None
            
            # Then cleanup
            if thread and thread.isRunning():
                try:
                    thread.quit()
                    thread.wait()
                except Exception as e:
                    logging.debug(f"Error stopping thread: {e}")
                finally:
                    try:
                        thread.deleteLater()
                    except Exception as e:
                        logging.debug(f"Error deleting thread: {e}")
            
            if worker:
                try:
                    # Disconnect signals safely
                    for signal in ['status_update', 'scan_finished', 'error_occurred', 
                                 'progress_update', 'dependency_found']:
                        try:
                            if hasattr(worker, signal):
                                getattr(worker, signal).disconnect()
                        except Exception as e:
                            logging.debug(f"Error disconnecting {signal}: {e}")
                except Exception as e:
                    logging.debug(f"Error disconnecting signals: {e}")
                finally:
                    try:
                        worker.deleteLater()
                    except Exception as e:
                        logging.debug(f"Error deleting worker: {e}")

    def handle_error(self, error_message):
        """Displays error messages and updates status bar."""
        QMessageBox.critical(self, self.get_text("msg_scan_progress_title"), error_message)
        self.results_text.append(f"ERROR: {error_message}\n")
        self.scan_button.setEnabled(True)
        self.update_status_bar_message(self.get_text("status_scan_failed")) # Use new status bar update method

    def create_requirements_file(self):
        """Generates the requirements.txt file (or equivalent)."""
        if not self.found_dependencies:
            QMessageBox.information(self, self.get_text("msg_no_dependencies_title"), self.get_text("msg_no_dependencies_text"))
            return

        if not self.current_scan_folder:
             QMessageBox.warning(self, self.get_text("msg_output_error_title"), self.get_text("msg_output_error_text"))
             self.update_status_bar_message(self.get_text("status_file_creation_failed")) # Use new status bar update method
             return

        output_folder = self.current_scan_folder
        selected_project_language = self.project_language_combo.currentText()

        filename = "dependencies.txt"
        if selected_project_language == "Python":
            filename = "requirements.txt"
        elif selected_project_language == "Node.js":
            filename = "package_dependencies.txt"

        output_path = os.path.join(output_folder, filename)

        self.results_text.append(self.get_text("results_generating_file").format(filename=filename, output_path=output_path))
        status_message = self.get_text("results_generating_file").format(filename=filename, output_path="")
        self.update_status_bar_message(status_message) # Use new status bar update method

        try:
            sorted_dependencies = sorted(list(self.found_dependencies))
            with open(output_path, 'w', encoding='utf-8') as f:
                for dep in sorted_dependencies:
                    f.write(f"{dep}\n")

            self.results_text.append(self.get_text("results_file_generated").format(filename=filename))
            self.results_text.append(self.get_text("results_review_generated_file"))
            self.update_status_bar_message(self.get_text("status_file_created").format(filename=filename)) # Use new status bar update method

        except Exception as e:
            self.results_text.append(self.get_text("results_file_write_error").format(output_path=output_path, error=e))
            QMessageBox.critical(self, self.get_text("msg_file_write_error_title"), self.get_text("msg_file_write_error_text").format(error=e))
            self.update_status_bar_message(self.get_text("status_file_creation_failed")) # Use new status bar update method

    def install_dependencies(self):
        """Installs the found Python dependencies using pip."""
        if not self.found_dependencies:
            QMessageBox.information(self, self.get_text("msg_no_dependencies_title"), self.get_text("msg_no_dependencies_text"))
            return

        if self.project_language_combo.currentText() != "Python":
            QMessageBox.warning(self, self.get_text("msg_language_mismatch_title"), self.get_text("msg_language_mismatch_text"))
            return

        reply = QMessageBox.question(self, self.get_text("msg_confirm_install_title"),
                                     self.get_text("msg_confirm_install_text").format(dependencies=', '.join(sorted(list(self.found_dependencies)))),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.update_status_bar_message(self.get_text("status_installing_dependencies")) # Use new status bar update method
            self.results_text.append(self.get_text("results_install_attempt"))
            
            deps_to_install = [dep for dep in self.found_dependencies if not self.worker._is_installed(dep)]
            if not deps_to_install:
                self.results_text.append(self.get_text("results_all_deps_installed"))
                self.update_status_bar_message(self.get_text("status_all_deps_installed")) # Use new status bar update method
                return

            install_command = f"pip install {' '.join(deps_to_install)}"
            logging.info(f"Executing install command: {install_command}")
            
            try:
                import subprocess
                process = subprocess.run(install_command, shell=True, capture_output=True, text=True)

                if process.returncode == 0:
                    self.results_text.append(self.get_text("results_dependencies_installed") + "\n")
                    self.update_status_bar_message(self.get_text("status_dependencies_installed")) # Use new status bar update method
                    logging.info("Dependencies installed successfully.")
                else:
                    error_output = process.stderr or process.stdout
                    self.results_text.append(self.get_text("results_error_installing").format(error_output=error_output))
                    self.update_status_bar_message(self.get_text("status_installation_failed")) # Use new status bar update method
                    logging.error(f"Dependency installation failed: {error_output}")
            except Exception as e:
                self.results_text.append(self.get_text("results_installation_error").format(error=e))
                self.update_status_bar_message(self.get_text("status_installation_error")) # Use new status bar update method
                logging.error(f"Exception during installation: {e}")
        else:
            self.update_status_bar_message(self.get_text("status_installation_cancelled")) # Use new status bar update method
            self.results_text.append(self.get_text("results_installation_cancelled"))

    def update_create_button_text(self):
        """Updates the text of the create requirements/dependencies button based on selected language."""
        selected_language_display = self.project_language_combo.currentText()
        if selected_language_display == "Python":
            self.create_req_button.setText(self.get_text("create_req_button"))
        elif selected_language_display == "Node.js":
            self.create_req_button.setText(self.get_text("create_pkg_deps_button"))

    def closeEvent(self, event):
        """Handles application close event."""
        if self.thread and self.thread.isRunning():
            reply = QMessageBox.question(self, self.get_text("msg_scan_progress_title"),
                                         self.get_text("msg_scan_progress_text"),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                self.thread.quit()
                self.thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def lock_ui(self, locked: bool):
        """Locks or unlocks the UI during scanning."""
        try:
            self.folder_path_entry.setEnabled(not locked)
            self.browse_button.setEnabled(not locked)
            self.project_language_combo.setEnabled(not locked)
            self.ui_language_combo.setEnabled(not locked)
            self.scan_button.setEnabled(not locked)
            self.stop_button.setEnabled(locked)
            self.create_req_button.setEnabled(not locked and bool(self.found_dependencies))
            self.install_button.setEnabled(not locked if self.project_language_combo.currentText() == "Python" and self.found_dependencies else False)
            
            # Safely enable/disable tabs
            if hasattr(self, 'tab_widget'):
                self.tab_widget.setEnabled(not locked)
                self.tab_widget.setTabEnabled(1, not locked)
                self.tab_widget.setTabEnabled(0, True)
        except Exception as e:
            logging.error(f"Error in lock_ui: {e}")


# --- Main execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = DependencyScannerApp()
    main_window.show()
    sys.exit(app.exec()) 