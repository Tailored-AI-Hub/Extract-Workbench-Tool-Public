'use client'

import React from 'react';
import Link from "next/link";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { Button } from "../../../components/ui/button";
import { FileText, ExternalLink, Trash2, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight } from "lucide-react";
import { Document, PaginationMeta } from "../../../services/pdfApi";
import { formatDate } from '../../utils';
import { DocumentSortField, SortDirection, DocumentSortFieldType, SortDirectionType } from '../../types';

interface DocumentsTableProps {
  projectId: string;
  documents: Document[];
  isOwner: boolean;
  onDelete: (document: Document) => void;
  deleting: boolean;
  sortField: DocumentSortFieldType | null;
  sortDirection: SortDirectionType;
  onSort: (field: DocumentSortFieldType) => void;
  uploading?: boolean;
  pagination?: PaginationMeta;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
}

export function DocumentsTable({ 
  projectId, 
  documents, 
  isOwner, 
  onDelete, 
  deleting, 
  sortField, 
  sortDirection, 
  onSort,
  uploading = false,
  pagination,
  onPageChange,
  onPageSizeChange
}: DocumentsTableProps) {
  const renderSortIcon = (field: DocumentSortFieldType) => {
    if (sortField === field) {
      return sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />;
    }
    return <ArrowUpDown className="h-4 w-4 opacity-50" />;
  };

  const SortableHeader = ({ field, children, className }: { field: DocumentSortFieldType; children: React.ReactNode; className?: string }) => (
    <TableHead 
      className={`cursor-pointer hover:bg-gray-50 select-none ${className || ''}`}
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        {renderSortIcon(field)}
      </div>
    </TableHead>
  );
  return (
    <div>
    <Table>
      <TableHeader>
        <TableRow>
          <SortableHeader field="filename" className="max-w-xs">File Name</SortableHeader>
          <SortableHeader field="page_count">Pages</SortableHeader>
          <SortableHeader field="owner_name">Uploaded By</SortableHeader>
          <SortableHeader field="uploaded_at">Uploaded At</SortableHeader>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {/* Loading row when uploading */}
        {uploading && (
          <TableRow className="bg-blue-50/50">
            <TableCell className="font-medium">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="text-blue-600 font-medium">Uploading files...</span>
              </div>
            </TableCell>
            <TableCell className="text-muted-foreground">
              <div className="animate-pulse bg-gray-200 h-4 w-8 rounded"></div>
            </TableCell>
            <TableCell className="text-muted-foreground">
              <div className="animate-pulse bg-gray-200 h-4 w-16 rounded"></div>
            </TableCell>
            <TableCell className="text-muted-foreground">
              <div className="animate-pulse bg-gray-200 h-4 w-20 rounded"></div>
            </TableCell>
            <TableCell>
              <div className="flex items-center justify-end gap-3">
                <div className="animate-pulse bg-gray-200 h-4 w-4 rounded"></div>
                <div className="animate-pulse bg-gray-200 h-4 w-4 rounded"></div>
              </div>
            </TableCell>
          </TableRow>
        )}
        
        {documents.length === 0 && !uploading ? (
          <TableRow>
            <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
              <div className="flex flex-col items-center gap-2">
                <FileText className="h-12 w-12 text-muted-foreground" />
                <h3 className="text-lg font-semibold">No documents yet</h3>
                <p className="text-sm">Upload your first document to get started.</p>
              </div>
            </TableCell>
          </TableRow>
        ) : (
          documents.map((doc) => (
            <TableRow key={doc.uuid} className="cursor-pointer hover:bg-muted/50">
              <TableCell className="font-medium max-w-xs">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <span className="text-foreground truncate" title={doc.filename}>{doc.filename}</span>
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground">{doc.page_count || 'N/A'}</TableCell>
              <TableCell className="text-muted-foreground">
                {doc.owner_name || 'N/A'}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatDate(doc.uploaded_at)}
              </TableCell>
              <TableCell>
                <div className="flex items-center justify-end gap-3">
                  <Link href={`/pdf/projects/${projectId}/documents/${doc.uuid}/extractors`}>
                    <ExternalLink className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                  </Link>
                  <button
                    aria-label={isOwner ? "Delete document" : "Only owners can delete documents"}
                    title={isOwner ? "Delete document" : "Only owners can delete documents"}
                    disabled={!isOwner || deleting}
                    onClick={() => isOwner && onDelete(doc)}
                    className={`text-red-600 hover:text-red-700 disabled:opacity-50 disabled:cursor-not-allowed disabled:text-gray-400`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
    
    {/* Pagination Controls */}
    {pagination && onPageChange && onPageSizeChange && (
      <div className="flex items-center justify-between px-2 py-4 border-t">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>
            Showing {((pagination.page - 1) * pagination.page_size) + 1} to{' '}
            {Math.min(pagination.page * pagination.page_size, pagination.total_count)} of{' '}
            {pagination.total_count} documents
          </span>
          <div className="flex items-center gap-2">
            <span>Rows per page:</span>
            <select
              value={pagination.page_size}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="px-2 py-1 border rounded text-sm"
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.page - 1)}
            disabled={!pagination.has_previous}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          
          <div className="flex items-center gap-1">
            <span className="text-sm text-muted-foreground">
              Page {pagination.page} of {pagination.total_pages}
            </span>
          </div>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.page + 1)}
            disabled={!pagination.has_next}
            className="gap-1"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    )}
  </div>
  );
}

