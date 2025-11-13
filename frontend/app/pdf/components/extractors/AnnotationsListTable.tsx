'use client'

import React, { useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { Input } from "../../../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import { Loader2, AlertCircle, Search, FileText } from "lucide-react";
import { pdfApi, AnnotationListItem, DocumentExtractionJob } from "../../../services/pdfApi";

interface AnnotationsListTableProps {
  projectId: string;
  documentId: string;
  token: string | null;
  extractionJobs: DocumentExtractionJob[];
  onAnnotationClick: (pageNumber: number, extractorUuid: string, annotationUuid: string) => void;
}

export function AnnotationsListTable({
  projectId,
  documentId,
  token,
  extractionJobs,
  onAnnotationClick,
}: AnnotationsListTableProps) {
  const [annotations, setAnnotations] = useState<AnnotationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filter state
  const [selectedExtractor, setSelectedExtractor] = useState<string>('all');
  const [searchText, setSearchText] = useState<string>('');

  useEffect(() => {
    const fetchAnnotations = async () => {
      if (!token) return;
      
      try {
        setLoading(true);
        setError(null);
        
        const filters: any = {};
        if (selectedExtractor !== 'all') {
          filters.extractorUuid = selectedExtractor;
        }
        if (searchText.trim()) {
          filters.search = searchText.trim();
        }
        
        const data = await pdfApi.getAnnotationsList(
          projectId,
          documentId,
          token,
          filters
        );
        setAnnotations(data);
      } catch (err) {
        console.error('Error fetching annotations list:', err);
        setError(err instanceof Error ? err.message : 'Failed to load annotations');
      } finally {
        setLoading(false);
      }
    };

    fetchAnnotations();
  }, [projectId, documentId, token, selectedExtractor, searchText]);

  const truncateText = (text: string, maxLength: number) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const getSelectedText = (annotation: AnnotationListItem) => {
    const { text, selection_start, selection_end } = annotation;
    if (!text) return '';

    const normalizedStart = Math.max(0, Math.min(selection_start ?? 0, text.length));
    const normalizedEnd = Math.max(normalizedStart, Math.min(selection_end ?? normalizedStart, text.length));

    const selection = text.slice(normalizedStart, normalizedEnd);
    return selection || text;
  };

  const successfulJobs = extractionJobs.filter(job => job.status === 'Success');

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading annotations...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12 text-red-600">
        <AlertCircle className="h-6 w-6 mr-2" />
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search in text or comments..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <div className="w-64">
          <Select value={selectedExtractor} onValueChange={setSelectedExtractor}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by extractor" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Extractors</SelectItem>
              {successfulJobs.map(job => (
                <SelectItem key={job.uuid} value={job.uuid}>
                  {job.extractor_display_name || job.extractor}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      {annotations.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <FileText className="h-16 w-16 mb-4 opacity-50" />
          <h3 className="text-lg font-semibold mb-2">No annotations found</h3>
          <p className="text-sm">
            {searchText || selectedExtractor !== 'all' 
              ? 'Try adjusting your filters' 
              : 'Start annotating text in the Annotation tab'}
          </p>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">Page</TableHead>
                <TableHead className="w-32">Extractor</TableHead>
                <TableHead className="w-32">User</TableHead>
                <TableHead>Selected Text</TableHead>
                <TableHead>Comment</TableHead>
                <TableHead className="w-32">Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {annotations.map((annotation) => {
                const selectedText = getSelectedText(annotation);
                return (
                  <TableRow
                    key={annotation.uuid}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => onAnnotationClick(
                      annotation.page_number,
                      annotation.extraction_job_uuid,
                      annotation.uuid
                    )}
                  >
                    <TableCell className="font-medium">{annotation.page_number}</TableCell>
                    <TableCell className="text-sm">{annotation.extractor || annotation.extractor_name || 'Unknown'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {annotation.user_name || 'Unknown'}
                    </TableCell>
                    <TableCell className="max-w-md">
                      <div className="text-sm" title={selectedText}>
                        {truncateText(selectedText, 100)}
                      </div>
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <div className="text-sm text-muted-foreground" title={annotation.comment}>
                        {annotation.comment ? truncateText(annotation.comment, 80) : '-'}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(annotation.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
      
      {annotations.length > 0 && (
        <div className="text-sm text-muted-foreground text-center">
          Showing {annotations.length} annotation{annotations.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}

