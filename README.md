# DependencyScanner

**DependencyScanner:** Tired of manual dependency tracking? Scan code across languages! Get precise dependency files (like requirements.txt) using AST analysis. Sleek PyQt6 GUI. Future support for multiple languages planned. Simplify your workflow and build better projects faster!

---

## ✨ Features

*   **Intuitive GUI:** Easy-to-use graphical interface built with PyQt6.
*   **Accurate Dependency Detection:** Utilizes Python's Abstract Syntax Tree (AST) module for precise parsing of import statements.
*   **Python Support (v1.0.0):** Currently supports scanning Python projects to find external libraries.
*   **`requirements.txt` Generation:** Automatically creates a `requirements.txt` file listing the detected dependencies in the scanned folder.
*   **Folder Scanning:** Recursively scans all Python files within a selected directory and its subdirectories.
*   **Built-in/Standard Library Exclusion:** Intelligently filters out Python's built-in modules and most standard library components.
*   **Status Updates:** Provides feedback during the scanning process via the GUI and status bar.
*   **Cross-Platform:** Built with Python and PyQt6, it should run on Windows, macOS, and Linux.

## 🚀 Getting Started

### Requirements

*   Python 3.6 or higher
*   PyQt6 library

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/TroubleGy/DependencyScanner
    ```

2.  **Navigate to the project directory:**
    ```bash
    cd DependencyScanner
    ```
3.  **Install the required library:**
    ```bash
    pip install PyQt6
    ```

### How to Run

1.  **Make sure you are in the project directory** (where `dependency_scanner.py` is located).
2.  **Run the script:**
    ```bash
    python dependency_scanner.py
    ```
3.  The GUI application window will open.
4.  Click the "Browse" button to select the root folder of the project you want to scan.
5.  Click "Scan Dependencies". The results and scanning progress will appear in the text area.
6.  Once the scan is complete and if dependencies are found, click "Create requirements.txt" to generate the file in the scanned folder.

## Roadmap

*   **Support for More Languages:** Implement scanning logic for Node.js (`package.json`), Java (Maven `pom.xml` / Gradle `build.gradle`), Ruby (Gemfile), Go (`go.mod`), Rust (`Cargo.toml`), and more.
*   **Version Checking:** Add functionality to check for the latest versions of detected dependencies (requires integrating with package managers' APIs like PyPI, npm registry, etc.).
*   **Dependency Updates:** Potentially add features to suggest or even automate dependency updates via Pull Requests.
*   **Improved UI/UX:** Further refine the graphical interface for better usability and aesthetics.

## 👋 Contributing

Contributions are welcome! If you have ideas for new features, improvements, or bug fixes, feel free to:

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/YourFeature`).
3.  Commit your changes (`git commit -m 'Add some YourFeature'`).
4.  Push to the branch (`git push origin feature/YourFeature`).
5.  Open a Pull Request.

Let's build something awesome together!

## 🌟 Show Your Support

Give a ⭐️ if this project helped you or you like the direction it's heading!

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/TroubleGy/DependencyScanner/blob/main/LICENCE) file for details.
