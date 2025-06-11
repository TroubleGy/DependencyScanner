# 🚀 Dependency Scanner

**Modern cross-language dependency scanner with a sleek PyQt6 interface.**  
Quickly analyze Python and Node.js projects for external dependencies. Supports `requirements.txt`, `pyproject.toml`, `package.json`, AST imports, dynamic modules, and more.

> **Version:** 1.1  
> **Author:** [TroubleGy](https://github.com/TroubleGy)  
> **License:** MIT  
> **Supported Project Types:** Python, Node.js  
> **UI Languages:** English 🇬🇧, Russian 🇷🇺

---

## ✨ Features

- 🖥️ **User-Friendly GUI** built with PyQt6  
- 🔍 **Deep Code Analysis**
  - Parses static imports (`ast`)
  - Detects dynamic imports (`importlib`)
  - Scans `requirements.txt`, `pyproject.toml`, `package.json`
  - Supports `.py`, `.js`, `.ts`, `.tsx` files
- 📄 **Generates dependency files**
  - `requirements.txt` for Python
  - `package_dependencies.txt` for Node.js
- ⚡ **Install dependencies directly** (Python only)
- 🧠 **Excludes** standard library & built-in modules
- ♻️ **Live updates** while scanning
- 🖱️ **Drag & Drop** folders into the interface
- 🌍 **Multilingual UI**: English / Russian switch
- 🧩 **Tabbed layout** for main and settings
- 📝 **Generates scanner.log** file automatically
- 🔁 Threaded scanning with stable QThread backend

---

## 📦 Dependencies

To run this project, you need the following Python packages:

- PyQt6  
- stdlib_list  
- toml  

You can install them manually or using the included `requirements.txt`.

---

## 🖥️ How to Run
```bash
git clone https://github.com/TroubleGy/DependencyScanner  
cd DependencyScanner  
python dependency_scanner.py
```
---

## 🧪 Usage

- Launch the application  
- Click **Browse** or **Drag & Drop** a folder  
- Select the language: **Python** or **Node.js**  
- Click **Scan Dependencies**  
- View results live during scan  
- Click **Create requirements.txt** (or `package_dependencies.txt`)  
- *(Python only)* Click **Install Dependencies** to install using pip

---

## 📁 Project Structure

DependencyScanner/  
├── dependency_scanner.py          — Main application  
├── assets/  
│   ├── icon.png                   — Window icon  
│   ├── github.png                — GitHub button icon  
│   └── translations.json         — UI text translations (EN/RU)  
├── requirements.txt              — Required Python libraries  
├── scanner.log                   — Log file created during usage  
└── README.md

---

## 📘 Roadmap

- ✅ Node.js support (package.json and JS/TS analysis)
- 🧩 Future support: Go, Java (Maven), Rust, Ruby
- 🔍 Dependency version checking (PyPI / NPM)
- ⚙️ Auto-suggestions for outdated libraries
- 🤖 AI-powered security/license detection
- 🐳 Docker version
- 📤 Export scanned results to HTML / Markdown
- 🖥️ Optional command-line (CLI) interface

---

## 🎯 Why Use Dependency Scanner?

| Feature                                        | Manual  | Dependency Scanner  |
|------------------------------------------------|---------|---------------------|
| Detect `.py`, `.js`, `.ts`, `.json`, `.toml`   |   ❌     |       ✅          |
| Skip built-ins and stdlib                      |   ❌     |       ✅          |
| Generate proper dependency files               |   ⚠️     |       ✅          |
| Drag & Drop GUI                                |   ❌     |       ✅          |
| Install Python packages automatically          |   ❌     |       ✅          |
| Localized UI (EN / RU)                         |   ❌     |       ✅          |

---

## 🔥 Development Mode
```bash
pip install -r requirements.txt  
python dependency_scanner.py
```

---

## 🔐 License

MIT License  
See the LICENSE file for full details.

---

## 👤 Author

**TroubleGy**  
GitHub — https://github.com/TroubleGy

> Built with ❤️, PyQt6, and sleepless nights 😎

---

## 🌟 Support This Project

If this project helped you — give it a ⭐️ on GitHub!  
You’re also welcome to share it or contribute 🙌

---
