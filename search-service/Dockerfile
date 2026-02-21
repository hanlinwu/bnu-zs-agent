FROM python:3.11-slim

# System deps for Playwright (Crawl4AI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Use a fixed browser cache path so runtime user can always find binaries.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install Chromium binary required by Crawl4AI/Playwright.
RUN playwright install --with-deps chromium

# Keep Crawl4AI post-install setup.
RUN crawl4ai-setup

COPY . .

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
