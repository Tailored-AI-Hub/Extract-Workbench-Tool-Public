"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Annotation = {
  id: string;
  start: number; // start index in original text
  end: number; // end index (exclusive)
  comment: string;
};

type Props = {
  text: string;
  className?: string;
  initialAnnotations?: Array<{ id?: string; start: number; end: number; comment: string }>;
  onCreate?: (a: { start: number; end: number; comment: string }) => Promise<{ id?: string } | void> | { id?: string } | void;
  onDelete?: (id: string) => Promise<void> | void;
  highlightedAnnotationId?: string | null;
};

export default function AnnotatableText({ text, className, initialAnnotations, onCreate, onDelete, highlightedAnnotationId }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectionRange, setSelectionRange] = useState<{ start: number; end: number } | null>(null);
  const [popup, setPopup] = useState<{ visible: boolean; x: number; y: number } | null>(null);
  const [draftComment, setDraftComment] = useState("");

  const getTextOffsetFromNode = useCallback(
    (node: Node, nodeOffset: number): number => {
      const root = containerRef.current;
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

  const handleMouseUp = useCallback((e: React.MouseEvent) => {
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
    const rect = wrapperRef.current?.getBoundingClientRect();
    const x = rect ? e.clientX - rect.left + 8 : e.clientX + 8;
    const y = rect ? e.clientY - rect.top + 8 : e.clientY + 8;
    setPopup({ visible: true, x, y });
  }, [getTextOffsetFromNode]);

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
      const sel = window.getSelection();
      if (sel) sel.removeAllRanges();
    })();
  }, [selectionRange, draftComment, onCreate]);

  const cancelPopup = useCallback(() => {
    setSelectionRange(null);
    setDraftComment("");
    setPopup(null);
    const sel = window.getSelection();
    if (sel) sel.removeAllRanges();
  }, []);

  const renderedContent = useMemo(() => {
    const content = text || "";
    if (!content) return "";

    if (annotations.length === 0) {
      return content;
    }

    const len = content.length;
    const sorted = [...annotations].sort((a, b) => a.start - b.start);
    const nodes: React.ReactNode[] = [];
    let cursor = 0;

    sorted.forEach((anno, index) => {
      const start = Math.max(0, Math.min(anno.start, len));
      const end = Math.max(start, Math.min(anno.end, len));

      if (start > cursor) {
        const slice = content.slice(cursor, start);
        nodes.push(<React.Fragment key={`text-${cursor}-${start}`}>{slice}</React.Fragment>);
      }

      if (end > start) {
        const slice = content.slice(start, end);
        const isHighlighted = highlightedAnnotationId === anno.id;
        nodes.push(
          <mark
            key={`anno-${anno.id}-${index}-${start}-${end}`}
            data-anno-id={anno.id}
            className={`rounded px-0.5 cursor-pointer ${
              isHighlighted 
                ? 'bg-yellow-400 ring-2 ring-yellow-600 ring-offset-1' 
                : 'bg-yellow-200'
            }`}
          >
            {slice}
          </mark>
        );
      }

      cursor = end;
    });

    if (cursor < len) {
      nodes.push(<React.Fragment key={`text-${cursor}-${len}`}>{content.slice(cursor)}</React.Fragment>);
    }

    return nodes;
  }, [text, annotations, highlightedAnnotationId]);

  // Positions for hover tooltip and clicked popup
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null);
  const [selectedPos, setSelectedPos] = useState<{ x: number; y: number } | null>(null);

  // Hover handlers (show lightweight tooltip while moving over marks)
  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const handleOver = (ev: MouseEvent) => {
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
        const rect = wrapperRef.current?.getBoundingClientRect();
        const x = rect ? ev.clientX - rect.left + 8 : ev.clientX + 8;
        const y = rect ? ev.clientY - rect.top + 8 : ev.clientY + 8;
        setHoverPos({ x, y });
      }
    };

    const handleLeave = () => {
      setHoveredId(null);
    };

    root.addEventListener("mousemove", handleOver);
    root.addEventListener("mouseleave", handleLeave);
    return () => {
      root.removeEventListener("mousemove", handleOver);
      root.removeEventListener("mouseleave", handleLeave);
    };
  }, []);

  // Click on highlight to open a persistent annotation popup near cursor
  const handleClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;
    const mark = target.closest("mark[data-anno-id]") as HTMLElement | null;
    if (mark) {
      const id = mark.getAttribute("data-anno-id");
      if (id) {
        setSelectedId(prev => (prev === id ? null : id));
        const rect = wrapperRef.current?.getBoundingClientRect();
        const x = rect ? e.clientX - rect.left + 8 : e.clientX + 8;
        const y = rect ? e.clientY - rect.top + 8 : e.clientY + 8;
        setSelectedPos({ x, y });
      }
    }
  }, []);

  const hoveredAnnotation = hoveredId ? annotations.find(a => a.id === hoveredId) : null;
  const selectedAnnotation = selectedId ? annotations.find(a => a.id === selectedId) : null;
  const deleteAnnotation = useCallback((id: string) => {
    (async () => {
      try { await Promise.resolve(onDelete?.(id)); } catch {}
      setAnnotations(prev => prev.filter(a => a.id !== id));
      setHoveredId(prev => (prev === id ? null : prev));
      setSelectedId(prev => (prev === id ? null : prev));
    })();
  }, [onDelete]);

  // Load initial annotations when text or prop changes
  useEffect(() => {
    if (!initialAnnotations || initialAnnotations.length === 0) {
      setAnnotations([]);
      return;
    }
    // Only process on client side to avoid hydration mismatch
    if (typeof window === 'undefined') return;
    
    const len = (text || '').length;
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
  }, [initialAnnotations, text]);

  // Scroll to highlighted annotation
  useEffect(() => {
    if (!highlightedAnnotationId || !containerRef.current) return;
    
    const mark = containerRef.current.querySelector(`mark[data-anno-id="${highlightedAnnotationId}"]`) as HTMLElement;
    if (mark) {
      mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [highlightedAnnotationId]);

  return (
    <div ref={wrapperRef} className={["relative", className].filter(Boolean).join(" ")}> 
      <div
        ref={containerRef}
        className="relative whitespace-pre-wrap text-sm text-foreground selectable-text"
        onMouseUp={handleMouseUp}
        onClick={handleClick}
      >
        {renderedContent}
      </div>

      {popup?.visible && (
        <div
          className="absolute z-30 bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700 shadow-lg rounded p-2 w-64"
          style={{ left: popup.x, top: popup.y }}
        >
          <div className="text-xs font-medium mb-1">Add annotation</div>
          <textarea
            className="w-full h-16 text-sm rounded border border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-1"
            value={draftComment}
            onChange={(e) => setDraftComment(e.target.value)}
            placeholder="Type your note..."
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

      {hoveredAnnotation && hoverPos && (!selectedAnnotation || selectedAnnotation.id !== hoveredAnnotation.id) && (
        <div
          className="absolute z-20 max-w-xs bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700 shadow-md rounded p-2 text-xs"
          style={{ left: hoverPos.x, top: hoverPos.y }}
        >
          <div className="whitespace-pre-wrap">{hoveredAnnotation.comment}</div>
        </div>
      )}

      {selectedAnnotation && selectedPos && (
        <div
          className="absolute z-30 max-w-xs bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700 shadow-lg rounded p-2 text-xs"
          style={{ left: selectedPos.x, top: selectedPos.y }}
        >
          <div className="mb-2 whitespace-pre-wrap">{selectedAnnotation.comment}</div>
          <div className="flex justify-end gap-2">
            <button
              className="px-2 py-1 text-[10px] rounded bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700"
              onClick={() => setSelectedId(null)}
            >
              Close
            </button>
            <button
              className="px-2 py-1 text-[10px] rounded bg-red-600 text-white hover:bg-red-700"
              onClick={() => selectedAnnotation && deleteAnnotation(selectedAnnotation.id)}
            >
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


