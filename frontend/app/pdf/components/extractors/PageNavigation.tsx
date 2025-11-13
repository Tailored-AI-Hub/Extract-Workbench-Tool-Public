'use client'

import React, { useState } from 'react';
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PageNavigationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function PageNavigation({ currentPage, totalPages, onPageChange }: PageNavigationProps) {
  const [gotoPage, setGotoPage] = useState("");

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      onPageChange(page);
    }
  };

  const handleGotoPage = () => {
    const pageNum = parseInt(gotoPage);
    if (pageNum >= 1 && pageNum <= totalPages) {
      onPageChange(pageNum);
      setGotoPage("");
    }
  };

  // Calculate current page range
  const currentRangeStart = Math.floor((currentPage - 1) / 5) * 5 + 1;
  const currentRangeEnd = Math.min(currentRangeStart + 4, totalPages);
  const isLastRange = currentRangeEnd === totalPages;
  
  // Show 5 consecutive pages
  const pagesToShow = [];
  for (let i = currentRangeStart; i <= currentRangeEnd; i++) {
    pagesToShow.push(i);
  }

  return (
    <div className="bg-gray-50 px-4 py-3 border-b flex items-center justify-center gap-2 sticky top-0 z-10">
      <Button
        variant="outline"
        size="sm"
        onClick={() => handlePageChange(currentPage - 1)}
        disabled={currentPage <= 1}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      
      <div className="flex items-center gap-1">
        {pagesToShow.map((pageNum) => (
          <Button
            key={pageNum}
            variant={currentPage === pageNum ? "default" : "outline"}
            size="sm"
            onClick={() => handlePageChange(pageNum)}
            className="w-8 h-8 p-0"
          >
            {pageNum}
          </Button>
        ))}
        {/* Show last page if not already included and not in last range */}
        {!isLastRange && totalPages > 5 && (
          <>
            <span className="text-gray-400">...</span>
            <Button
              variant={currentPage === totalPages ? "default" : "outline"}
              size="sm"
              onClick={() => handlePageChange(totalPages)}
              className="w-8 h-8 p-0"
            >
              {totalPages}
            </Button>
          </>
        )}
      </div>
      
      <Button
        variant="outline"
        size="sm"
        onClick={() => handlePageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
      
      <div className="flex items-center gap-2 ml-4">
        <Input
          type="number"
          placeholder="Go to"
          value={gotoPage}
          onChange={(e) => setGotoPage(e.target.value)}
          className="w-20 h-8 text-xs"
          min="1"
          max={totalPages}
        />
        <Button
          variant="outline"
          size="sm"
          onClick={handleGotoPage}
          className="h-8 px-2"
        >
          Go
        </Button>
      </div>
    </div>
  );
}

