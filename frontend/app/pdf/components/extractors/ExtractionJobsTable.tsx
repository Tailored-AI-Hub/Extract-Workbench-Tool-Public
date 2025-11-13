'use client'

import React, { useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { Badge } from "../../../components/ui/badge";
import { ArrowUpDown, ArrowUp, ArrowDown, ExternalLink, RotateCcw, Loader2, ChevronDown, ChevronRight, Filter } from "lucide-react";
import { DocumentExtractionJob } from "../../../services/pdfApi";
import { getStatusConfig, formatLatency, formatCost } from '../../utils';
import { SortField, SortDirection } from '../../types';
import { RatingBreakdownRow } from './RatingBreakdownRow';

interface ExtractionJobsTableProps {
  jobs: DocumentExtractionJob[];
  sortField: SortField;
  sortDirection: SortDirection;
  onSort: (field: keyof DocumentExtractionJob) => void;
  onViewExtractor: (extractor: string) => void;
  onRetryJob: (jobUuid: string) => void;
  retryingJobs: Set<string>;
  projectId: string;
  documentId: string;
  token: string | null;
  ratingFilter: 'all' | 'my';
  onRatingFilterChange: (filter: 'all' | 'my') => void;
}

export function ExtractionJobsTable({
  jobs,
  sortField,
  sortDirection,
  onSort,
  onViewExtractor,
  onRetryJob,
  retryingJobs,
  projectId,
  documentId,
  token,
  ratingFilter,
  onRatingFilterChange
}: ExtractionJobsTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRow = (jobUuid: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(jobUuid)) {
        newSet.delete(jobUuid);
      } else {
        newSet.add(jobUuid);
      }
      return newSet;
    });
  };

  const renderSortIcon = (field: keyof DocumentExtractionJob) => {
    if (sortField === field) {
      return sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />;
    }
    return <ArrowUpDown className="h-4 w-4 opacity-50" />;
  };

  const SortableHeader = ({ field, children }: { field: keyof DocumentExtractionJob; children: React.ReactNode }) => (
    <TableHead 
      className="cursor-pointer hover:bg-gray-50 select-none"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        {renderSortIcon(field)}
      </div>
    </TableHead>
  );

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <SortableHeader field="extractor">Extractor</SortableHeader>
          <SortableHeader field="status">Status</SortableHeader>
          <SortableHeader field="latency_ms">Latency (s)</SortableHeader>
          <SortableHeader field="cost">Cost ($)</SortableHeader>
          <SortableHeader field="pages_annotated">Pages Annotated</SortableHeader>
          <TableHead>
            <div className="flex items-center gap-2">
              <button
                className="cursor-pointer hover:bg-gray-50 select-none flex items-center gap-1 py-2"
                onClick={() => onSort('total_rating')}
                title="Sort by rating"
              >
                <span>Average Rating</span>
                {renderSortIcon('total_rating')}
              </button>
              <button
                onClick={() => onRatingFilterChange(ratingFilter === 'all' ? 'my' : 'all')}
                className={`p-1 rounded transition-colors ${
                  ratingFilter === 'my' 
                    ? 'bg-blue-100 text-blue-600 hover:bg-blue-200' 
                    : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'
                }`}
                title={ratingFilter === 'all' ? 'Show only my ratings' : 'Show all ratings'}
              >
                <Filter className="h-3.5 w-3.5" />
              </button>
            </div>
          </TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.length === 0 ? (
          <TableRow>
            <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
              <div className="flex flex-col items-center gap-2">
                <RotateCcw className="h-12 w-12 text-muted-foreground" />
                <h3 className="text-lg font-semibold">No extraction jobs found</h3>
                <p className="text-sm">Extraction jobs will appear here once processing begins.</p>
              </div>
            </TableCell>
          </TableRow>
        ) : (
          jobs.map((job) => {
            const statusConfig = getStatusConfig(job.status);
            const isExpanded = expandedRows.has(job.uuid);
            const hasRating = job.total_rating && job.total_feedback_count > 0;
            return (
            <React.Fragment key={job.uuid}>
              <TableRow className="hover:bg-muted/50">
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <span className="text-foreground">{job.extractor_display_name || job.extractor}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={statusConfig.variant}>{statusConfig.text}</Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatLatency(job.latency_ms)}</TableCell>
                <TableCell className="text-muted-foreground">{formatCost(job.cost)}</TableCell>
                <TableCell className="text-muted-foreground">{job.pages_annotated}</TableCell>
                <TableCell className="text-muted-foreground">
                  {hasRating ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => toggleRow(job.uuid)}
                        className="flex items-center gap-1 hover:text-foreground"
                        title={isExpanded ? "Hide breakdown" : "Show breakdown"}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )}
                        <span className="text-yellow-500">★</span>
                        <span>{job.total_rating}/5</span>
                      </button>
                    </div>
                  ) : (
                    "-"
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-3 mx-4">
                    {job.status === "Success" && (
                      <button
                        aria-label="View extractor"
                        title="View extractor"
                        onClick={() => onViewExtractor(job.extractor)}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </button>
                    )}
                    {job.status === "Failure" && (
                      <button
                        aria-label="Retry job"
                        title="Retry job"
                        disabled={retryingJobs.has(job.uuid)}
                        onClick={() => onRetryJob(job.uuid)}
                        className="text-muted-foreground hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed disabled:text-gray-400"
                      >
                        {retryingJobs.has(job.uuid) ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <RotateCcw className="h-4 w-4" />
                        )}
                      </button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
              {isExpanded && (
                <RatingBreakdownRow
                  projectId={projectId}
                  documentId={documentId}
                  jobUuid={job.uuid}
                  token={token}
                />
              )}
            </React.Fragment>
          );
          })
        )}
      </TableBody>
    </Table>
  );
}

