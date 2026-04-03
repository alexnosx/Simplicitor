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
OLLAMA_POLL_INTERVAL_MS = 5000
OLLAMA_TIMEOUT_S = 60
SMALL_MODEL_PARAM_THRESHOLD = 7_000_000_000

# ── UI Limits ─────────────────────────────────────────────────────────────────
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 640
TOP_BAR_HEIGHT = 48
BORDER_RADIUS_PX = 4
MAX_PROMPT_CHARS = 2000
PROMPT_COMPLEXITY_THRESHOLD_CHARS = 500

# ── Styling keywords that trigger the small-model tip ─────────────────────────
STYLING_KEYWORDS = [
    "color", "colour", "font", "bold", "italic", "blue", "red", "green",
    "highlight", "header", "footer", "align", "center", "centre", "table",
    "border", "background", "dark", "light",
]

# ── File Types ────────────────────────────────────────────────────────────────
GENERATE_FILE_TYPES = ["Word (.docx)", "Excel (.xlsx)", "PowerPoint (.pptx)"]
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
