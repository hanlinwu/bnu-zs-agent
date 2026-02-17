# Knowledge Base Hierarchy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the flat knowledge document system into a two-level hierarchy (Knowledge Base → Documents) with per-KB enable/disable controlling RAG retrieval.

**Architecture:** New `knowledge_bases` table with `kb_id` FK on `knowledge_documents`. New CRUD API for KBs. Frontend Knowledge.vue split into left panel (KB list) + right panel (existing doc table). RAG search JOINs through KB to filter disabled bases.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL, Vue 3 + Element Plus + TypeScript

---

### Task 1: Backend Model — KnowledgeBase

**Files:**
- Modify: `server/app/models/knowledge.py`

**Step 1: Add KnowledgeBase model and kb_id FK**

Add `KnowledgeBase` class and `kb_id` column to `KnowledgeDocument`:

```python
# Add to server/app/models/knowledge.py, BEFORE KnowledgeDocument class:

from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Boolean, text
# (update existing import to include Boolean)

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
```

Add to `KnowledgeDocument` class:

```python
    kb_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=True)
```

**Step 2: Add DB migration in main.py lifespan**

Add after existing migration block in `server/app/main.py` lifespan function (after the `review_records` migration):

```python
    # Ensure knowledge_bases table and kb_id column exist
    async with engine.begin() as conn:
        # Add kb_id column to knowledge_documents if missing
        await conn.execute(_text("""
            DO $$ BEGIN
                ALTER TABLE knowledge_documents ADD COLUMN kb_id UUID REFERENCES knowledge_bases(id);
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """))
```

**Step 3: Commit**

```
feat: add KnowledgeBase model and kb_id FK on KnowledgeDocument
```

---

### Task 2: Backend Seed — Default Knowledge Base

**Files:**
- Modify: `server/app/core/seed.py`

**Step 1: Add seed function for default KB**

Add at the end of `seed.py`:

```python
async def seed_default_knowledge_base():
    """Ensure a default knowledge base exists and all orphan documents are assigned to it."""
    from app.models.knowledge import KnowledgeBase, KnowledgeDocument

    session_factory = get_session_factory()
    async with session_factory() as db:
        # Check if any KB exists
        count = (await db.execute(select(func.count()).select_from(KnowledgeBase))).scalar() or 0
        if count == 0:
            # Create default KB
            default_kb = KnowledgeBase(
                name="默认知识库",
                description="系统默认知识库",
                enabled=True,
                sort_order=0,
            )
            db.add(default_kb)
            await db.flush()

            # Assign all orphan documents
            from sqlalchemy import update
            await db.execute(
                update(KnowledgeDocument)
                .where(KnowledgeDocument.kb_id.is_(None))
                .values(kb_id=default_kb.id)
            )
            await db.commit()
        else:
            # Still assign any orphan documents to first KB
            first_kb = (await db.execute(
                select(KnowledgeBase).order_by(KnowledgeBase.sort_order, KnowledgeBase.created_at).limit(1)
            )).scalar_one_or_none()
            if first_kb:
                orphan_count = (await db.execute(
                    select(func.count()).select_from(KnowledgeDocument)
                    .where(KnowledgeDocument.kb_id.is_(None))
                )).scalar() or 0
                if orphan_count > 0:
                    from sqlalchemy import update
                    await db.execute(
                        update(KnowledgeDocument)
                        .where(KnowledgeDocument.kb_id.is_(None))
                        .values(kb_id=first_kb.id)
                    )
                    await db.commit()
```

**Step 2: Call seed in main.py lifespan**

Add after `seed_review_workflows()` in `server/app/main.py`:

```python
    from app.core.seed import seed_roles_and_permissions, seed_calendar_periods, seed_model_config, seed_review_workflows, seed_default_knowledge_base
    # ... existing seed calls ...
    await seed_default_knowledge_base()
```

**Step 3: Commit**

```
feat: seed default knowledge base and assign orphan documents
```

---

### Task 3: Backend API — Knowledge Base CRUD

**Files:**
- Create: `server/app/api/v1/admin_knowledge_base.py`
- Modify: `server/app/api/router.py`

**Step 1: Create the KB CRUD endpoint file**

```python
"""Knowledge base (库) CRUD API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.knowledge import KnowledgeBase, KnowledgeDocument

router = APIRouter()


class KBCreateRequest(BaseModel):
    name: str
    description: str | None = None
    enabled: bool = True
    sort_order: int = 0


class KBUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    sort_order: int | None = None


@router.get("", dependencies=[Depends(require_permission("knowledge:read"))])
async def list_knowledge_bases(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """知识库列表（含文档数量统计）"""
    stmt = (
        select(KnowledgeBase)
        .order_by(KnowledgeBase.sort_order, KnowledgeBase.created_at)
    )
    result = await db.execute(stmt)
    kbs = result.scalars().all()

    items = []
    for kb in kbs:
        doc_count = (await db.execute(
            select(func.count()).select_from(KnowledgeDocument)
            .where(KnowledgeDocument.kb_id == kb.id)
        )).scalar() or 0
        items.append({
            "id": str(kb.id),
            "name": kb.name,
            "description": kb.description or "",
            "enabled": kb.enabled,
            "sort_order": kb.sort_order,
            "doc_count": doc_count,
            "created_at": kb.created_at.isoformat(),
            "updated_at": kb.updated_at.isoformat(),
        })

    return {"items": items}


@router.post("", dependencies=[Depends(require_permission("knowledge:create"))])
async def create_knowledge_base(
    body: KBCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建知识库"""
    kb = KnowledgeBase(
        name=body.name,
        description=body.description,
        enabled=body.enabled,
        sort_order=body.sort_order,
        created_by=admin.id,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return {
        "id": str(kb.id),
        "name": kb.name,
        "description": kb.description or "",
        "enabled": kb.enabled,
        "sort_order": kb.sort_order,
        "created_at": kb.created_at.isoformat(),
    }


@router.put("/{kb_id}", dependencies=[Depends(require_permission("knowledge:create"))])
async def update_knowledge_base(
    kb_id: str,
    body: KBUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑知识库"""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundError("知识库不存在")

    if body.name is not None:
        kb.name = body.name
    if body.description is not None:
        kb.description = body.description
    if body.enabled is not None:
        kb.enabled = body.enabled
    if body.sort_order is not None:
        kb.sort_order = body.sort_order
    kb.updated_at = datetime.now(timezone.utc)

    await db.commit()
    return {"success": True, "message": "知识库已更新"}


@router.delete("/{kb_id}", dependencies=[Depends(require_permission("knowledge:delete"))])
async def delete_knowledge_base(
    kb_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除知识库（仅允许删除空库）"""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundError("知识库不存在")

    doc_count = (await db.execute(
        select(func.count()).select_from(KnowledgeDocument)
        .where(KnowledgeDocument.kb_id == kb.id)
    )).scalar() or 0

    if doc_count > 0:
        raise BizError(code=400, message=f"该知识库下还有 {doc_count} 篇文档，请先移除或删除文档")

    await db.delete(kb)
    await db.commit()
    return {"success": True, "message": "知识库已删除"}
```

**Step 2: Register route in router.py**

Add import and registration in `server/app/api/router.py`:

```python
from app.api.v1 import admin_knowledge_base
# ...
api_router.include_router(admin_knowledge_base.router, prefix="/admin/knowledge-bases", tags=["知识库"])
```

**Step 3: Commit**

```
feat: add knowledge base CRUD API endpoints
```

---

### Task 4: Backend — Modify Document Endpoints for kb_id

**Files:**
- Modify: `server/app/api/v1/knowledge.py`
- Modify: `server/app/schemas/knowledge.py`

**Step 1: Add kb_id to upload endpoint**

In `server/app/api/v1/knowledge.py`, modify `upload_document` to accept `kb_id` as a Form field:

```python
from fastapi import APIRouter, BackgroundTasks, Depends, Query, UploadFile, File, Form

# Change upload_document signature to add kb_id:
async def upload_document(
    file: UploadFile = File(...),
    kb_id: str = Form(...),  # ADD THIS
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
```

And when creating the document:

```python
    doc = KnowledgeDocument(
        title=file.filename or "untitled",
        file_type=ext,
        file_path=file_path,
        file_hash=file_hash,
        status="pending",
        current_node="pending",
        uploaded_by=admin.id,
        kb_id=kb_id,  # ADD THIS
    )
```

**Step 2: Add kb_id filter to list_documents**

In `list_documents`, add `kb_id` parameter:

```python
async def list_documents(
    status: str | None = None,
    kb_id: str | None = None,  # ADD THIS
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100, alias="pageSize"),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
```

Add filtering:

```python
    if kb_id:
        stmt = stmt.where(KnowledgeDocument.kb_id == kb_id)
        count_stmt = count_stmt.where(KnowledgeDocument.kb_id == kb_id)
```

**Step 3: Add kbId to response schema**

In `server/app/schemas/knowledge.py`, add to `KnowledgeDocResponse`:

```python
    kbId: str | None = None
```

In `_doc_to_response` in `knowledge.py`, add:

```python
    kbId=str(doc.kb_id) if doc.kb_id else None,
```

**Step 4: Commit**

```
feat: add kb_id to document upload, listing, and response
```

---

### Task 5: Backend — Update RAG Search

**Files:**
- Modify: `server/app/services/knowledge_service.py`

**Step 1: Update search SQL to filter by KB enabled**

Replace the SQL query in `search()`:

```python
    stmt = sa_text("""
        SELECT
            kc.id as chunk_id,
            kc.document_id,
            kd.title as document_title,
            kc.content,
            1 - (kc.embedding <=> CAST(:query_vec AS vector)) as score
        FROM knowledge_chunks kc
        JOIN knowledge_documents kd ON kd.id = kc.document_id
        JOIN knowledge_bases kb ON kb.id = kd.kb_id
        WHERE kd.status = 'approved'
          AND kb.enabled = true
          AND kc.embedding IS NOT NULL
        ORDER BY kc.embedding <=> CAST(:query_vec AS vector)
        LIMIT :top_k
    """)
```

**Step 2: Commit**

```
feat: filter disabled knowledge bases from RAG search
```

---

### Task 6: Frontend Types & API — Knowledge Base

**Files:**
- Modify: `client/src/types/knowledge.ts`
- Create: `client/src/api/admin/knowledgeBase.ts`
- Modify: `client/src/api/admin/knowledge.ts`

**Step 1: Add KnowledgeBase type**

Add to `client/src/types/knowledge.ts`:

```typescript
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
```

Add `kbId` to `KnowledgeDocument`:

```typescript
  kbId?: string
```

**Step 2: Create knowledgeBase.ts API client**

```typescript
import request from '../request'
import type { KnowledgeBase } from '@/types/knowledge'

export const getKnowledgeBases = () =>
  request.get<{ items: KnowledgeBase[] }>('/admin/knowledge-bases')

export const createKnowledgeBase = (data: { name: string; description?: string; enabled?: boolean; sort_order?: number }) =>
  request.post<KnowledgeBase>('/admin/knowledge-bases', data)

export const updateKnowledgeBase = (id: string, data: { name?: string; description?: string; enabled?: boolean; sort_order?: number }) =>
  request.put(`/admin/knowledge-bases/${id}`, data)

export const deleteKnowledgeBase = (id: string) =>
  request.delete(`/admin/knowledge-bases/${id}`)
```

**Step 3: Update knowledge.ts to support kb_id**

Modify `getDocuments` params type:

```typescript
export const getDocuments = (params: { page: number; pageSize: number; status?: string; kb_id?: string }) =>
  request.get<PaginatedResult<KnowledgeDocument>>('/admin/knowledge', { params })
```

**Step 4: Commit**

```
feat: add frontend types and API client for knowledge bases
```

---

### Task 7: Frontend — Rewrite Knowledge.vue with Left-Right Layout

**Files:**
- Modify: `client/src/views/admin/Knowledge.vue`

**Step 1: Rewrite Knowledge.vue**

This is the largest frontend change. The page becomes a split layout:

- **Left panel (280px):** KB list with create/edit/delete, enable toggle, selection highlight
- **Right panel:** Existing document table scoped to selected KB

Key changes to script:
- Import `* as kbApi from '@/api/admin/knowledgeBase'`
- Add state: `knowledgeBases`, `selectedKbId`, `kbDialogVisible`, `kbForm`, `kbEditing`
- Add `fetchKnowledgeBases()` — load KB list on mount
- Add `selectKb(kbId)` — set selectedKbId, reload documents
- Add `handleCreateKb()`, `handleUpdateKb()`, `handleDeleteKb()`, `handleToggleKbEnabled()`
- Modify `fetchDocuments()` — pass `kb_id: selectedKbId.value` to API
- Modify upload — send `kb_id` as FormData field
- Auto-select first KB on mount

Key changes to template:
- Wrap in `<div class="knowledge-page">` with flexbox
- Left panel: `.kb-sidebar` with KB list items
- Right panel: `.kb-content` with existing table (unchanged logic)
- Upload dialog: add hidden `kb_id` or use `data` prop on el-upload
- KB edit dialog: name, description, sort_order fields

Key changes to style:
- `.knowledge-page` becomes `display: flex; gap: 20px;`
- `.kb-sidebar` gets `width: 280px; flex-shrink: 0;`
- `.kb-content` gets `flex: 1; min-width: 0;`

**Step 2: Commit**

```
feat: rewrite Knowledge.vue with left-right KB/document layout
```

---

### Task 8: Frontend — Update Upload Dialog for kb_id

**Files:**
- Modify: `client/src/views/admin/Knowledge.vue` (continued from Task 7)

**Step 1: Pass kb_id in upload**

The `el-upload` component uses `action` URL + `data` prop to send additional form fields:

```vue
<el-upload
  drag
  action="/api/v1/admin/knowledge/upload"
  :headers="uploadHeaders"
  :data="{ kb_id: selectedKbId }"
  accept=".pdf,.docx,.txt,.md"
  :before-upload="beforeUpload"
  :on-success="handleUploadSuccess"
  :on-error="handleUploadError"
  :show-file-list="true"
  :limit="5"
>
```

**Step 2: Commit**

```
feat: pass kb_id when uploading documents
```

---

### Task 9: Verify — Start Server & Check

**Step 1: Start the backend server**

```bash
cd /workspace/server && source .venv/bin/activate && uvicorn app.main:app --reload --port 8001
```

Verify:
- Server starts without errors
- `knowledge_bases` table is created
- Default KB is seeded
- Orphan documents assigned to default KB

**Step 2: Test KB CRUD API**

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/admin/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# List KBs
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/v1/admin/knowledge-bases | python3 -m json.tool

# Create KB
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' http://localhost:8001/api/v1/admin/knowledge-bases -d '{"name":"招生政策","description":"各类招生政策文件"}' | python3 -m json.tool

# List documents with kb_id filter
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8001/api/v1/admin/knowledge?kb_id=<KB_ID>" | python3 -m json.tool
```

**Step 3: Run TypeScript check**

```bash
cd /workspace/client && npx vue-tsc --noEmit
```

**Step 4: Commit (if any fixes needed)**

```
fix: address issues found during verification
```

---

## Summary of Files

| # | Action | File |
|---|--------|------|
| 1 | Modify | `server/app/models/knowledge.py` — add `KnowledgeBase` model, `kb_id` FK |
| 2 | Modify | `server/app/main.py` — add migration for `kb_id` column |
| 3 | Modify | `server/app/core/seed.py` — seed default KB, assign orphans |
| 4 | Create | `server/app/api/v1/admin_knowledge_base.py` — KB CRUD |
| 5 | Modify | `server/app/api/router.py` — register KB route |
| 6 | Modify | `server/app/api/v1/knowledge.py` — add `kb_id` to upload/list |
| 7 | Modify | `server/app/schemas/knowledge.py` — add `kbId` to response |
| 8 | Modify | `server/app/services/knowledge_service.py` — JOIN KB in search |
| 9 | Modify | `client/src/types/knowledge.ts` — add `KnowledgeBase` type, `kbId` field |
| 10 | Create | `client/src/api/admin/knowledgeBase.ts` — KB API client |
| 11 | Modify | `client/src/api/admin/knowledge.ts` — add `kb_id` param |
| 12 | Modify | `client/src/views/admin/Knowledge.vue` — full rewrite with split layout |
