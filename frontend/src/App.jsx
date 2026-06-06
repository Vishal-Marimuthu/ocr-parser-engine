import React, { useState, useRef } from 'react';

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [toonData, setToonData] = useState(null);
  const [error, setError] = useState(null);
  
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = (selectedFile) => {
    if (!selectedFile.type.startsWith('image/')) {
      setError('Please upload an image file.');
      return;
    }
    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setToonData(null);
    setError(null);
  };

  const handleSubmit = async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/extract`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const textData = await response.text();
      setToonData(textData);
    } catch (err) {
      setError(err.message || 'An error occurred during OCR processing.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        <header className="mb-10 text-center">
          <h1 className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent mb-4">
            Intelligent Document OCR
          </h1>
          <p className="text-slate-400 text-lg">
            Upload an invoice or receipt to extract structured data using AI & Computer Vision.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Upload Section */}
          <div className="bg-slate-800 rounded-2xl p-6 shadow-xl border border-slate-700">
            <h2 className="text-2xl font-semibold mb-4 text-white">Upload Document</h2>
            
            <div 
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current.click()}
              className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-300 flex flex-col items-center justify-center min-h-[300px]
                ${preview ? 'border-purple-500 bg-slate-800/50' : 'border-slate-600 hover:border-blue-400 hover:bg-slate-800/80'}`}
            >
              <input 
                type="file" 
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="image/*"
                className="hidden"
              />
              
              {preview ? (
                <div className="relative w-full h-full flex flex-col items-center">
                  <img src={preview} alt="Document Preview" className="max-h-64 object-contain mb-4 rounded shadow-lg" />
                  <p className="text-sm text-slate-400">Click or drag to change image</p>
                </div>
              ) : (
                <>
                  <div className="w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mb-4">
                    <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-slate-200">Drag & drop your document here</p>
                  <p className="text-sm text-slate-500 mt-2">Supports JPG, PNG</p>
                </>
              )}
            </div>

            <div className="mt-6 flex flex-col sm:flex-row gap-4 items-center justify-between">
              <button 
                onClick={handleSubmit}
                disabled={!file || isLoading}
                className={`w-full sm:w-auto px-8 py-3 rounded-lg font-bold text-white transition-all duration-300 shadow-lg
                  ${!file || isLoading 
                    ? 'bg-slate-700 cursor-not-allowed opacity-70' 
                    : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-400 hover:to-purple-500 hover:shadow-purple-500/25 hover:-translate-y-0.5'}`}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing...
                  </span>
                ) : 'Extract Data'}
              </button>

              <a 
                href="/sample_invoice.png" 
                download
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors underline"
              >
                Download Sample Invoice
              </a>
            </div>

            {error && (
              <div className="mt-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}
          </div>

          {/* Results Section */}
          <div className="bg-slate-800 rounded-2xl p-6 shadow-xl border border-slate-700 flex flex-col">
            <h2 className="text-2xl font-semibold mb-4 text-white flex items-center">
              Extraction Results
              {toonData && <span className="ml-3 px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full uppercase tracking-wider">Success</span>}
            </h2>
            
            <div className="flex-grow bg-slate-950 rounded-xl border border-slate-700 p-4 overflow-hidden flex flex-col relative min-h-[300px]">
              {toonData ? (
                <>
                  <div className="flex justify-between items-center mb-3 border-b border-slate-800 pb-2">
                    <span className="text-xs text-slate-500 font-mono">Format: text/toon</span>
                    <button 
                      onClick={() => navigator.clipboard.writeText(toonData)}
                      className="text-xs text-slate-400 hover:text-white transition-colors flex items-center"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                      Copy
                    </button>
                  </div>
                  <pre className="text-green-400 font-mono text-sm overflow-auto whitespace-pre-wrap flex-grow custom-scrollbar">
                    {toonData}
                  </pre>
                </>
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-slate-600">
                  <svg className="w-12 h-12 mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p>Results will appear here in TOON format</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
