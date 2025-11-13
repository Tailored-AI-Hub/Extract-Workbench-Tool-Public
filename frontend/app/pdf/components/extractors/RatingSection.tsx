/**
 * Rating section component
 * Handles rating display and submission
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { RatingControl } from './RatingControl';
import { PageAverageRating } from '../../../services/pdfApi';
import { Loader2 } from 'lucide-react';

interface RatingSectionProps {
  rating: number;
  pageAverageRating: PageAverageRating | null;
  submittingRating: boolean;
  loadingAverageRating: boolean;
  ratingError: string | null;
  onRatingChange: (rating: number) => void;
}

export function RatingSection({
  rating,
  pageAverageRating,
  submittingRating,
  loadingAverageRating,
  ratingError,
  onRatingChange,
}: RatingSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Rate This Page</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <RatingControl
          rating={rating}
          onRatingChange={onRatingChange}
          submitting={submittingRating}
          error={ratingError}
        />

        {ratingError && (
          <div className="text-sm text-red-600">{ratingError}</div>
        )}

        {loadingAverageRating ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            Loading average rating...
          </div>
        ) : (
          pageAverageRating && (
            <div className="space-y-1 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Average Rating:</span>
                <span className="font-medium">
                  {pageAverageRating.average_rating?.toFixed(1) || 'N/A'} / 5
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Total Ratings:</span>
                <span className="font-medium">{pageAverageRating.total_ratings}</span>
              </div>
              {pageAverageRating.user_rating !== null && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Your Rating:</span>
                  <span className="font-medium">{pageAverageRating.user_rating} / 5</span>
                </div>
              )}
            </div>
          )
        )}
      </CardContent>
    </Card>
  );
}
