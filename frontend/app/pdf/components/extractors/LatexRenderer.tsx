'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react';
import DOMPurify from 'dompurify';

// Custom LaTeX syntax highlighting
const highlightLatex = (text: string): string => {
  return text
    // Commands (backslash followed by letters)
    .replace(/\\([a-zA-Z]+)/g, '<span class="text-blue-400 font-semibold">\\$1</span>')
    // Environments
    .replace(/\\begin\{([^}]+)\}/g, '<span class="text-green-400 font-semibold">\\begin</span><span class="text-yellow-300">{</span><span class="text-orange-300">$1</span><span class="text-yellow-300">}</span>')
    .replace(/\\end\{([^}]+)\}/g, '<span class="text-green-400 font-semibold">\\end</span><span class="text-yellow-300">{</span><span class="text-orange-300">$1</span><span class="text-yellow-300">}</span>')
    // Table separators
    .replace(/(\\\\\s*)/g, '<span class="text-red-400 font-bold">\\\\</span>')
    .replace(/(\s*&\s*)/g, '<span class="text-cyan-400 font-bold"> & </span>')
    // Braces
    .replace(/\{/g, '<span class="text-yellow-300">{</span>')
    .replace(/\}/g, '<span class="text-yellow-300">}</span>')
    // Brackets
    .replace(/\[/g, '<span class="text-purple-300">[</span>')
    .replace(/\]/g, '<span class="text-purple-300">]</span>')
    // Comments
    .replace(/(%.*$)/gm, '<span class="text-gray-500 italic">$1</span>')
    // Math delimiters
    .replace(/\$/g, '<span class="text-red-400 font-bold">$</span>')
    // Special characters
    .replace(/(%)/g, '<span class="text-gray-500">$1</span>')
    .replace(/(#)/g, '<span class="text-pink-400">$1</span>');
};

interface Annotation {
  id: string;
  start: number;
  end: number;
  comment: string;
}

interface LatexRendererProps {
  content: string;
  initialAnnotations?: Array<{ id?: string; start: number; end: number; comment: string }>;
  onCreate?: (a: { start: number; end: number; comment: string }) => Promise<{ id?: string } | void> | { id?: string } | void;
  onDelete?: (id: string) => Promise<void> | void;
  highlightedAnnotationId?: string | null;
}

export function LatexRenderer({ content, initialAnnotations = [], onCreate, onDelete, highlightedAnnotationId }: LatexRendererProps) {
  const [highlightedContent, setHighlightedContent] = useState('');
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectionRange, setSelectionRange] = useState<{ start: number; end: number } | null>(null);
  const [popup, setPopup] = useState<{ visible: boolean; x: number; y: number } | null>(null);
  const [draftComment, setDraftComment] = useState("");
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null);
  const [selectedPos, setSelectedPos] = useState<{ x: number; y: number } | null>(null);
  const [cursorPosition, setCursorPosition] = useState<{ x: number; y: number } | null>(null);
  const [clickedAnnotationCursorPos, setClickedAnnotationCursorPos] = useState<{ x: number; y: number } | null>(null);
  
  const codeRef = useRef<HTMLPreElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Format LaTeX content with better indentation and spacing
  const formatLatexContent = (text: string): string => {
    return text
      .replace(/\\begin\{([^}]+)\}/g, '\n\\begin{$1}')
      .replace(/\\end\{([^}]+)\}/g, '\\end{$1}\n')
      .replace(/\\section\*?\{([^}]+)\}/g, '\n\\section*{$1}\n')
      .replace(/\\subsection\*?\{([^}]+)\}/g, '\n\\subsection*{$1}\n')
      .replace(/\\paragraph\*?\{([^}]+)\}/g, '\n\\paragraph*{$1}\n')
      .replace(/\\item/g, '\n  \\item')
      .replace(/\\textbf\{([^}]+)\}/g, '\\textbf{$1}')
      .replace(/\\textit\{([^}]+)\}/g, '\\textit{$1}')
      // Handle table rows
      .replace(/\\\\/g, '\\\\\n')
      // Handle table columns
      .replace(/&/g, ' & ')
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .join('\n');
  };

  // Apply annotations to highlighted HTML by finding text positions and wrapping with mark tags
  const applyAnnotationsToHtml = (html: string, plainText: string): string => {
    if (!annotations.length) return html;

    const sorted = [...annotations].sort((a, b) => b.start - b.start); // Reverse order to insert from end
    let result = html;
    
    for (const anno of sorted) {
      const start = Math.max(0, Math.min(anno.start, plainText.length));
      const end = Math.max(start, Math.min(anno.end, plainText.length));
      const segment = plainText.slice(start, end);
      
      if (!segment) continue;
      
      // Find the position of this segment in the highlighted HTML
      // We need to strip HTML and find the text position
      let htmlPos = 0;
      let textPos = 0;
      
      // Skip through HTML to find text position
      while (htmlPos < result.length && textPos < start) {
        // If we hit a tag, skip it
        if (result[htmlPos] === '<') {
          const tagEnd = result.indexOf('>', htmlPos);
          if (tagEnd === -1) break;
          htmlPos = tagEnd + 1;
        } else {
          htmlPos++;
          textPos++;
        }
      }
      
      const htmlStart = htmlPos;
      
      // Find the end position
      while (htmlPos < result.length && textPos < end) {
        if (result[htmlPos] === '<') {
          const tagEnd = result.indexOf('>', htmlPos);
          if (tagEnd === -1) break;
          htmlPos = tagEnd + 1;
        } else {
          htmlPos++;
          textPos++;
        }
      }
      
      const htmlEnd = htmlPos;
      const highlightedSegment = result.slice(htmlStart, htmlEnd);
      const isHighlighted = highlightedAnnotationId === anno.id;
      const markClass = isHighlighted 
        ? 'bg-yellow-400 ring-2 ring-yellow-600 ring-offset-1 rounded px-0.5 cursor-pointer'
        : 'bg-yellow-200 dark:bg-yellow-900 rounded px-0.5 cursor-pointer';
      const markedSegment = `<mark class="${markClass}" data-anno-id="${anno.id}">${highlightedSegment}</mark>`;
      result = result.slice(0, htmlStart) + markedSegment + result.slice(htmlEnd);
    }

    return result;
  };

  // Get text offset from node
  const getTextOffsetFromNode = useCallback(
    (node: Node, nodeOffset: number): number => {
      const root = codeRef.current;
      if (!root) return 0;

      let offset = 0;
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
      while (walker.nextNode()) {
        const current = walker.currentNode as Text;
        if (current === node) {
          offset += nodeOffset;
          break;
        }
        offset += current.nodeValue ? current.nodeValue.length : 0;
      }
      return offset;
    },
    []
  );

  // Handle mouse up for text selection
  const handleMouseUp = useCallback((e: React.MouseEvent) => {
    if (!onCreate) return;
    
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) {
      setPopup(null);
      return;
    }
    const range = sel.getRangeAt(0);
    if (!range || range.collapsed) {
      setPopup(null);
      return;
    }

    const startOffset = getTextOffsetFromNode(range.startContainer, range.startOffset);
    const endOffset = getTextOffsetFromNode(range.endContainer, range.endOffset);
    if (startOffset === endOffset) {
      setPopup(null);
      return;
    }

    const normalizedStart = Math.max(0, Math.min(startOffset, endOffset));
    const normalizedEnd = Math.max(0, Math.max(startOffset, endOffset));

    setSelectionRange({ start: normalizedStart, end: normalizedEnd });
    setDraftComment("");
    
    // Store cursor position for fixed positioning
    setCursorPosition({ x: e.clientX, y: e.clientY });
    setPopup({ visible: true, x: e.clientX, y: e.clientY });
  }, [getTextOffsetFromNode, onCreate]);

  const saveAnnotation = useCallback(() => {
    (async () => {
      if (!selectionRange) return;
      if (!draftComment.trim()) {
        setPopup(null);
        return;
      }
      // Use crypto.randomUUID() if available, fallback to timestamp + random for client-side only
      const generateId = () => {
        if (typeof window !== 'undefined' && window.crypto && window.crypto.randomUUID) {
          return window.crypto.randomUUID();
        }
        return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      };
      const baseAnno: Annotation = {
        id: generateId(),
        start: selectionRange.start,
        end: selectionRange.end,
        comment: draftComment.trim(),
      };
      let createdId: string | undefined;
      try {
        const res = await Promise.resolve(onCreate?.({ start: baseAnno.start, end: baseAnno.end, comment: baseAnno.comment }));
        if (res && typeof res === 'object' && 'id' in res) createdId = res.id;
      } catch {
        // swallow API errors; keep local annotation so user doesn't lose note
      }
      const newAnno: Annotation = { ...baseAnno, id: createdId || baseAnno.id };
      setAnnotations(prev => [...prev, newAnno].sort((a, b) => a.start - b.start));
      setSelectionRange(null);
      setDraftComment("");
      setPopup(null);
      setCursorPosition(null);
      const sel = window.getSelection();
      if (sel) sel.removeAllRanges();
    })();
  }, [selectionRange, draftComment, onCreate]);

  const cancelPopup = useCallback(() => {
    setSelectionRange(null);
    setDraftComment("");
    setPopup(null);
    setCursorPosition(null);
    const sel = window.getSelection();
    if (sel) sel.removeAllRanges();
  }, []);

  // Load initial annotations
  useEffect(() => {
    if (!initialAnnotations || initialAnnotations.length === 0) {
      setAnnotations([]);
      return;
    }
    // Only process on client side to avoid hydration mismatch
    if (typeof window === 'undefined') return;
    
    const len = (content || '').length;
    // Generate IDs only on client side to avoid hydration mismatch
    const generateId = () => {
      if (window.crypto && window.crypto.randomUUID) {
        return window.crypto.randomUUID();
      }
      return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    };
    const mapped: Annotation[] = initialAnnotations.map(a => ({
      id: a.id || generateId(),
      start: Math.max(0, Math.min(a.start, len)),
      end: Math.max(0, Math.min(a.end, len)),
      comment: a.comment,
    })).sort((x, y) => x.start - y.start);
    setAnnotations(mapped);
  }, [initialAnnotations, content]);

  // Apply syntax highlighting first, then add annotations
  useEffect(() => {
    let formatted = formatLatexContent(content);
    
    // Apply syntax highlighting
    formatted = highlightLatex(formatted);
    
    // Then apply annotations on top of highlighted HTML
    if (annotations.length) {
      formatted = applyAnnotationsToHtml(formatted, content);
    }
    
    setHighlightedContent(formatted);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content, annotations, highlightedAnnotationId]);

  // Scroll to highlighted annotation
  useEffect(() => {
    if (!highlightedAnnotationId || !codeRef.current) return;
    
    const mark = codeRef.current.querySelector(`mark[data-anno-id="${highlightedAnnotationId}"]`) as HTMLElement;
    if (mark) {
      mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [highlightedAnnotationId]);

  const hoveredAnnotation = hoveredId ? annotations.find(a => a.id === hoveredId) : null;
  const selectedAnnotation = selectedId ? annotations.find(a => a.id === selectedId) : null;

  const deleteAnnotation = useCallback((id: string) => {
    (async () => {
      try { await Promise.resolve(onDelete?.(id)); } catch {}
      setAnnotations(prev => prev.filter(a => a.id !== id));
      setHoveredId(prev => (prev === id ? null : prev));
      setSelectedId(prev => (prev === id ? null : prev));
      setClickedAnnotationCursorPos(null);
    })();
  }, [onDelete]);

  // Handle click on annotations
  const handleClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;
    const mark = target.closest("mark[data-anno-id]") as HTMLElement | null;
    if (mark) {
      const id = mark.getAttribute("data-anno-id");
      if (id) {
        setSelectedId(prev => (prev === id ? null : id));
        // Store cursor position for fixed positioning
        setClickedAnnotationCursorPos({ x: e.clientX, y: e.clientY });
        setSelectedPos({ x: e.clientX, y: e.clientY });
      }
    }
  }, []);

  // Hover handlers
  useEffect(() => {
    const root = codeRef.current;
    if (!root) return;

    const handleMove = (ev: MouseEvent) => {
      const target = ev.target as HTMLElement | null;
      if (!target) return;
      const mark = target.closest("mark[data-anno-id]") as HTMLElement | null;
      if (!mark) {
        setHoveredId(null);
        return;
      }
      const id = mark.getAttribute("data-anno-id");
      if (id) {
        setHoveredId(id);
        // Update cursor position as mouse moves to keep tooltip following cursor
        setHoverPos({ x: ev.clientX, y: ev.clientY });
      }
    };

    const handleLeave = () => {
      setHoveredId(null);
    };

    root.addEventListener("mousemove", handleMove);
    root.addEventListener("mouseleave", handleLeave);
    return () => {
      root.removeEventListener("mousemove", handleMove);
      root.removeEventListener("mouseleave", handleLeave);
    };
  }, []);

  return (
    <div className="latex-content -m-4">
      {/* LaTeX content with syntax highlighting */}
      <div className="relative" ref={wrapperRef}>
        <pre
          ref={codeRef}
          className="bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 p-6 overflow-x-auto text-sm leading-relaxed m-0"
          style={{ fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace', border: 'none', margin: 0 }}
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(highlightedContent)
          }}
          onMouseUp={handleMouseUp}
          onClick={handleClick}
        />
      </div>

      {/* Add annotation popup */}
      {popup?.visible && cursorPosition && (
        <div
          className="fixed z-30 bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700 shadow-lg rounded p-2 w-64"
          style={{ 
            left: `${cursorPosition.x + 10}px`, 
            top: `${cursorPosition.y + 10}px` 
          }}
        >
          <div className="text-xs font-medium mb-1">Add annotation</div>
          <textarea
            className="w-full h-16 text-sm rounded border border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-1"
            value={draftComment}
            onChange={(e) => setDraftComment(e.target.value)}
            placeholder="Type your note..."
            autoFocus
          />
          <div className="mt-2 flex justify-end gap-2">
            <button
              className="px-2 py-1 text-xs rounded bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700"
              onClick={cancelPopup}
            >
              Cancel
            </button>
            <button
              className="px-2 py-1 text-xs rounded bg-black dark:bg-gray-800 text-white hover:bg-gray-800 dark:hover:bg-gray-700"
              onClick={saveAnnotation}
            >
              Save
            </button>
          </div>
        </div>
      )}

      {/* Hover tooltip */}
      {hoveredAnnotation && hoverPos && (!selectedAnnotation || selectedAnnotation.id !== hoveredAnnotation.id) && (
        <div
          className="fixed z-20 max-w-xs bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700 shadow-md rounded p-2 text-xs"
          style={{ 
            left: `${hoverPos.x + 10}px`, 
            top: `${hoverPos.y + 10}px` 
          }}
        >
          <div className="whitespace-pre-wrap">{hoveredAnnotation.comment}</div>
        </div>
      )}

      {/* Clicked annotation popup */}
      {selectedAnnotation && clickedAnnotationCursorPos && (
        <div
          className="fixed z-30 max-w-xs bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700 shadow-lg rounded p-2 text-xs"
          style={{ 
            left: `${clickedAnnotationCursorPos.x + 10}px`, 
            top: `${clickedAnnotationCursorPos.y + 10}px` 
          }}
        >
          <div className="mb-2 whitespace-pre-wrap">{selectedAnnotation.comment}</div>
          <div className="flex justify-end gap-2">
            <button
              className="px-2 py-1 text-[10px] rounded bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700"
              onClick={() => {
                setSelectedId(null);
                setClickedAnnotationCursorPos(null);
              }}
            >
              Close
            </button>
            <button
              className="px-2 py-1 text-[10px] rounded bg-red-600 text-white hover:bg-red-700"
              onClick={() => {
                if (selectedAnnotation) {
                  deleteAnnotation(selectedAnnotation.id);
                }
                setClickedAnnotationCursorPos(null);
              }}
            >
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}