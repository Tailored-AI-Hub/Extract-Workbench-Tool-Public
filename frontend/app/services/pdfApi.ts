import { API_BASE_URL } from './api'

// Type definitions for sorting
export type DocumentSortFieldType = 'uploaded_at' | 'filename' | 'file_type' | 'page_count' | 'owner_name' | 'uuid'
export type SortDirectionType = 'asc' | 'desc'

export interface Project {
  uuid: string
  name: string
  description?: string
  created_at: string
  owner_name?: string
  is_owner?: boolean
}

export interface ProjectCreateRequest {
  name: string
  description?: string
}

export interface Document {
  uuid: string
  filename: string
  filepath: string
  uploaded_at: string
  page_count?: number
  file_type: string
  owner_name?: string
}

export interface PaginationMeta {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface PaginatedDocumentsResponse {
  documents: Document[]
  pagination: PaginationMeta
}

export interface DocumentExtractionJob {
  uuid: string
  document_uuid: string
  extractor: string
  extractor_display_name: string
  status: string
  start_time?: string
  end_time?: string
  latency_ms?: number
  cost?: number
  pages_annotated: number
  total_rating?: number
  total_feedback_count: number
}

export interface DocumentPageContent {
  uuid: string
  extraction_job_uuid: string
  page_number: number
  content: Record<string, any>
  feedback?: {
    uuid: string
    document_uuid: string
    page_number: number
    extraction_job_uuid: string
    feedback_type: string
    rating: number
    comment: string
    user_id?: number
    user_name?: string
    created_at: string
  }
  metadata?: Record<string, any>
}

export interface AnnotationPayload {
  documentId: string
  extractionJobUuid: string
  pageNumber: number
  text: string
  comment?: string
  selectionStart: number
  selectionEnd: number
}

export interface AnnotationResponse {
  uuid: string
  document_uuid: string
  extraction_job_uuid: string
  page_number: number
  text: string
  comment?: string
  selection_start: number
  selection_end: number
  user_id?: number
  user_name?: string
  created_at: string
}

export interface FeedbackRequest {
  document_uuid: string
  page_number: number
  extraction_job_uuid: string
  rating: number
  comment?: string
}

export interface FeedbackResponse {
  uuid: string
  document_uuid: string
  page_number: number
  extraction_job_uuid: string
  feedback_type: string
  rating: number
  comment?: string
  user_id?: number
  user_name?: string
  created_at: string
}

export interface PageAverageRating {
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

export interface AnnotationListItem {
  uuid: string
  document_uuid: string
  extraction_job_uuid: string
  page_number: number
  text: string
  comment?: string
  selection_start: number
  selection_end: number
  user_id?: number
  user_name?: string
  created_at: string
  extractor?: string
  extractor_name?: string // Keep for backward compatibility
}

export interface ExtractorInfo {
  id: string
  name: string
  description: string
  cost_per_page: number
  support_tags: string[]
}

export interface ExtractorCategory {
  category: string
  extractors: ExtractorInfo[]
}

export interface ExtractorsResponse {
  pdf_extractors: ExtractorCategory[]
  image_extractors: ExtractorCategory[]
}

class PdfApiService {
  private getAuthHeaders(token: string) {
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    } as const
  }

  // Projects API
  async getProjects(token: string): Promise<Project[]> {
    const response = await fetch(`${API_BASE_URL}/projects`, {
      headers: this.getAuthHeaders(token),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch projects')
    }

    return response.json()
  }

  async createProject(project: ProjectCreateRequest, token: string): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/create-project`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(project),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to create project')
    }

    return response.json()
  }

  async getProject(projectUuid: string, token: string): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/projects/${projectUuid}`, {
      headers: this.getAuthHeaders(token),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch project')
    }

    return response.json()
  }

  async deleteProject(projectUuid: string, token: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/delete-project/${projectUuid}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to delete project')
    }
  }

  // Documents API
  async getProjectDocuments(
    projectUuid: string,
    token: string,
    page: number = 1,
    pageSize: number = 10,
    sortBy: DocumentSortFieldType = 'uploaded_at',
    sortDirection: SortDirectionType = 'desc'
  ): Promise<PaginatedDocumentsResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      sort_by: sortBy,
      sort_direction: sortDirection,
    })

    const response = await fetch(`${API_BASE_URL}/projects/${projectUuid}/documents?${params}`, {
      headers: this.getAuthHeaders(token),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch documents')
    }

    return response.json()
  }

  async getDocument(projectUuid: string, documentUuid: string, token: string): Promise<Document> {
    const response = await fetch(`${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}`, {
      headers: this.getAuthHeaders(token),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch document')
    }

    return response.json()
  }

  async deleteDocument(projectUuid: string, documentUuid: string, token: string): Promise<void> {
    const primary = await fetch(`${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
    if (primary.ok) return
    // Fallback to legacy route if backend doesn't expose the nested DELETE route
    if (primary.status === 405 || primary.status === 404) {
      const legacy = await fetch(`${API_BASE_URL}/delete-document/${documentUuid}`, {
        method: 'DELETE',
        headers: this.getAuthHeaders(token),
      })
      if (legacy.ok) return
      const errLegacy = await legacy.json().catch(() => ({}))
      throw new Error(errLegacy.detail || 'Failed to delete document')
    }
    const error = await primary.json().catch(() => ({}))
    throw new Error(error.detail || 'Failed to delete document')
  }

  // Extraction Jobs API
  async getDocumentExtractionJobs(
    projectUuid: string,
    documentUuid: string,
    token: string,
    filterByUser: boolean = false
  ): Promise<DocumentExtractionJob[]> {
    const url = `${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}/extraction-jobs${filterByUser ? '?filter_by_user=true' : ''}`
    const response = await fetch(url, {
      headers: this.getAuthHeaders(token),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch extraction jobs')
    }

    return response.json()
  }

  // Upload API - handles both single and multiple files
  async uploadDocuments(
    projectUuid: string,
    files: File[],
    selectedExtractors: string[],
    token: string,
    ownerName: string
  ): Promise<{ message: string; document_uuids: string[]; failed_uploads: Array<{ filename: string; error: string }> }> {
    const formData = new FormData()

    // Append all files
    files.forEach(file => {
      formData.append('files', file)
    })

    formData.append('selected_extractors', JSON.stringify(selectedExtractors))
    formData.append('owner_name', ownerName)

    const response = await fetch(`${API_BASE_URL}/projects/${projectUuid}/upload-multiple`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to upload documents')
    }

    return response.json()
  }

  // Extractors API
  async getExtractors(): Promise<ExtractorsResponse> {
    const response = await fetch(`${API_BASE_URL}/extractors`)

    if (!response.ok) {
      throw new Error('Failed to fetch extractors')
    }

    return response.json()
  }

  // Page Content API
  async getExtractionJobPages(
    projectUuid: string,
    documentUuid: string,
    jobUuid: string,
    token: string
  ): Promise<DocumentPageContent[]> {
    const response = await fetch(
      `${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}/extraction-jobs/${jobUuid}/pages`,
      {
        headers: this.getAuthHeaders(token),
      }
    )

    if (!response.ok) {
      throw new Error('Failed to fetch extraction job pages')
    }

    return response.json()
  }

  // Annotations API
  async createAnnotation(payload: AnnotationPayload, token: string): Promise<AnnotationResponse> {
    const response = await fetch(`${API_BASE_URL}/annotations`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to create annotation')
    }
    return response.json()
  }

  async getAnnotations(
    documentId: string,
    token: string,
    filters?: { extractionJobUuid?: string; pageNumber?: number }
  ): Promise<AnnotationResponse[]> {
    const url = new URL(`${API_BASE_URL}/annotations`)
    url.searchParams.set('documentId', documentId)
    if (filters?.extractionJobUuid) url.searchParams.set('extractionJobUuid', filters.extractionJobUuid)
    if (typeof filters?.pageNumber === 'number') url.searchParams.set('pageNumber', String(filters.pageNumber))
    const response = await fetch(url.toString(), {
      headers: this.getAuthHeaders(token),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to fetch annotations')
    }
    return response.json()
  }

  async deleteAnnotation(annotationUuid: string, token: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/annotations/${annotationUuid}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to delete annotation')
    }
  }

  // Feedback (Ratings) API
  async submitFeedback(
    projectUuid: string,
    documentUuid: string,
    payload: FeedbackRequest,
    token: string
  ): Promise<FeedbackResponse> {
    const response = await fetch(
      `${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}/feedback`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(token),
        body: JSON.stringify(payload),
      }
    )
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to submit feedback')
    }
    return response.json()
  }

  async getPageFeedback(
    projectUuid: string,
    documentUuid: string,
    pageNumber: number,
    token: string
  ): Promise<FeedbackResponse[]> {
    const response = await fetch(
      `${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}/pages/${pageNumber}/feedback`,
      {
        headers: this.getAuthHeaders(token),
      }
    )
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to fetch page feedback')
    }
    return response.json()
  }

  async getPageAverageRating(
    projectUuid: string,
    documentUuid: string,
    pageNumber: number,
    extractionJobUuid: string,
    token: string
  ): Promise<PageAverageRating> {
    const response = await fetch(
      `${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}/pages/${pageNumber}/average-rating?extraction_job_uuid=${extractionJobUuid}`,
      {
        headers: this.getAuthHeaders(token),
      }
    )
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to get page average rating')
    }
    return response.json()
  }

  // Retry extraction job
  async retryExtractionJob(
    projectUuid: string,
    documentUuid: string,
    jobUuid: string,
    token: string
  ): Promise<{ message: string; job_uuid: string; status: string }> {
    const response = await fetch(
      `${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}/extraction-jobs/${jobUuid}/retry`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(token),
      }
    )

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to retry extraction job')
    }

    return response.json()
  }

  // Rating breakdown API
  async getRatingBreakdown(
    projectUuid: string,
    documentUuid: string,
    jobUuid: string,
    token: string
  ): Promise<UserRatingBreakdown[]> {
    const response = await fetch(
      `${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}/extraction-jobs/${jobUuid}/rating-breakdown`,
      {
        headers: this.getAuthHeaders(token),
      }
    )

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to fetch rating breakdown')
    }

    return response.json()
  }

  // Annotations list API
  async getAnnotationsList(
    projectUuid: string,
    documentUuid: string,
    token: string,
    filters?: {
      extractorUuid?: string
      userId?: number
      pageNumber?: number
      search?: string
    }
  ): Promise<AnnotationListItem[]> {
    const params = new URLSearchParams()
    if (filters?.extractorUuid) params.set('extractor_uuid', filters.extractorUuid)
    if (filters?.userId !== undefined) params.set('user_id', filters.userId.toString())
    if (filters?.pageNumber !== undefined) params.set('page_number', filters.pageNumber.toString())
    if (filters?.search) params.set('search', filters.search)

    const url = `${API_BASE_URL}/projects/${projectUuid}/documents/${documentUuid}/annotations-list${
      params.toString() ? `?${params.toString()}` : ''
    }`

    const response = await fetch(url, {
      headers: this.getAuthHeaders(token),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Failed to fetch annotations list')
    }

    return response.json()
  }
}

export const pdfApi = new PdfApiService()

