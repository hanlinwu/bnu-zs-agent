"""Meilisearch client wrapper — indexing and search operations."""

import hashlib
import logging
from meilisearch_python_sdk import AsyncClient
from config import settings

logger = logging.getLogger(__name__)


def url_to_doc_id(url: str) -> str:
    """Deterministic document ID from URL for dedup on re-crawl."""
    return hashlib.sha256(url.strip().encode()).hexdigest()[:24]


class MeiliSearchService:
    def __init__(self):
        self.url = settings.MEILISEARCH_URL
        self.api_key = settings.MEILISEARCH_API_KEY or None
        self.index_name = settings.CRAWL_INDEX_NAME
        self._client: AsyncClient | None = None

    @property
    def client(self) -> AsyncClient:
        if self._client is None:
            self._client = AsyncClient(self.url, self.api_key)
        return self._client

    async def ensure_index(self):
        """Create index and configure attributes if not already set up."""
        try:
            await self.client.create_index(self.index_name, primary_key="id")
        except Exception:
            pass  # index already exists

        index = self.client.index(self.index_name)
        await index.update_searchable_attributes(["title", "content", "url"])
        await index.update_filterable_attributes(["domain", "crawled_at"])
        await index.update_sortable_attributes(["crawled_at"])
        logger.info("Meilisearch index '%s' ready", self.index_name)

    async def index_page(self, doc: dict):
        """Add or update a single page document.

        doc should have: id, url, title, content, domain, crawled_at
        """
        index = self.client.index(self.index_name)
        await index.add_documents([doc])

    async def index_pages(self, docs: list[dict]):
        """Batch-index multiple page documents."""
        if not docs:
            return
        index = self.client.index(self.index_name)
        await index.add_documents(docs)

    async def search(
        self,
        query: str,
        domain: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Full-text search with optional domain filter."""
        index = self.client.index(self.index_name)
        filter_expr = f'domain = "{domain}"' if domain else None
        result = await index.search(
            query,
            filter=filter_expr,
            offset=(page - 1) * page_size,
            limit=page_size,
            attributes_to_crop=["content"],
            crop_length=200,
            show_ranking_score=True,
        )
        return {
            "hits": [
                {
                    "id": h.get("id", ""),
                    "url": h.get("url", ""),
                    "title": h.get("title", ""),
                    "content_snippet": h.get("_formatted", {}).get("content", h.get("content", ""))[:300],
                    "domain": h.get("domain", ""),
                    "crawled_at": h.get("crawled_at", ""),
                    "score": h.get("_rankingScore"),
                }
                for h in result.hits
            ],
            "total": result.estimated_total_hits or 0,
            "query": query,
            "page": page,
            "page_size": page_size,
        }

    async def delete_by_domain(self, domain: str):
        """Delete all documents for a domain."""
        index = self.client.index(self.index_name)
        await index.delete_documents_by_filter(f'domain = "{domain}"')
        logger.info("Deleted all documents for domain: %s", domain)

    async def get_stats(self) -> dict:
        """Return index stats."""
        index = self.client.index(self.index_name)
        stats = await index.get_stats()
        return {"number_of_documents": stats.number_of_documents}


# Singleton
meili_service = MeiliSearchService()
