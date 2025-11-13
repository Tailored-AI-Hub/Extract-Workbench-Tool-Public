'use client'

import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import { DocumentExtractionJob } from "../../../services/pdfApi";

interface ExtractorSelectorProps {
  selectedExtractor: string;
  extractionJobs: DocumentExtractionJob[];
  onSelectExtractor: (extractor: string) => void;
  formatExtractorLabel?: (extractor: string) => string;
}

export function ExtractorSelector({ selectedExtractor, extractionJobs, onSelectExtractor, formatExtractorLabel }: ExtractorSelectorProps) {
  // Filter to only show successful extraction jobs
  const successfulJobs = extractionJobs.filter(job => job.status === 'Success');
  const formatLabel = formatExtractorLabel ?? ((extractor: string) => extractor);
  
  return (
    <Select value={selectedExtractor} onValueChange={onSelectExtractor}>
      <SelectTrigger className="w-30 h-8">
        <SelectValue placeholder="Select extractor" />
      </SelectTrigger>
      <SelectContent>
        {successfulJobs.map((job) => (
          <SelectItem key={job.uuid} value={job.extractor}>
            {job.extractor_display_name || formatLabel(job.extractor)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

