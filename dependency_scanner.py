# dependency_scanner.py

import os
import sys
import ast # Import the Abstract Syntax Tree module
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QFileDialog, QMessageBox, QFrame, QSizePolicy,
                             QStatusBar) # Import QStatusBar for status messages
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QDir, Qt # Import Qt for alignment
from PyQt6.QtGui import QColor, QPalette, QFont # Import QFont for styling text

# --- Worker Thread for Scanning ---
class DependencyScannerWorker(QObject):
    # Signals to communicate with the main GUI thread
    status_update = pyqtSignal(str)
    scan_finished = pyqtSignal(set)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str) # Signal for status bar updates

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self._is_running = True # Flag to potentially stop the scan

    def run(self):
        """Main function for the worker thread."""
        self.status_update.emit(f"Starting scan in folder: {self.folder_path}")
        self.progress_update.emit("Scanning...") # Update status bar
        potential_dependencies = set()

        if not os.path.isdir(self.folder_path):
            self.error_occurred.emit(f"Error: Folder not found at '{self.folder_path}'")
            self.scan_finished.emit(potential_dependencies) # Finish even on error
            self.progress_update.emit("Scan failed.") # Update status bar
            return

        # Get list of built-in modules (reliable)
        built_in_modules = set(sys.builtin_module_names)

        # Add common standard library modules.
        standard_library_modules = {
            "os", "sys", "re", "json", "math", "random", "datetime", "collections",
            "io", "functools", "itertools", "logging", "threading", "multiprocessing",
            "subprocess", "unittest", "pytest", "csv", "json", "xml", "html", "urllib",
            "http", "socket", "email", "sqlite3", "platform", "shutil", "glob", "time",
            "argparse", "configparser", "abc", "asyncio", "base64", "calendar", "cmath",
            "contextlib", "dataclasses", "decimal", "difflib", "filecmp", "ftplib",
            "heapq", "hmac", "imghdr", "inspect", "ipaddress", "locale", "msvcrt",
            "netrc", "nntplib", "optparse", "pathlib", "pprint", "profile", "pstats",
            "queue", "reprlib", "rlcompleter", "sched", "secrets", "signal", "smtplib",
            "sndhdr", "ssl", "stat", "statistics", "string", "tabnanny", "tarfile",
            "telnetlib", "tempfile", "textwrap", "timeit", "trace", "traceback",
            "turtledemo", "types", "typing", "uuid", "warnings", "wave", "weakref",
            "webbrowser", "wsgiref", "zipapp", "zipfile", "zlib"
        }

        # Combine built-ins and standard library for exclusion
        excluded_modules = built_in_modules.union(standard_library_modules)

        for root, _, files in os.walk(self.folder_path):
            if not self._is_running: # Check if scanning should be stopped
                break
            for file in files:
                if not self._is_running: # Check again
                    break
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self.status_update.emit(f"  Parsing: {file_path}")
                    self.progress_update.emit(f"Parsing: {file}") # Update status bar
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Use AST to parse the code
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    # The name is the full imported name, e.g., 'PyQt6.QtWidgets'
                                    # We only need the top-level package name
                                    package_name = alias.name.split('.')[0]
                                    # Basic check if the name looks like a valid package name
                                    # and is not in excluded list.
                                    if package_name and package_name.isidentifier() and package_name not in excluded_modules:
                                        potential_dependencies.add(package_name)
                            elif isinstance(node, ast.ImportFrom):
                                # The module is the name from the 'from ...' part, e.g., 'PyQt6.QtCore'
                                # We only need the top-level package name
                                if node.module:
                                    package_name = node.module.split('.')[0]
                                    # Basic check if the name looks like a valid package name
                                    # and is not in excluded list.
                                    if package_name and package_name.isidentifier() and package_name not in excluded_modules:
                                        potential_dependencies.add(package_name)

                    except SyntaxError as e:
                        self.status_update.emit(f"Could not parse file (Syntax Error) {file_path}: {e}")
                        self.progress_update.emit(f"Error in {file}") # Update status bar
                    except Exception as e:
                        self.status_update.emit(f"Could not read/process file {file_path}: {e}")
                        self.progress_update.emit(f"Error in {file}") # Update status bar

        self.scan_finished.emit(potential_dependencies) # Emit results when done
        self.progress_update.emit("Scan complete.") # Update status bar

    def stop(self):
        """Method to stop the scanner gracefully."""
        self._is_running = False
        self.progress_update.emit("Scan interrupted.") # Update status bar


# --- Main Application Window ---
class DependencyScannerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.found_dependencies = set() # To store dependencies after scanning
        self.worker = None # To hold the worker thread object
        self.thread = None # To hold the QThread object
        self.current_scan_folder = None # Store the folder being scanned

        self.init_ui()

    def init_ui(self):
        """Sets up the user interface."""
        self.setWindowTitle("Dependency Scanner") # Changed title
        self.setGeometry(100, 100, 700, 550) # x, y, width, height

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15) # Increased margin

        # --- Input Frame ---
        input_frame = QFrame(self)
        input_frame.setFrameShape(QFrame.Shape.StyledPanel)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10) # Add margin inside frame
        main_layout.addWidget(input_frame)

        self.folder_label = QLabel("Project Folder:")
        self.folder_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter) # Align right
        input_layout.addWidget(self.folder_label)

        self.folder_path_entry = QLineEdit(self)
        self.folder_path_entry.setPlaceholderText("Select a folder to scan...")
        input_layout.addWidget(self.folder_path_entry, 1) # Give stretch factor

        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.browse_folder) # Connect the signal!
        input_layout.addWidget(self.browse_button)

        # --- Buttons Frame ---
        button_frame = QFrame(self)
        button_layout = QHBoxLayout(button_frame)
        main_layout.addWidget(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0) # Remove margins

        self.scan_button = QPushButton("Scan Dependencies", self)
        self.scan_button.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_button)

        self.create_req_button = QPushButton("Create requirements.txt", self)
        self.create_req_button.clicked.connect(self.create_requirements_file)
        self.create_req_button.setEnabled(False) # Disabled by default
        button_layout.addWidget(self.create_req_button)

        # Add a stretch to push buttons to the left
        button_layout.addStretch(1)


        # --- Results Text Area ---
        self.results_text = QTextEdit(self)
        self.results_text.setReadOnly(True) # Make it read-only
        self.results_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) # Expand to fill space
        self.results_text.setFont(QFont('Courier New', 10))
        main_layout.addWidget(self.results_text)

        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # --- Basic Styling with QSS (Qt Style Sheets) ---
        # Further refined styles for better contrast and spacing
        self.setStyleSheet("""
            QMainWindow {
                background-color: #202020; /* Even darker background */
                color: #e0e0e0; /* Lighter text */
            }
            QWidget {
                 color: #e0e0e0; /* Default text color */
            }
            QFrame {
                border: 1px solid #404040; /* Visible border for frames */
                border-radius: 8px; /* Increased border radius */
                background-color: #303030; /* Darker gray for frames */
                margin: 4px; /* Add more margin around frames */
                padding: 5px; /* Add padding inside frames */
            }
            QLabel {
                font-weight: bold;
                color: #e0e0e0; /* Explicitly set label color */
            }
            QLineEdit {
                padding: 8px; /* Increased padding */
                border: 1px solid #5090ff; /* Brighter blue border */
                border-radius: 6px; /* Increased border radius */
                background-color: #ffffff; /* White background for input */
                color: #333333; /* Dark text for input */
            }
             QLineEdit:focus {
                border: 1px solid #3070e0; /* Darker blue when focused */
             }
            QPushButton {
                background-color: #5090ff; /* Brighter blue button */
                color: white;
                padding: 10px 20px; /* Increased padding */
                border: none;
                border-radius: 6px;
                font-weight: bold;
                min-width: 100px; /* Minimum button width */
            }
            QPushButton:hover {
                background-color: #3070e0; /* Darker blue on hover */
            }
            QPushButton:pressed {
                background-color: #0050a0; /* Even darker when pressed */
            }
            QPushButton:disabled {
                background-color: #606060; /* Grey when disabled */
                color: #b0b0b0;
            }
            QTextEdit {
                padding: 15px; /* Increased padding */
                border: 1px solid #404040;
                border-radius: 8px;
                background-color: #303030;
                color: #e0e0e0;
                selection-background-color: #5090ff; /* Blue selection */
                selection-color: white;
            }
            QStatusBar {
                background-color: #303030;
                color: #e0e0e0;
                padding: 5px; /* Increased padding */
                border-top: 1px solid #404040;
            }
            QStatusBar QLabel { /* Style for the message in status bar */
                font-weight: normal;
                color: #e0e0e0;
            }
        """)


    def browse_folder(self):
        """Opens a dialog to select a folder."""
        folder_selected = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if folder_selected:
            self.folder_path_entry.setText(folder_selected)
            self.current_scan_folder = folder_selected # Store selected folder
            self.statusBar.showMessage(f"Selected folder: {folder_selected}")


    def start_scan(self):
        """Starts the dependency scanning process in a separate thread."""
        folder_path = self.folder_path_entry.text()

        if not folder_path:
            QMessageBox.warning(self, "Input Error", "Please select a folder to scan.")
            return

        # Clear previous results and disable buttons
        self.results_text.clear()
        self.scan_button.setEnabled(False)
        self.create_req_button.setEnabled(False)
        self.results_text.append("Starting scan...\n")
        self.statusBar.showMessage("Scan in progress...") # Update status bar


        # Create a QThread and Worker
        self.thread = QThread()
        self.worker = DependencyScannerWorker(folder_path)

        # Move worker to the thread
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.status_update.connect(self.update_status_text)
        self.worker.scan_finished.connect(self.handle_scan_finished)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.progress_update.connect(self.statusBar.showMessage) # Connect worker progress to status bar


        # Clean up after thread finishes
        self.worker.scan_finished.connect(self.thread.quit)
        self.worker.scan_finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)


        # Start the thread
        self.thread.start()


    def update_status_text(self, message):
        """Appends status messages to the results text area."""
        self.results_text.append(message)
        # Auto-scroll to the bottom
        self.results_text.verticalScrollBar().setValue(self.results_text.verticalScrollBar().maximum())


    def handle_scan_finished(self, dependencies):
        """Handles the results after the scanning thread finishes."""
        self.found_dependencies = dependencies # Store the found dependencies

        self.results_text.append("\nScan complete.\n")
        self.results_text.append("Potential external dependencies found (excluding most built-ins/stdlib):")

        if self.found_dependencies:
            sorted_dependencies = sorted(list(self.found_dependencies))
            for dep in sorted_dependencies:
                self.results_text.append(f"- {dep}")
            self.create_req_button.setEnabled(True) # Enable create button
            self.statusBar.showMessage("Scan complete. Dependencies found.") # Update status bar
        else:
            self.results_text.append("No potential external dependencies found based on import statements.")
            self.statusBar.showMessage("Scan complete. No external dependencies found.") # Update status bar


        self.results_text.append("\nReview the list carefully! It might not be exhaustive or could include false positives depending on code structure.\n")

        # Re-enable scan button
        self.scan_button.setEnabled(True)


    def handle_error(self, error_message):
        """Displays error messages and updates status bar."""
        QMessageBox.critical(self, "Scan Error", error_message)
        self.results_text.append(f"ERROR: {error_message}\n")
        self.scan_button.setEnabled(True) # Ensure scan button is re-enabled
        self.statusBar.showMessage("Scan error.") # Update status bar


    def create_requirements_file(self):
        """Generates the requirements.txt file."""
        if not self.found_dependencies:
            QMessageBox.showinfo(self, "No Dependencies", "No dependencies found to write to requirements.txt.")
            return

        # Default output path is within the scanned folder
        # NOTE: The requirements.txt file will be created in the folder you SELECTED for scanning.
        # If you scanned C:/Users/user/Desktop/GithubProjects, it will be created there.
        # If you scanned C:/Users/user/Desktop/GithubProjects/RequirementsCreator, it will be created there.
        if not self.current_scan_folder:
             QMessageBox.warning(self, "Output Error", "Cannot determine scan folder path.")
             self.statusBar.showMessage("File creation failed: Cannot determine scan folder.")
             return

        output_folder = self.current_scan_folder
        filename = "requirements.txt"
        output_path = os.path.join(output_folder, filename)


        self.results_text.append(f"\nGenerating requirements.txt at: {output_path}...")
        self.statusBar.showMessage("Generating requirements.txt...") # Update status bar

        try:
            sorted_dependencies = sorted(list(self.found_dependencies))
            with open(output_path, 'w', encoding='utf-8') as f:
                for dep in sorted_dependencies:
                    f.write(f"{dep}\n")

            self.results_text.append("Requirements file generated successfully.")
            self.results_text.append("Note: Review the generated file.")
            self.statusBar.showMessage("requirements.txt created.") # Update status bar

        except Exception as e:
            self.results_text.append(f"Could not write requirements file {output_path}: {e}")
            QMessageBox.critical(self, "File Write Error", f"Could not write requirements file: {e}")
            self.statusBar.showMessage("File creation failed.") # Update status bar


    def closeEvent(self, event):
        """Handles application close event."""
        if self.thread and self.thread.isRunning():
            reply = QMessageBox.question(self, 'Scanning in Progress',
                                         'Scanning is still in progress. Do you want to stop and exit?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop() # Request the worker to stop
                self.thread.quit()
                self.thread.wait() # Wait for the thread to finish
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# --- Main execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = DependencyScannerApp()
    main_window.show()
    sys.exit(app.exec()) 