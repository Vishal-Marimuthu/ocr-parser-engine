import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, FileText, Moon, Sun, UploadCloud } from 'lucide-react';

const fieldLabels = {
  vendor_name: 'Vendor name',
  invoice_number: 'Invoice number',
  date: 'Date',
  total_amount: 'Invoice-declared total',
  expense_category: 'Expense category',
  taxable_amount: 'Taxable value (after discounts)',
  discount_amount: 'Discount (informational)',
  additional_charges: 'Additional charges',
};

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
  const fileInputRef = useRef(null);

  const processFile = useCallback((selectedFile) => {
    if (!selectedFile.type.startsWith('image/') && selectedFile.type !== 'application/pdf') {
      setError('Please upload an image or a PDF file.');
      return;
    }

    setFile(selectedFile);
    setPreview(selectedFile.type.startsWith('image/') ? URL.createObjectURL(selectedFile) : null);
    setResponse(null);
    setError(null);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    const handlePaste = (event) => {
      const image = Array.from(event.clipboardData?.items || [])
        .find((item) => item.type.startsWith('image/'))
        ?.getAsFile();
      if (image) {
        processFile(new File([image], `clipboard_image_${Date.now()}.png`, { type: image.type }));
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [processFile]);

  const handleSubmit = async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);
    setResponse(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/extract`, {
        method: 'POST',
        body: formData,
      });
      const result = await res.json();

      if (!res.ok) {
        const detail = result.detail;
        throw new Error(
          typeof detail === 'string'
            ? detail
            : detail?.message || `Server responded with ${res.status}`,
        );
      }

      setResponse(result);
    } catch (err) {
      setError(err.message || 'An error occurred during document processing.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-primary text-primary font-sans transition-colors duration-300">
      <div className="max-w-7xl mx-auto p-4 sm:p-8">
        <header className="flex justify-between items-center mb-8 pb-4 border-b border-themed">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-accent rounded-lg flex items-center justify-center text-white">
              <FileText className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">
              OpticForge <span className="text-accent font-black">AI</span>
            </h1>
          </div>
          <button
            onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
            className="p-2 rounded-full bg-secondary hover:bg-tertiary transition-colors border border-themed text-secondary"
            title="Toggle theme"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </header>

        <main className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <section className="lg:col-span-4 bg-secondary rounded-2xl p-6 border border-themed shadow-sm">
            <h2 className="text-lg font-semibold mb-4 text-primary">Upload document</h2>
            <div
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                if (event.dataTransfer.files[0]) processFile(event.dataTransfer.files[0]);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed border-themed rounded-xl p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[250px] ${
                file ? 'bg-tertiary border-accent' : 'hover:border-accent hover:bg-tertiary'
              }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={(event) => {
                  if (event.target.files?.[0]) processFile(event.target.files[0]);
                }}
                accept="image/*,application/pdf"
                className="hidden"
              />
              {file && file.type === 'application/pdf' ? (
                <div className="flex flex-col items-center">
                  <FileText className="w-12 h-12 text-accent mb-3" />
                  <p className="font-semibold truncate max-w-[200px] text-primary">{file.name}</p>
                  <p className="text-xs text-secondary mt-1">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB · PDF
                  </p>
                </div>
              ) : preview ? (
                <img src={preview} alt="Document preview" className="max-h-48 object-contain rounded shadow-sm" />
              ) : (
                <>
                  <UploadCloud className="w-10 h-10 text-secondary mb-3" />
                  <p className="font-medium text-primary">Click or drag a document</p>
                  <p className="text-xs text-secondary mt-2">Images or PDFs. You can also paste (Ctrl+V).</p>
                </>
              )}
            </div>

            <button
              onClick={handleSubmit}
              disabled={!file || isLoading}
              className={`w-full mt-6 py-3 rounded-lg font-bold text-white transition-all shadow ${
                !file || isLoading
                  ? 'bg-tertiary text-secondary cursor-not-allowed'
                  : 'bg-accent hover-bg-accent hover:-translate-y-0.5'
              }`}
            >
              {isLoading ? 'Extracting text and details…' : 'Extract text and details'}
            </button>

            {error && (
              <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg text-red-500 text-sm flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </section>

          <section className="lg:col-span-8 bg-secondary rounded-2xl p-6 border border-themed shadow-sm">
            {!response ? (
              <div className="min-h-[250px] flex flex-col items-center justify-center text-secondary text-center">
                <FileText className="w-12 h-12 mb-3 opacity-20" />
                <p className="text-lg font-medium">Your results will appear here</p>
                <p className="text-sm mt-1">Upload a document to extract its text and key details.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-6">
                <div>
                  <h2 className="text-xl font-bold text-primary">Extracted details</h2>
                  <p className="text-sm text-secondary mt-1">
                    Extracted invoice fields with OCR-based tax and total checks.
                  </p>
                  <p className="text-xs text-secondary mt-1">
                    Extraction method: {response.extraction_method === 'ocr_fallback'
                      ? 'Local OCR fallback'
                      : 'AI with OCR financial checks'}
                  </p>
                </div>

                {response.extraction_warnings.length > 0 && (
                  <ul className="space-y-1 text-sm text-yellow-600 dark:text-yellow-400 list-disc list-inside">
                    {response.extraction_warnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                )}

                {response.extraction_method === 'ocr_fallback' && (
                  <p className="text-sm text-secondary">
                    The AI service did not return usable results. The app used readable invoice
                    labels as a backup, so any field not recognized may need you to check the
                    document and OCR text below.
                  </p>
                )}

                {response.invoices?.length ? (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-primary">Invoice results by page</h3>
                    <p className="text-sm text-secondary">
                      Each page is checked separately. Printed amounts are preserved; calculations
                      are shown alongside them for verification.
                    </p>
                    {response.invoices.map((invoice, index) => (
                      <InvoiceResultCard key={`${invoice.page_number}-${index}`} invoice={invoice} index={index} />
                    ))}
                  </div>
                ) : (
                  <>
                    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {Object.entries(fieldLabels).map(([key, label]) => (
                        <div key={key} className="bg-primary border border-themed rounded-xl p-4">
                          <dt className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">
                            {label}
                          </dt>
                          <dd className="text-lg font-semibold text-primary break-words">
                            {response.data[key] && response.data[key] !== 'N/A'
                              ? response.data[key]
                              : 'Not found in readable text'}
                          </dd>
                        </div>
                      ))}
                    </dl>
                    <TaxCheckSection gstCheck={response.gst_check} />
                  </>
                )}

                <div>
                  <h3 className="text-lg font-semibold text-primary mb-2">Full extracted text</h3>
                  <textarea
                    aria-label="Full extracted text"
                    readOnly
                    value={response.extracted_text.replace(
                      /^\s*===\s*PAGE\s+(\d+)\s*===\s*$/gim,
                      'Page $1',
                    )}
                    rows={12}
                    className="w-full resize-y rounded-xl border border-themed bg-primary p-4 font-mono text-sm text-primary"
                  />
                </div>
              </div>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}

function CheckValue({ label, value }) {
  return (
    <div className="bg-secondary rounded-lg p-3">
      <p className="text-xs font-bold text-secondary uppercase tracking-wider">{label}</p>
      <p className="mt-1 font-semibold text-primary capitalize">
        {typeof value === 'string' ? value.replace(/_/g, ' ') : value || 'N/A'}
      </p>
    </div>
  );
}

function InvoiceResultCard({ invoice, index }) {
  const { data, gst_check: gstCheck } = invoice;
  const detailFields = [
    ['Invoice number', data.invoice_number],
    ['Invoice date', data.date],
    ['Expense category', data.expense_category],
    ['Net amount before tax', data.taxable_amount],
    ['Discount', data.discount_amount],
    ['Additional charges', data.additional_charges],
    ['Invoice total as printed', gstCheck.declared_total],
  ];

  return (
    <article className="bg-primary border border-themed rounded-xl p-4">
      <h4 className="text-base font-bold text-primary">
        Invoice {index + 1} · Page {invoice.page_number}
      </h4>
      <p className="text-sm text-secondary mt-1">
        {data.vendor_name !== 'N/A' ? data.vendor_name : 'Vendor not found in readable text'}
      </p>
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
        {detailFields.map(([label, value]) => (
          <div key={label} className="bg-secondary rounded-lg p-3">
            <dt className="text-xs font-bold text-secondary uppercase">{label}</dt>
            <dd className="mt-1 font-semibold text-primary">{value && value !== 'N/A' ? value : 'Not found'}</dd>
          </div>
        ))}
      </dl>

      <section className="mt-4 border-t border-themed pt-4">
        <h5 className="font-semibold text-primary">Tax and total verification</h5>
        {gstCheck.taxes.length ? (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-secondary uppercase border-b border-themed">
                <tr>
                  <th className="py-2 pr-3">Tax</th>
                  <th className="py-2 pr-3">Rate</th>
                  <th className="py-2 pr-3">Printed</th>
                  <th className="py-2 pr-3">Calculated</th>
                  <th className="py-2 pr-3">Difference</th>
                  <th className="py-2">Check</th>
                </tr>
              </thead>
              <tbody>
                {gstCheck.taxes.map((tax, taxIndex) => (
                  <tr key={`${tax.tax_type}-${taxIndex}`} className="border-b border-themed last:border-0">
                    <td className="py-2 pr-3 font-medium text-primary">{tax.tax_type}</td>
                    <td className="py-2 pr-3 text-primary">{tax.rate}</td>
                    <td className="py-2 pr-3 text-primary">{tax.declared_amount}</td>
                    <td className="py-2 pr-3 text-primary">{tax.calculated_amount}</td>
                    <td className="py-2 pr-3 text-primary">{tax.difference}</td>
                    <td className="py-2 text-primary">{tax.status.replace(/_/g, ' ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-2 text-sm text-secondary">No tax lines were found in this invoice.</p>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
          <CheckValue label="GST shown" value={gstCheck.gst_total} />
          <CheckValue label="Other tax shown" value={gstCheck.other_tax_total} />
          <CheckValue label="GST recalculated" value={gstCheck.calculated_gst_total} />
          <CheckValue label="Other tax recalculated" value={gstCheck.calculated_other_tax_total} />
          <CheckValue label="Total using printed tax" value={gstCheck.calculated_total} />
          <CheckValue label="Printed minus shown-tax total" value={gstCheck.total_difference} />
          <CheckValue label="Recalculated payable total" value={gstCheck.recalculated_total} />
          <CheckValue label="Printed minus recalculated" value={gstCheck.recalculated_difference} />
          <CheckValue label="Recalculated total check" value={gstCheck.recalculated_total_status} />
          <CheckValue label="Tax check" value={gstCheck.tax_status} />
          <CheckValue label="Printed component check" value={gstCheck.total_status} />
        </div>
        <p className="mt-3 text-xs text-secondary">
          Shown-tax total = net amount + printed tax amounts + additional charges.
          Recalculated total uses the tax amounts recalculated from each rate.
        </p>
        {gstCheck.warnings.length > 0 && (
          <ul className="mt-3 space-y-1 text-sm text-yellow-600 dark:text-yellow-400 list-disc list-inside">
            {gstCheck.warnings.map((warning, warningIndex) => <li key={warningIndex}>{warning}</li>)}
          </ul>
        )}
      </section>
    </article>
  );
}

function TaxCheckSection({ gstCheck }) {
  return (
    <section className="bg-primary border border-themed rounded-xl p-4">
      <h3 className="text-lg font-semibold text-primary">Tax and total check</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
        <CheckValue label="GST check" value={gstCheck.tax_status} />
        <CheckValue label="Invoice total check" value={gstCheck.total_status} />
        <CheckValue label="GST shown" value={gstCheck.gst_total} />
        <CheckValue label="Other taxes shown" value={gstCheck.other_tax_total} />
        <CheckValue label="Invoice-declared total" value={gstCheck.declared_total} />
        <CheckValue label="Calculated total" value={gstCheck.calculated_total} />
        <CheckValue label="Declared minus calculated" value={gstCheck.total_difference} />
      </div>
      {gstCheck.warnings.length > 0 && (
        <ul className="mt-4 space-y-1 text-sm text-yellow-600 dark:text-yellow-400 list-disc list-inside">
          {gstCheck.warnings.map((warning, index) => <li key={index}>{warning}</li>)}
        </ul>
      )}
    </section>
  );
}

export default App;
