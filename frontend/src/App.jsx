import React, { useState, useRef, useEffect } from 'react';

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [viewMode, setViewMode] = useState('structured');
  const [error, setError] = useState(null);
  
  const fileInputRef = useRef(null);

  // Clipboard Paste Handler
  useEffect(() => {
    const handlePaste = (e) => {
      const items = e.clipboardData?.items;
      if (items) {
        for (let i = 0; i < items.length; i++) {
          if (items[i].type.indexOf('image') !== -1) {
            const blob = items[i].getAsFile();
            // Create a pseudo file from the clipboard blob
            const pastedFile = new File([blob], `clipboard_image_${Date.now()}.png`, { type: blob.type });
            processFile(pastedFile);
            break;
          }
        }
      }
    };
    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, []);

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
    if (!selectedFile.type.startsWith('image/') && selectedFile.type !== 'application/pdf') {
      setError('Please upload an image or a PDF file.');
      return;
    }
    setFile(selectedFile);
    if (selectedFile.type.startsWith('image/')) {
      setPreview(URL.createObjectURL(selectedFile));
    } else {
      setPreview(null);
    }
    setExtractedData(null);
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

      const data = await response.json();
      setExtractedData(data);
    } catch (err) {
      setError(err.message || 'An error occurred during OCR processing.');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        <header className="mb-10 text-center">
          <h1 className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent mb-4">
            Intelligent Document OCR
          </h1>
          <p className="text-slate-400 text-lg">
            Upload an invoice or receipt (Image or PDF) to extract structured data.
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
                ${file ? 'border-purple-500 bg-slate-800/50' : 'border-slate-600 hover:border-blue-400 hover:bg-slate-800/80'}`}
            >
              <input 
                type="file" 
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="image/*,application/pdf"
                className="hidden"
              />
              
              {file && file.type === 'application/pdf' ? (
                <div className="relative w-full h-full flex flex-col items-center justify-center p-4">
                  <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center text-red-400 mb-3 border border-red-500/20">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <p className="text-lg font-semibold text-slate-200 truncate max-w-xs">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB • PDF Document</p>
                  <p className="text-xs text-slate-400 mt-4">Click, drag, or paste another file to change</p>
                </div>
              ) : preview ? (
                <div className="relative w-full h-full flex flex-col items-center">
                  <img src={preview} alt="Document Preview" className="max-h-64 object-contain mb-4 rounded shadow-lg" />
                  <p className="text-sm text-slate-400">Click, drag, or press Ctrl+V to change image</p>
                </div>
              ) : (
                <>
                  <div className="w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mb-4">
                    <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-slate-200">Drag & drop your document here</p>
                  <p className="text-sm text-slate-400 mt-1">Or press **Ctrl+V** to paste copied images</p>
                  <p className="text-xs text-slate-500 mt-2">Supports JPG, PNG, PDF</p>
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
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-semibold text-white flex items-center">
                Extraction Results
                {extractedData && <span className="ml-3 px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full uppercase tracking-wider">Success</span>}
              </h2>
              {extractedData && (
                <div className="flex bg-slate-900 rounded-lg p-1 border border-slate-700 text-sm">
                  <button
                    onClick={() => setViewMode('structured')}
                    className={`px-3 py-1.5 rounded-md transition-all ${viewMode === 'structured' ? 'bg-blue-500 text-white font-medium' : 'text-slate-400 hover:text-white'}`}
                  >
                    Structured
                  </button>
                  <button
                    onClick={() => setViewMode('json')}
                    className={`px-3 py-1.5 rounded-md transition-all ${viewMode === 'json' ? 'bg-blue-500 text-white font-medium' : 'text-slate-400 hover:text-white'}`}
                  >
                    Raw JSON
                  </button>
                </div>
              )}
            </div>
            
            <div className="flex-grow bg-slate-950 rounded-xl border border-slate-700 p-6 overflow-hidden flex flex-col relative min-h-[300px]">
              {extractedData ? (
                viewMode === 'structured' ? (
                  <div className="space-y-6 overflow-y-auto max-h-[450px] custom-scrollbar pr-1">
                    {/* Invoice Number Card */}
                    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex items-center justify-between hover:border-slate-700 transition-all">
                      <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Invoice Number</p>
                          <p className="text-lg font-bold text-white mt-0.5">{extractedData.invoice_number}</p>
                        </div>
                      </div>
                      <button 
                        onClick={() => copyToClipboard(extractedData.invoice_number)}
                        className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all"
                        title="Copy Invoice Number"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                      </button>
                    </div>

                    {/* Date Card */}
                    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex items-center justify-between hover:border-slate-700 transition-all">
                      <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Date</p>
                          <p className="text-lg font-bold text-white mt-0.5">{extractedData.date}</p>
                        </div>
                      </div>
                      <button 
                        onClick={() => copyToClipboard(extractedData.date)}
                        className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all"
                        title="Copy Date"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                      </button>
                    </div>

                    {/* Amount Card */}
                    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex items-center justify-between hover:border-slate-700 transition-all">
                      <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Total Amount</p>
                          <p className="text-xl font-extrabold text-emerald-400 mt-0.5">{extractedData.total_amount !== "N/A" && !extractedData.total_amount.startsWith('$') ? `$${extractedData.total_amount}` : extractedData.total_amount}</p>
                        </div>
                      </div>
                      <button 
                        onClick={() => copyToClipboard(extractedData.total_amount)}
                        className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all"
                        title="Copy Total Amount"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                      </button>
                    </div>

                    {/* Full Extracted Text */}
                    <div className="bg-slate-900/30 border border-slate-800 rounded-xl p-4 flex flex-col space-y-2">
                      <div className="flex justify-between items-center">
                        <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Full Extracted Text</p>
                        <button 
                          onClick={() => copyToClipboard(extractedData.raw_text)}
                          className="text-xs text-slate-400 hover:text-white flex items-center transition-colors"
                        >
                          <svg className="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                          Copy raw text
                        </button>
                      </div>
                      <p className="text-sm text-slate-300 font-mono bg-slate-950/50 p-3 rounded-lg border border-slate-900 whitespace-pre-wrap max-h-64 overflow-y-auto custom-scrollbar">
                        {extractedData.raw_text}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col h-full">
                    <div className="flex justify-between items-center mb-3 border-b border-slate-800 pb-2">
                      <span className="text-xs text-slate-500 font-mono">Format: application/json</span>
                      <button 
                        onClick={() => copyToClipboard(JSON.stringify(extractedData, null, 2))}
                        className="text-xs text-slate-400 hover:text-white transition-colors flex items-center"
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                        Copy JSON
                      </button>
                    </div>
                    <pre className="text-blue-400 font-mono text-sm overflow-auto whitespace-pre-wrap flex-grow custom-scrollbar">
                      {JSON.stringify(extractedData, null, 2)}
                    </pre>
                  </div>
                )
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-slate-600">
                  <svg className="w-12 h-12 mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p>Results will appear here in structured format</p>
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
