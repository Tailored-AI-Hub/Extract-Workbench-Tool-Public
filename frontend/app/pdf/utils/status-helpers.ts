type StatusVariant = "default" | "secondary" | "destructive" | "outline";

export interface StatusConfig {
  variant: StatusVariant;
  text: string;
}

const STATUS_CONFIGS: Record<string, StatusConfig> = {
  Success: { variant: "default", text: "Success" },
  Failure: { variant: "destructive", text: "Failed" },
  Processing: { variant: "secondary", text: "Processing" },
  "Not Started": { variant: "outline", text: "Not Started" },
  Completed: { variant: "default", text: "Completed" },
  Failed: { variant: "destructive", text: "Failed" },
  Queued: { variant: "outline", text: "Queued" }
};

/**
 * Get status configuration for a given status
 */
export function getStatusConfig(status: string): StatusConfig {
  return STATUS_CONFIGS[status] || { variant: "outline" as const, text: status };
}

/**
 * Check if a job can be retried
 */
export function canRetryJob(status: string): boolean {
  return status === 'Failed' || status === 'Failure';
}

/**
 * Get retry button tooltip text
 */
export function getRetryTooltip(status: string): string {
  if (canRetryJob(status)) {
    return "Retry extraction";
  }
  if (status === 'Success') {
    return "Retry not needed - extraction successful";
  }
  return "Retry not available - job not failed";
}

/**
 * Check if any extractor has Success status
 */
export function hasSuccessfulExtractor(extractionJobs: Array<{ status: string }>): boolean {
  return extractionJobs.some(job => job.status === 'Success');
}

