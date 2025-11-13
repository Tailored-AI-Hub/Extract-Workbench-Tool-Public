import { API_BASE_URL } from './api'

export interface AudioProjectCreateRequest {
  name: string
  description?: string
}

export interface AudioProject {
  uuid: string
  name: string
  description?: string
  created_at: string
  owner_name?: string
  is_owner?: boolean
}

export interface AudioItem {
  uuid: string
  filename: string
  filepath: string
  uploaded_at: string
  duration_seconds?: number
  owner_name?: string
}

export interface AudioPaginationMeta {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface PaginatedAudiosResponse {
  audios: AudioItem[]
  pagination: AudioPaginationMeta
}

export interface AudioExtractionJob {
  uuid: string
  audio_uuid: string
  extractor: string
  extractor_display_name: string
  status: string
  start_time?: string
  end_time?: string
  latency_ms?: number
  cost?: number
  segments_annotated: number
  total_rating?: number
  total_feedback_count: number
}

export interface AudioSegmentContent {
  uuid: string
  extraction_job_uuid: string
  segment_number: number
  start_ms?: number | null
  end_ms?: number | null
  content: Record<string, any>
}

export interface AudioAnnotation {
  uuid: string
  audio_uuid: string
  extraction_job_uuid: string
  segment_number: number
  text: string
  comment?: string
  selection_start_char?: number
  selection_end_char?: number
  user_id?: number
  user_name?: string
  created_at: string
}

export interface AudioSegmentFeedback {
  uuid: string
  audio_uuid: string
  segment_number: number
  extraction_job_uuid: string
  feedback_type: string
  rating: number | null
  comment?: string
  created_at: string
}

export interface AudioSegmentAverageRating {
  average_rating: number | null
  total_ratings: number
  user_rating: number | null
}

export interface UserRatingBreakdown {
  user_id?: number
  user_name?: string
  average_rating: number
  pages_rated: number
  total_ratings: number
  latest_comment?: string
  latest_rated_at: string
}

class AudioApiService {
  private getAuthHeaders(token: string) {
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    } as const
  }

  async getProjects(token: string): Promise<AudioProject[]> {
    const res = await fetch(`${API_BASE_URL}/audio/projects`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch audio projects')
    return res.json()
  }

  async createProject(payload: AudioProjectCreateRequest, token: string): Promise<AudioProject> {
    const res = await fetch(`${API_BASE_URL}/audio/create-project`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('Failed to create audio project')
    return res.json()
  }

  async deleteProject(projectUuid: string, token: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to delete audio project')
  }

  async getProject(projectUuid: string, token: string): Promise<AudioProject> {
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch audio project')
    return res.json()
  }

  async getProjectAudios(projectUuid: string, token: string, page = 1, pageSize = 10, sortBy = 'uploaded_at', sortDirection: 'asc' | 'desc' = 'desc'): Promise<PaginatedAudiosResponse> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), sort_by: sortBy, sort_direction: sortDirection })
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/audios?${params}`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch audios')
    return res.json()
  }

  async uploadAudios(projectUuid: string, files: File[], selectedExtractors: string[], token: string, ownerName: string): Promise<{ message: string; audio_uuids: string[]; failed_uploads: Array<{ filename: string; error: string }> }> {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    formData.append('selected_extractors', JSON.stringify(selectedExtractors))
    formData.append('owner_name', ownerName)
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/upload-multiple`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    })
    if (!res.ok) throw new Error('Failed to upload audio files')
    return res.json()
  }

  async getAudioExtractionJobs(projectUuid: string, audioUuid: string, token: string): Promise<AudioExtractionJob[]> {
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/audios/${audioUuid}/extraction-jobs`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch audio extraction jobs')
    return res.json()
  }

  async getExtractionJobSegments(projectUuid: string, audioUuid: string, jobUuid: string, token: string): Promise<AudioSegmentContent[]> {
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/audios/${audioUuid}/extraction-jobs/${jobUuid}/segments`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch segments')
    return res.json()
  }

  // Annotation methods
  async getAudioAnnotations(audioId: string, token: string, extractionJobUuid?: string, segmentNumber?: number): Promise<AudioAnnotation[]> {
    const params = new URLSearchParams({ audioId })
    if (extractionJobUuid) params.append('extractionJobUuid', extractionJobUuid)
    if (segmentNumber !== undefined) params.append('segmentNumber', String(segmentNumber))
    const res = await fetch(`${API_BASE_URL}/audio/annotations?${params}`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch annotations')
    return res.json()
  }

  async createAudioAnnotation(payload: {
    audioId: string
    extractionJobUuid: string
    segmentNumber: number
    text: string
    comment?: string
    selectionStartChar?: number
    selectionEndChar?: number
  }, token: string): Promise<AudioAnnotation> {
    const res = await fetch(`${API_BASE_URL}/audio/annotations`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('Failed to create annotation')
    return res.json()
  }

  async deleteAudioAnnotation(annotationUuid: string, token: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/audio/annotations/${annotationUuid}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to delete annotation')
  }

  async deleteAudio(projectUuid: string, audioUuid: string, token: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/audios/${audioUuid}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to delete audio')
  }

  // Feedback methods
  async getAudioSegmentFeedback(projectUuid: string, audioUuid: string, segmentNumber: number, token: string): Promise<AudioSegmentFeedback[]> {
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/audios/${audioUuid}/segments/${segmentNumber}/feedback`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch segment feedback')
    return res.json()
  }

  async getAudioSegmentAverageRating(projectUuid: string, audioUuid: string, segmentNumber: number, extractionJobUuid: string, token: string): Promise<AudioSegmentAverageRating> {
    const params = new URLSearchParams({ extraction_job_uuid: extractionJobUuid })
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/audios/${audioUuid}/segments/${segmentNumber}/average-rating?${params}`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch average rating')
    return res.json()
  }

  async submitAudioSegmentFeedback(payload: {
    audio_uuid: string
    segment_number: number
    extraction_job_uuid: string
    rating: number
    comment?: string
  }, projectUuid: string, token: string): Promise<AudioSegmentFeedback> {
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/audios/${payload.audio_uuid}/feedback`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('Failed to submit feedback')
    return res.json()
  }

  async getAudioRatingBreakdown(projectUuid: string, audioUuid: string, jobUuid: string, token: string): Promise<UserRatingBreakdown[]> {
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/audios/${audioUuid}/extraction-jobs/${jobUuid}/rating-breakdown`, {
      headers: this.getAuthHeaders(token)
    })
    if (!res.ok) throw new Error('Failed to fetch audio rating breakdown')
    return res.json()
  }

  async getAudioExtractionRawResult(projectUuid: string, audioUuid: string, jobUuid: string, token: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/audio/projects/${projectUuid}/audios/${audioUuid}/extraction-jobs/${jobUuid}/raw-result`, {
      headers: this.getAuthHeaders(token)
    })
    if (!res.ok) throw new Error('Failed to fetch raw extraction result')
    return res.json()
  }

  async retryExtractionJob(
    projectUuid: string,
    audioUuid: string,
    jobUuid: string,
    token: string
  ): Promise<{ message: string; job_uuid: string; status: string }> {
    const res = await fetch(
      `${API_BASE_URL}/audio/projects/${projectUuid}/audios/${audioUuid}/extraction-jobs/${jobUuid}/retry`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(token),
      }
    )
    if (!res.ok) {
      const error = await res.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to retry extraction job')
    }
    return res.json()
  }
}

export const audioApi = new AudioApiService()


