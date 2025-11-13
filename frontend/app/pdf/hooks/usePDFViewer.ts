import { useState, useEffect, useRef } from 'react';

export function usePDFViewer(pdfUrl: string, token: string | null, activeTab: string, currentPage: number, setCurrentPage: (page: number) => void) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);

  // Load PDF via PDF.js when the document URL changes
  useEffect(() => {
    let isCancelled = false;
    
    const loadPdf = async () => {
      if (!pdfUrl) return;
      
      const existing = window.document.getElementById('pdfjs-script') as HTMLScriptElement | null;
      const ensureScript = () => new Promise<void>((resolve, reject) => {
        if (existing && (window as any).pdfjsLib) {
          resolve();
          return;
        }
        const script = existing ?? window.document.createElement('script');
        script.id = 'pdfjs-script';
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        (script as any).crossOrigin = 'anonymous';
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('Failed to load PDF.js'));
        if (!existing) window.document.body.appendChild(script);
      });
      
      try {
        await ensureScript();
        const pdfjsLib = (window as any).pdfjsLib;
        if (!pdfjsLib) return;
        pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

        let loaded: any | null = null;
        try {
          const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
          const res = await fetch(pdfUrl, { headers });
          if (res.ok) {
            const data = await res.arrayBuffer();
            const loadingTask = pdfjsLib.getDocument({ data });
            loaded = await loadingTask.promise;
            setPdfError(null);
          } else {
            setPdfError(`Failed to load PDF (${res.status})`);
          }
        } catch {
          setPdfError('Failed to fetch PDF');
        }

        if (!isCancelled) setPdfDoc(loaded);
      } catch {
        // silently ignore
      }
    };

    // reset previous state and load
    setPdfDoc(null);
    loadPdf();

    return () => { isCancelled = true; };
  }, [pdfUrl, token, activeTab]);

  // Render current page to canvas when pdfDoc or currentPage changes
  useEffect(() => {
    const renderPage = async () => {
      if (!pdfDoc || !canvasRef.current) return;
      try {
        const page = await pdfDoc.getPage(currentPage);
        const viewport = page.getViewport({ scale: 1.4 });
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        await page.render({ canvasContext: ctx, viewport }).promise;
      } catch {
        // ignore render errors
      }
    };
    renderPage();
  }, [pdfDoc, currentPage]);

  return {
    canvasRef,
    pdfDoc,
    pdfError
  };
}

