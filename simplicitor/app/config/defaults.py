# simplicitor/app/config/defaults.py

# ── Colors ────────────────────────────────────────────────────────────────────
BACKGROUND_COLOR = "#FAFAFA"
PANEL_BG_COLOR = "#F5F5F5"
PRIMARY_ACCENT_COLOR = "#2563EB"
BODY_TEXT_COLOR = "#1E1E1E"
SUCCESS_COLOR = "#16A34A"
ERROR_COLOR = "#DC2626"
DISABLED_COLOR = "#9CA3AF"
BORDER_COLOR = "#E5E7EB"
INFO_BANNER_BG_COLOR = "#EFF6FF"
WHITE = "#FFFFFF"
HOVER_ACCENT_COLOR = "#1D4ED8"    # darker blue for button hover
BORDER_HOVER_COLOR = "#D1D5DB"    # darker grey for border hover

# ── Typography ────────────────────────────────────────────────────────────────
APP_FONT_FAMILY = "Segoe UI"
FONT_SIZE_BODY_PT = 10
FONT_SIZE_HEADING_PT = 11

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TAGS_ENDPOINT = "/api/tags"
OLLAMA_PS_ENDPOINT = "/api/ps"
OLLAMA_SHOW_ENDPOINT = "/api/show"
OLLAMA_GENERATE_ENDPOINT = "/api/generate"
OLLAMA_CHAT_ENDPOINT = "/api/chat"
OLLAMA_CHAT_COMPLETIONS_ENDPOINT = "/v1/chat/completions"
OLLAMA_POLL_INTERVAL_MS = 5000
OLLAMA_POLL_TIMEOUT_S = 3            # connectivity probe + poll-loop discovery calls; must stay under the poll interval
OLLAMA_TIMEOUT_S = 60
OLLAMA_MANIPULATION_TIMEOUT_S = 120  # manipulation sends file content → needs more time
OLLAMA_TEMPLATE_TIMEOUT_S = 180      # templated path: heavier prompt + larger expected output (slow local models)
OLLAMA_REPAIR_MAX_TOKENS = 8192      # max_tokens budget for templated attempt 1 and truncation-bump repair
SMALL_MODEL_PARAM_THRESHOLD = 7_000_000_000

# ── PowerPoint layout indices (standard Blank template) ──────────────────────
PPTX_LAYOUT_TITLE_SLIDE = 0       # "Title Slide" layout
PPTX_LAYOUT_TITLE_CONTENT = 1     # "Title and Content" layout
PPTX_LAYOUT_SECTION_HEADER = 2    # "Section Header" layout

# ── UI Limits ─────────────────────────────────────────────────────────────────
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 640
TOP_BAR_HEIGHT = 48
BORDER_RADIUS_PX = 4
MAX_PROMPT_CHARS = 2000

# Maximum characters of file content sent to the LLM (larger files are truncated)
MAX_MANIPULATION_CHARS = 50_000
# Approximate token limit for LLM input (word_count * 1.3 heuristic); content beyond this is cut
MANIPULATION_TOKEN_LIMIT = 2000
PROMPT_COMPLEXITY_THRESHOLD_CHARS = 500

# ── Styling keywords that trigger the small-model tip ─────────────────────────
STYLING_KEYWORDS = [
    "color", "colour", "font", "bold", "italic", "blue", "red", "green",
    "highlight", "header", "footer", "align", "center", "centre", "table",
    "border", "background", "dark", "light",
]

# ── Out-of-scope keywords for manipulation (visual/styling requests) ───────────
# Prompts matching these keywords against .pptx/.docx files are rejected before
# any file I/O because the pipeline can only modify text and structure in v1.
MANIPULATION_OUT_OF_SCOPE_KEYWORDS = [
    "theme", "color", "colour", "style", "font", "layout",
    "background", "design", "template", "image", "picture",
    "logo", "icon", "shape", "border", "animation", "transition",
]
# File types where visual changes are commonly requested but unsupported
MANIPULATION_VISUAL_EXTENSIONS = {".pptx", ".docx"}

# ── File Types ────────────────────────────────────────────────────────────────
GENERATE_FILE_TYPES = ["Word (.docx)", "Excel (.xlsx)", "PowerPoint (.pptx)"]
# The template engine fills PowerPoint layouts only; the "From template" button is
# enabled only when this file type is selected.
TEMPLATE_FILE_TYPE = "PowerPoint (.pptx)"
EDIT_EXTENSIONS = [".docx", ".xlsx", ".pptx", ".txt", ".pdf"]
EDIT_FILE_FILTER = "Supported Files (*.docx *.xlsx *.pptx *.txt *.pdf)"

# ── App Identity ──────────────────────────────────────────────────────────────
APP_NAME = "Simplicitor"
APP_DATA_SUBDIR = "Simplicitor"

# ── Default subdirectory names (under Documents/Simplicitor/) ─────────────────
DEFAULT_GENERATED_SUBDIR = "Generated"
DEFAULT_UPLOADS_SUBDIR = "Uploads"
DEFAULT_BACKUPS_SUBDIR = "Backups"
DEFAULT_LOGS_SUBDIR = "Logs"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE_PREFIX = "simplicitor_"
LOG_BACKUP_COUNT = 7

# ── Backup ────────────────────────────────────────────────────────────────────
BACKUP_SUFFIX = "_backup"

# ── Prompt placeholder text ───────────────────────────────────────────────────
PROMPT_PLACEHOLDERS = {
    "Word (.docx)": (
        "Describe the document you need, e.g.: Create a project status report "
        "with sections for timeline, risks, and next steps"
    ),
    "Excel (.xlsx)": (
        "Describe the spreadsheet you need, e.g.: Create a monthly budget tracker "
        "with columns for category, planned amount, actual amount, and difference"
    ),
    "PowerPoint (.pptx)": (
        "Describe the presentation you need, e.g.: Create a 5-slide pitch deck "
        "about our new product launch"
    ),
}

EDIT_PROMPT_PLACEHOLDERS = {
    ".docx": "What would you like to change? e.g.: Rewrite the executive summary to be more concise",
    ".xlsx": "What would you like to change? e.g.: Add a totals row and highlight cells where values exceed the budget",
    ".pptx": "What would you like to change? e.g.: Make the title slide dark blue with white text",
    ".txt": "What would you like to change? e.g.: Summarize this text into three bullet points",
    ".pdf": (
        "What would you like to extract? e.g.: Summarize the key findings from this report "
        "into bullet points (output will be saved as .docx or .txt)"
    ),
    "default": "Describe the change you want to make to this file",
}

FILE_TYPE_EXTENSIONS = {
    "Word (.docx)": ".docx",
    "Excel (.xlsx)": ".xlsx",
    "PowerPoint (.pptx)": ".pptx",
}
