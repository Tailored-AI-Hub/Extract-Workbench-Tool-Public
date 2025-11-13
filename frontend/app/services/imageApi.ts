import { API_BASE_URL } from './api'

export interface ImageProjectCreateRequest {
  name: string
  description?: string
}

export interface ImageProject {
  uuid: string
  name: string
  description?: string
  created_at: string
  owner_name?: string
  is_owner?: boolean
}

export interface ImageItem {
  uuid: string
  filename: string
  filepath: string
  uploaded_at: string
  width?: number
  height?: number
  file_size_bytes?: number
  owner_name?: string
}

export interface ImagePaginationMeta {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface PaginatedImagesResponse {
  images: ImageItem[]
  pagination: ImagePaginationMeta
}

export interface ImageExtractionJob {
  uuid: string
  image_uuid: string
  extractor: string
  extractor_display_name: string
  status: string
  start_time?: string
  end_time?: string
  latency_ms?: number
  cost?: number
  annotated: number
  total_rating?: number
  total_feedback_count: number
}

export interface ImageContent {
  uuid: string
  extraction_job_uuid: string
  content: Record<string, any>
  metadata_?: Record<string, any>
  feedback?: ImageFeedback
}

export interface ImageFeedback {
  uuid: string
  image_uuid: string
  extraction_job_uuid: string
  feedback_type: string
  rating: number | null
  comment?: string
  user_id?: number
  user_name?: string
  created_at: string
}

export interface ImageFeedbackRequest {
  image_uuid: string
  extraction_job_uuid: string
  rating?: number
  comment?: string
}

export interface ImageAnnotation {
  uuid: string
  image_uuid: string
  extraction_job_uuid: string
  text: string
  comment?: string
  selection_start_char?: number
  selection_end_char?: number
  user_id?: number
  user_name?: string
  created_at: string
}

export interface ImageAnnotationCreateRequest {
  imageId: string
  extractionJobUuid: string
  text: string
  comment?: string
  selectionStartChar?: number
  selectionEndChar?: number
}

export interface ImageAverageRating {
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

export interface ImageExtractorInfo {
  id: string
  name: string
  description: string
  cost_per_page: number
  support_tags: string[]
}

class ImageApiService {
  private getAuthHeaders(token: string) {
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    } as const
  }

  async getExtractors(token: string): Promise<{ image_extractors: Array<{ category: string; extractors: ImageExtractorInfo[] }> }> {
    const res = await fetch(`${API_BASE_URL}/image/extractors`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch image extractors')
    return res.json()
  }

  async getProjects(token: string): Promise<ImageProject[]> {
    const res = await fetch(`${API_BASE_URL}/image/projects`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch image projects')
    return res.json()
  }

  async createProject(payload: ImageProjectCreateRequest, token: string): Promise<ImageProject> {
    const res = await fetch(`${API_BASE_URL}/image/create-project`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('Failed to create image project')
    return res.json()
  }

  async deleteProject(projectUuid: string, token: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to delete image project')
  }

  async getProject(projectUuid: string, token: string): Promise<ImageProject> {
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}`, { headers: this.getAuthHeaders(token) })
    if (!res.ok) throw new Error('Failed to fetch image project')
    return res.json()
  }

  async getProjectImages(
    projectUuid: string,
    token: string,
    page = 1,
    pageSize = 10,
    sortBy = 'uploaded_at',
    sortDirection: 'asc' | 'desc' = 'desc'
  ): Promise<PaginatedImagesResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
      sort_by: sortBy,
      sort_direction: sortDirection,
    })
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}/images?${params}`, {
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to fetch images')
    return res.json()
  }

  async uploadImages(
    projectUuid: string,
    files: File[],
    selectedExtractors: string[],
    token: string
  ): Promise<{ message: string; image_uuids: string[]; failed_uploads: Array<{ filename: string; error: string }> }> {
    const formData = new FormData()
    files.forEach((f) => formData.append('files', f))
    formData.append('selected_extractors', JSON.stringify(selectedExtractors))
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}/upload-multiple`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    })
    if (!res.ok) throw new Error('Failed to upload image files')
    return res.json()
  }

  async getImage(projectUuid: string, imageUuid: string, token: string): Promise<ImageItem> {
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}`, {
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to fetch image')
    return res.json()
  }

  async deleteImage(projectUuid: string, imageUuid: string, token: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to delete image')
  }

  async getImageExtractionJobs(
    projectUuid: string,
    imageUuid: string,
    token: string
  ): Promise<ImageExtractionJob[]> {
    const res = await fetch(
      `${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}/extraction-jobs`,
      { headers: this.getAuthHeaders(token) }
    )
    if (!res.ok) throw new Error('Failed to fetch image extraction jobs')
    return res.json()
  }

  async getImageExtractionContent(
    projectUuid: string,
    imageUuid: string,
    jobUuid: string,
    token: string
  ): Promise<ImageContent> {
    const res = await fetch(
      `${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}/extraction-jobs/${jobUuid}/content`,
      { headers: this.getAuthHeaders(token) }
    )
    if (!res.ok) throw new Error('Failed to fetch image content')
    return res.json()
  }

  // Feedback methods
  async submitImageFeedback(
    projectUuid: string,
    imageUuid: string,
    payload: ImageFeedbackRequest,
    token: string
  ): Promise<ImageFeedback> {
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}/feedback`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('Failed to submit feedback')
    return res.json()
  }

  async getImageFeedback(
    projectUuid: string,
    imageUuid: string,
    token: string
  ): Promise<ImageFeedback[]> {
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}/feedback`, {
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to fetch image feedback')
    return res.json()
  }

  async getImageAverageRating(
    projectUuid: string,
    imageUuid: string,
    jobUuid: string,
    token: string
  ): Promise<ImageAverageRating> {
    const res = await fetch(
      `${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}/extraction-jobs/${jobUuid}/average-rating`,
      { headers: this.getAuthHeaders(token) }
    )
    if (!res.ok) throw new Error('Failed to fetch average rating')
    return res.json()
  }

  async getImageRatingBreakdown(projectUuid: string, imageUuid: string, jobUuid: string, token: string): Promise<UserRatingBreakdown[]> {
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}/extraction-jobs/${jobUuid}/rating-breakdown`, {
      headers: this.getAuthHeaders(token)
    })
    if (!res.ok) throw new Error('Failed to fetch image rating breakdown')
    return res.json()
  }

  // Annotation methods
  async getImageAnnotations(
    imageId: string,
    token: string,
    extractionJobUuid?: string
  ): Promise<ImageAnnotation[]> {
    const params = new URLSearchParams({ imageId })
    if (extractionJobUuid) params.append('extractionJobUuid', extractionJobUuid)
    const res = await fetch(`${API_BASE_URL}/image/annotations?${params}`, {
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to fetch annotations')
    return res.json()
  }

  async createImageAnnotation(payload: ImageAnnotationCreateRequest, token: string): Promise<ImageAnnotation> {
    const res = await fetch(`${API_BASE_URL}/image/annotations`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('Failed to create annotation')
    return res.json()
  }

  async deleteImageAnnotation(annotationUuid: string, token: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/image/annotations/${annotationUuid}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
    if (!res.ok) throw new Error('Failed to delete annotation')
  }

  async downloadImageFile(projectUuid: string, imageUuid: string, token: string): Promise<Blob> {
    const res = await fetch(`${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}/image-load`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('Failed to download image file')
    return res.blob()
  }

  async retryExtractionJob(
    projectUuid: string,
    imageUuid: string,
    jobUuid: string,
    token: string
  ): Promise<{ message: string; job_uuid: string; status: string }> {
    const res = await fetch(
      `${API_BASE_URL}/image/projects/${projectUuid}/images/${imageUuid}/extraction-jobs/${jobUuid}/retry`,
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

export const imageApi = new ImageApiService()

