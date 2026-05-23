import logging
import os
import sys
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from notebooklm import NotebookLMClient
from notebooklm import (
    AudioFormat, AudioLength,
    VideoFormat, VideoStyle,
    InfographicOrientation, InfographicDetail,
)

# Configure logging to stderr (stdout is used for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

_client = None
_client_context = None

@asynccontextmanager
async def lifespan(_app):
    """Initialize NotebookLM client on server startup."""
    global _client, _client_context
    logger.info("Starting NotebookLM MCP server...")
    try:
        _client = await NotebookLMClient.from_storage()
        _client_context = await _client.__aenter__()
        logger.info("NotebookLM client initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize NotebookLM client: {e}")
        logger.error("Please run 'uv run notebooklm login' to authenticate.")
        raise
    finally:
        if _client:
            try:
                await _client.__aexit__(None, None, None)
                logger.info("NotebookLM client closed")
            except Exception as e:
                logger.error(f"Error closing client: {e}")

mcp = FastMCP("NotebookLM", lifespan=lifespan)

async def get_client():
    global _client
    if _client is None:
        raise RuntimeError("NotebookLM client not initialized. Please restart the server.")
    return _client

def _status_str(status: int) -> str:
    return {1: "processing", 2: "pending", 3: "completed", 4: "failed"}.get(status, "unknown")

def _default_download_path(filename: str) -> str:
    return os.path.expanduser(f"~/Downloads/{filename}")

# ─── Notebook management ──────────────────────────────────────────────────────

@mcp.tool()
async def list_notebooks():
    """List all notebooks in your NotebookLM account."""
    client = await get_client()
    notebooks = await client.notebooks.list()
    return [{"id": nb.id, "title": nb.title, "source_count": nb.sources_count} for nb in notebooks]

@mcp.tool()
async def create_notebook(title: str):
    """Create a new notebook with the given title."""
    client = await get_client()
    notebook = await client.notebooks.create(title)
    return {"id": notebook.id, "title": notebook.title}

# ─── Sources ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def add_source_url(notebook_id: str, url: str):
    """Add a website or YouTube URL as a source to a notebook."""
    client = await get_client()
    source = await client.sources.add_url(notebook_id, url)
    return {"id": source.id, "title": source.title}

@mcp.tool()
async def add_source_text(notebook_id: str, title: str, text: str):
    """Add raw text as a source to a notebook."""
    client = await get_client()
    source = await client.sources.add_text(notebook_id, title, text)
    return {"id": source.id, "title": source.title}

# ─── Chat ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def ask_notebook(notebook_id: str, question: str):
    """Ask a question based on the sources in a notebook."""
    client = await get_client()
    result = await client.chat.ask(notebook_id, question)
    return {"answer": result.text, "sources": [s.title for s in result.sources]}

@mcp.tool()
async def get_notebook_summary(notebook_id: str):
    """Get a comprehensive summary and key insights of a notebook."""
    client = await get_client()
    result = await client.chat.ask(
        notebook_id,
        "Please provide a comprehensive summary and key insights of this notebook."
    )
    return {"summary": result.text}

# ─── Artifact status ─────────────────────────────────────────────────────────

@mcp.tool()
async def list_artifacts(notebook_id: str):
    """
    List all generated artifacts for a notebook with their status.

    Status values: processing | pending | completed | failed
    Use this to check if a generation task is done before downloading.
    """
    client = await get_client()
    artifacts = await client.artifacts.list(notebook_id)
    return [
        {
            "id": a.id,
            "title": a.title,
            "kind": str(a.kind),
            "status": _status_str(a.status),
            "created_at": str(a.created_at) if a.created_at else None,
            "url": a.url,
        }
        for a in artifacts
    ]

# ─── Generate (with full params) ─────────────────────────────────────────────

@mcp.tool()
async def generate_audio_overview(
    notebook_id: str,
    instructions: str = "Create a deep dive podcast-style overview.",
    audio_format: str = "DEEP_DIVE",
    audio_length: str = "DEFAULT",
    language: str = "en",
):
    """
    Generate an Audio Overview (podcast) in NotebookLM.

    audio_format: DEEP_DIVE | BRIEF | CRITIQUE | DEBATE
    audio_length: SHORT | DEFAULT | LONG
    language: language code, e.g. "en", "zh"
    """
    client = await get_client()
    fmt = AudioFormat[audio_format.upper()]
    length = AudioLength[audio_length.upper()]
    status = await client.artifacts.generate_audio(
        notebook_id,
        instructions=instructions,
        audio_format=fmt,
        audio_length=length,
        language=language,
    )
    return {"task_id": status.task_id, "status": "Task started. Use list_artifacts to check progress, then download_audio when completed."}

@mcp.tool()
async def generate_video_overview(
    notebook_id: str,
    instructions: str = "Create an engaging video overview of these sources.",
    video_format: str = "EXPLAINER",
    video_style: str = "AUTO_SELECT",
    language: str = "en",
):
    """
    Generate a Video Overview in NotebookLM.

    video_format: EXPLAINER | BRIEF
    video_style: AUTO_SELECT | CLASSIC | WHITEBOARD | KAWAII | ANIME | WATERCOLOR | RETRO_PRINT | HERITAGE | PAPER_CRAFT
    language: language code, e.g. "en", "zh"
    """
    client = await get_client()
    fmt = VideoFormat[video_format.upper()]
    style = VideoStyle[video_style.upper()]
    status = await client.artifacts.generate_video(
        notebook_id,
        instructions=instructions,
        video_format=fmt,
        video_style=style,
        language=language,
    )
    return {"task_id": status.task_id, "status": "Task started. Use list_artifacts to check progress, then download_video when completed."}

@mcp.tool()
async def generate_slide_deck(notebook_id: str, instructions: str = "Create a comprehensive slide deck."):
    """Generate a Slide Deck (PowerPoint style) in NotebookLM."""
    client = await get_client()
    status = await client.artifacts.generate_slide_deck(notebook_id, instructions=instructions)
    return {"task_id": status.task_id, "status": "Task started. Use list_artifacts to check progress, then download_slide_deck when completed."}

@mcp.tool()
async def generate_mind_map(notebook_id: str):
    """Generate an interactive Mind Map in NotebookLM."""
    client = await get_client()
    result = await client.artifacts.generate_mind_map(notebook_id)
    return {"note_id": result.get("note_id"), "status": "Mind map generated and saved to notes."}

@mcp.tool()
async def generate_infographic(
    notebook_id: str,
    instructions: str = "Create an informative infographic.",
    orientation: str = "LANDSCAPE",
    detail_level: str = "STANDARD",
    language: str = "en",
):
    """
    Generate an Infographic in NotebookLM.

    orientation: LANDSCAPE | PORTRAIT | SQUARE
    detail_level: CONCISE | STANDARD | DETAILED
    language: language code, e.g. "en", "zh"
    """
    client = await get_client()
    ori = InfographicOrientation[orientation.upper()]
    detail = InfographicDetail[detail_level.upper()]
    status = await client.artifacts.generate_infographic(
        notebook_id,
        instructions=instructions,
        orientation=ori,
        detail_level=detail,
        language=language,
    )
    return {"task_id": status.task_id, "status": "Task started. Check NotebookLM studio."}

@mcp.tool()
async def generate_quiz(notebook_id: str, instructions: str = "Create a quiz based on these sources."):
    """Generate a Quiz in NotebookLM."""
    client = await get_client()
    status = await client.artifacts.generate_quiz(notebook_id, instructions=instructions)
    return {"task_id": status.task_id, "status": "Task started. Check NotebookLM studio."}

@mcp.tool()
async def generate_flashcards(notebook_id: str, instructions: str = "Create study flashcards."):
    """Generate Flashcards in NotebookLM."""
    client = await get_client()
    status = await client.artifacts.generate_flashcards(notebook_id, instructions=instructions)
    return {"task_id": status.task_id, "status": "Task started. Check NotebookLM studio."}

@mcp.tool()
async def generate_summary_report(notebook_id: str, instructions: str = "Create a briefing document."):
    """Generate a Summary Report (Briefing Doc) in NotebookLM."""
    client = await get_client()
    status = await client.artifacts.generate_report(notebook_id, custom_prompt=instructions)
    return {"task_id": status.task_id, "status": "Task started. Check NotebookLM studio."}

@mcp.tool()
async def generate_data_table(notebook_id: str, instructions: str = "Extract key data into a table."):
    """Generate a Data Table artifact in NotebookLM."""
    client = await get_client()
    status = await client.artifacts.generate_data_table(notebook_id, instructions=instructions)
    return {"task_id": status.task_id, "status": "Task started. Check NotebookLM studio."}

# ─── Download ────────────────────────────────────────────────────────────────

@mcp.tool()
async def download_audio(
    notebook_id: str,
    output_path: str = "",
    artifact_id: str = "",
):
    """
    Download a completed Audio Overview to a local file.

    output_path: full local path to save (default: ~/Downloads/<notebook_id>_audio.mp3)
    artifact_id: specific artifact ID to download (default: first completed audio)

    Run list_artifacts first to confirm status is 'completed'.
    """
    client = await get_client()
    path = output_path or _default_download_path(f"{notebook_id}_audio.mp3")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    saved = await client.artifacts.download_audio(
        notebook_id,
        output_path=path,
        artifact_id=artifact_id or None,
    )
    return {"saved_to": saved, "status": "Download complete."}

@mcp.tool()
async def download_video(
    notebook_id: str,
    output_path: str = "",
    artifact_id: str = "",
):
    """
    Download a completed Video Overview to a local file.

    output_path: full local path to save (default: ~/Downloads/<notebook_id>_video.mp4)
    artifact_id: specific artifact ID to download (default: first completed video)

    Run list_artifacts first to confirm status is 'completed'.
    """
    client = await get_client()
    path = output_path or _default_download_path(f"{notebook_id}_video.mp4")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    saved = await client.artifacts.download_video(
        notebook_id,
        output_path=path,
        artifact_id=artifact_id or None,
    )
    return {"saved_to": saved, "status": "Download complete."}

@mcp.tool()
async def download_slide_deck(
    notebook_id: str,
    output_path: str = "",
    artifact_id: str = "",
):
    """
    Download a completed Slide Deck to a local file.

    output_path: full local path to save (default: ~/Downloads/<notebook_id>_slides.pptx)
    artifact_id: specific artifact ID to download (default: first completed slide deck)

    Run list_artifacts first to confirm status is 'completed'.
    """
    client = await get_client()
    path = output_path or _default_download_path(f"{notebook_id}_slides.pptx")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    saved = await client.artifacts.download_slide_deck(
        notebook_id,
        output_path=path,
        artifact_id=artifact_id or None,
    )
    return {"saved_to": saved, "status": "Download complete."}

if __name__ == "__main__":
    mcp.run()
