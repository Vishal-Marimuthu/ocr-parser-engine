# OCR Parser Engine

An intelligent document OCR (Optical Character Recognition) parsing engine with a modern web interface. This project combines FastAPI backend with React frontend to extract and parse document information automatically.

## 🚀 Features

- **Document OCR**: Automatically extract text from images using Tesseract OCR
- **Intelligent Parsing**: Extract structured data like invoice numbers, dates, and amounts
- **REST API**: FastAPI-based backend with CORS support
- **Modern UI**: React + Vite frontend with Tailwind CSS styling
- **File Upload**: Support for image file uploads and processing

## 📋 Project Structure

```
ocr-parser-engine/
├── backend/                 # FastAPI OCR engine
│   ├── main.py             # Main application entry point
│   ├── generate_sample.py   # Sample data generation
│   └── requirements.txt     # Python dependencies
├── frontend/               # React web application
│   ├── src/               # React components
│   ├── public/            # Static files
│   ├── package.json       # Node dependencies
│   ├── vite.config.js     # Vite configuration
│   ├── eslint.config.js   # ESLint configuration
│   └── README.md          # Frontend documentation
└── README.md              # This file
```

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Tesseract OCR** - Optical character recognition engine
- **OpenCV** - Image processing
- **Python 3.x**

### Frontend
- **React 19** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Node.js/npm** - Package management

## 📦 Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- Tesseract OCR engine installed on your system

### Install Tesseract OCR

**Windows:**
```bash
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Or use Chocolatey
choco install tesseract
```

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## 🔧 Development

### Backend Development
```bash
cd backend
uvicorn main:app --reload
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Building Frontend for Production
```bash
cd frontend
npm run build
```

### Linting
```bash
cd frontend
npm run lint
```

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🎯 Key Features Explained

### Document Parsing
The backend intelligently extracts:
- **Invoice Numbers**: Using regex patterns to identify invoice IDs
- **Dates**: Recognizing various date formats
- **Amounts**: Extracting monetary values in different currencies

### Resilient Configuration
The application includes resilient Tesseract path detection for multiple installation locations:
- Program Files (standard installation)
- Program Files (x86)
- User AppData directory

## 🚀 Deployment

For production deployment, ensure:
1. Install Tesseract OCR on your server
2. Set appropriate environment variables
3. Configure CORS origins based on your frontend URL
4. Use a production ASGI server (e.g., Gunicorn)

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions or issues, please open an issue on the GitHub repository.

---

**Made with ❤️ for intelligent document processing**
