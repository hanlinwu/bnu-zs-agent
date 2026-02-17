/** 知识库 */
export interface KnowledgeBase {
  id: string
  name: string
  description: string
  enabled: boolean
  sort_order: number
  doc_count: number
  created_at: string
  updated_at: string
}

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
  currentNode: string
  uploaderId: string
  uploaderName: string
  reviewerId?: string
  reviewerName?: string
  reviewNote?: string
  chunkCount: number
  kbId?: string
  effectiveAt?: string
  expiredAt?: string
  createdAt: string
  updatedAt: string
}

/** 知识库切片 */
export interface KnowledgeChunk {
  id: string
  chunkIndex: number
  content: string
  tokenCount: number
}
