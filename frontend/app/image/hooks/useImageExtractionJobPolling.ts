import { useCallback, useEffect, useRef } from 'react';
import { imageApi, ImageExtractionJob } from '../../services/imageApi';
import { POLLING_CONFIG } from '../../constants';

export function useImageExtractionJobPolling(
  projectId: string,
  imageId: string,
  token: string | null,
  extractionJobs: ImageExtractionJob[],
  setExtractionJobs: (jobs: ImageExtractionJob[]) => void
) {
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isRatingPollModeRef = useRef(false);
  const extractionJobsRef = useRef(extractionJobs);

  // Keep ref in sync with extractionJobs
  useEffect(() => {
    extractionJobsRef.current = extractionJobs;
  }, [extractionJobs]);

  // Fetch extraction jobs
  const fetchExtractionJobs = useCallback(async () => {
    if (!projectId || !imageId || !token) {
      return;
    }

    try {
      const jobsData = await imageApi.getImageExtractionJobs(projectId, imageId, token);
      setExtractionJobs(jobsData);
    } catch (error) {
      console.error('Failed to fetch image extraction jobs:', error);
    }
  }, [projectId, imageId, token, setExtractionJobs]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    isRatingPollModeRef.current = false;
  }, []);

  // Start fast polling for processing jobs
  const startFastPolling = useCallback(() => {
    stopPolling();
    
    if (!token || !projectId || !imageId) {
      return;
    }
    
    isRatingPollModeRef.current = false;
    
    const interval = setInterval(async () => {
      if (!token) {
        clearInterval(interval);
        pollingIntervalRef.current = null;
        return;
      }
      
      try {
        const jobsData = await imageApi.getImageExtractionJobs(projectId, imageId, token);
        setExtractionJobs(jobsData);
        
        // Check if all jobs are completed (not processing)
        const allCompleted = jobsData.every(job => 
          job.status !== 'Processing' && job.status !== 'NOT_STARTED'
        );
        
        if (allCompleted) {
          clearInterval(interval);
          pollingIntervalRef.current = null;
        }
      } catch (error) {
        console.error('Error polling image extraction jobs:', error);
      }
    }, POLLING_CONFIG.EXTRACTION_JOB_INTERVAL);
    
    pollingIntervalRef.current = interval;
  }, [projectId, imageId, token, setExtractionJobs, stopPolling]);

  // Start slow polling for rating updates
  const startSlowPolling = useCallback(() => {
    stopPolling();
    
    if (!token || !projectId || !imageId) {
      return;
    }
    
    isRatingPollModeRef.current = true;
    
    const interval = setInterval(async () => {
      if (!token) {
        clearInterval(interval);
        pollingIntervalRef.current = null;
        isRatingPollModeRef.current = false;
        return;
      }
      try {
        const jobsData = await imageApi.getImageExtractionJobs(projectId, imageId, token);
        setExtractionJobs(jobsData);
      } catch (error) {
        console.error('Error polling image extraction jobs for ratings:', error);
      }
    }, 10000); // Poll every 10 seconds for rating updates
    
    pollingIntervalRef.current = interval;
  }, [projectId, imageId, token, setExtractionJobs, stopPolling]);

  // Cleanup polling interval on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  // Auto-start polling if there are processing jobs
  // Continue polling after jobs complete to refresh rating data (at slower rate)
  useEffect(() => {
    const hasProcessingJobs = extractionJobs.some(job => 
      job.status === 'Processing' || job.status === 'NOT_STARTED'
    );
    
    if (!token || !projectId || !imageId) {
      stopPolling();
      return;
    }
    
    if (hasProcessingJobs) {
      // Start fast polling (3s) when jobs are processing
      if (!pollingIntervalRef.current || isRatingPollModeRef.current) {
        startFastPolling();
      }
    } else if (extractionJobs.length > 0) {
      // Continue slower polling (10s) after jobs complete to refresh ratings
      if (!pollingIntervalRef.current || !isRatingPollModeRef.current) {
        startSlowPolling();
      }
    } else {
      // No jobs at all, stop polling
      stopPolling();
    }
  }, [extractionJobs, projectId, imageId, token, startFastPolling, startSlowPolling, stopPolling]);

  return {
    fetchExtractionJobs
  };
}

