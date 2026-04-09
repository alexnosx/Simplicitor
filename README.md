# Simplicitor

Generate and edit Word, Excel, and PowerPoint files using plain English — powered by a locally running AI.

No cloud. No subscription. No data leaves your machine.

## Requirements

- **Windows 10 or 11** (64-bit)
- **[Ollama](https://ollama.com)** installed and running on your machine
- At least one language model loaded in Ollama (see recommendations below)

## Installation

1. Download `Simplicitor.exe` from the [Releases](../../releases) page
2. Double-click `Simplicitor.exe` — no installation or Python required

## Recommended Models

For best results use a model with **7 billion parameters or more**:

| Model | Download size | Ollama command |
|---|---|---|
| Qwen3 8B | ~5 GB | `ollama pull qwen3:8b` |
| Llama 3.1 8B | ~4.7 GB | `ollama pull llama3.1:8b` |
| Mistral 7B | ~4 GB | `ollama pull mistral:7b` |

Smaller models work for simple requests but may struggle with complex documents.

## Quick Start

### 1. Start Ollama

Open a terminal (Win+R → `cmd`) and run:

```
ollama serve
```

Then in another terminal, load your model:

```
ollama run qwen3:8b
```

### 2. Launch Simplicitor

Double-click `Simplicitor.exe`. The status dot in the top bar turns **green** when the AI is ready.

### Create a new document

1. Select a file type: **Word**, **Excel**, or **PowerPoint**
2. Choose where to save it (defaults to `Documents\Simplicitor\Generated`)
3. Describe what you need in the text box
4. Click **Generate** — the file is saved automatically and an **Open file** button appears

### Edit an existing document

1. Drag a `.docx`, `.xlsx`, `.pptx`, `.txt`, or `.pdf` file into the Edit panel (or click to browse)
2. Describe the change you want
3. Click **Save** — a backup of the original is created automatically in `Documents\Simplicitor\Backups`

## Troubleshooting

**"AI engine not connected" (red indicator)**
- Make sure Ollama is running: open a terminal and run `ollama serve`
- Click the **Retry** button in the app

**Generation produces empty or garbled output**
- Try a shorter, simpler prompt
- Use a larger model (7B+ recommended)
- Check the logs: Settings → View Logs Folder

**"Cannot create the output folder" error**
- Open Settings (⚙ gear icon) and verify the "Generated files" path is valid
- Make sure you have write permission to that folder

**The generated file looks wrong (missing formatting, wrong structure)**
- The AI controls content; Simplicitor handles formatting
- Try adding more detail to your prompt
- Upgrade to a larger model

## Settings

Click the **⚙** gear icon (top right) to configure:

| Setting | Default location |
|---|---|
| Generated files | `Documents\Simplicitor\Generated` |
| Uploaded files | `Documents\Simplicitor\Uploads` |
| Backups | `Documents\Simplicitor\Backups` |
| Logs | `Documents\Simplicitor\Logs` |

Click **View Logs Folder** to open the log directory in Explorer.
Click **Reset to Defaults** to restore all paths to their defaults.

## Building from Source

Requirements: Python 3.11+, Git

```bat
git clone <repo-url>
cd Simplicitor
pip install -r requirements.txt
pip install -r requirements-build.txt
python resources/create_icon.py
python build.py
```

The compiled executable will be at `dist\Simplicitor.exe`.

## Privacy

Simplicitor sends your prompts only to the Ollama instance running on your own machine. No data is sent to any external server. Log files contain operation metadata (timestamps, file types, success/error status) but never file content or prompt text.
