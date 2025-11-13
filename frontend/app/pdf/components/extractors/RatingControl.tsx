'use client'

import React from 'react';
import { Star, Loader2 } from "lucide-react";

interface RatingControlProps {
  rating: number;
  onRatingChange: (rating: number) => void;
  submitting: boolean;
  error?: string | null;
  averageRating?: number | null;
  totalRatings?: number;
}

export function RatingControl({ 
  rating, 
  onRatingChange, 
  submitting, 
  error,
  averageRating,
  totalRatings
}: RatingControlProps) {
  // Safeguard: Ensure rating is never negative or invalid
  const safeRating = Math.max(0, Math.min(5, rating || 0));
  
  return (
    <div className="flex items-center gap-2">
      {/* Average Rating Display */}
      <div className="flex items-center gap-1">
        <span className="text-sm font-medium text-gray-700">Rating:</span>
        {averageRating !== null && averageRating !== undefined ? (
          <div className="flex items-center gap-1">
            <span className="text-yellow-500">★</span>
            <span className="text-sm">{averageRating.toFixed(1)}</span>
          </div>
        ) : (
          <span className="text-sm text-gray-500">--</span>
        )}
      </div>
      
      {/* User Rating Input */}
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => onRatingChange(star)}
            disabled={submitting}
            className={`p-0.5 transition-transform ${submitting ? 'opacity-50 cursor-not-allowed' : 'hover:scale-110'}`}
            title={`Rate ${star} star${star > 1 ? 's' : ''}`}
          >
            <Star
              className={`h-3 w-3 ${
                star <= safeRating
                  ? "text-yellow-400 fill-yellow-400"
                  : "text-gray-300 hover:text-yellow-300"
              }`}
            />
          </button>
        ))}
        {submitting && (
          <Loader2 className="ml-1 h-3 w-3 animate-spin text-gray-500" />
        )}
      </div>
      
      {error && (
        <span className="text-xs text-red-600 ml-1">{error}</span>
      )}
    </div>
  );
}

