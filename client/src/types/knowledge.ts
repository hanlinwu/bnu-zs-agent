/** 文档状态 */
export type DocumentStatus = 'pending' | 'reviewing' | 'approved' | 'rejected' | 'processing' | 'active' | 'archived'

/** 文件类型 */
export type DocumentFileType = 'pdf' | 'docx' | 'txt' | 'md'

/** 知识库文档 */
export interface KnowledgeDocument {
  id: string
  title: string
  fileType: DocumentFileType
  fileUrl: string
  fileHash: string
  fileSize: number
  status: DocumentStatus
  uploaderId: string
  uploaderName: string
  reviewerId?: string
  reviewerName?: string
  reviewNote?: string
  chunkCount: number
  effectiveAt?: string
  expiredAt?: string
  createdAt: string
  updatedAt: string
}

/** 知识库切片 */
export interface KnowledgeChunk {
  id: string
  documentId: string
  content: string
  embedding?: number[]
  tokenCount: number
  index: number
  metadata: Record<string, unknown>
  createdAt: string
}
