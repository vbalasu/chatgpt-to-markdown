# ChatGPT to Markdown

A Claude Code skill that converts ChatGPT share links into clean Markdown documents.

## Usage

### Standalone (no Claude Code needed)

```bash
# Pass URL as argument
python convert.py https://chatgpt.com/share/<id>

# Specify output filename
python convert.py https://chatgpt.com/share/<id> output.md

# Interactive — prompts for URL
python convert.py
```

The output filename is auto-generated from the conversation title (e.g., `join-types-in-sql.md`).

### As a Claude Code skill

```bash
/chatgpt-to-markdown https://chatgpt.com/share/<id>
```

## How It Works

1. Uses Playwright to fetch the ChatGPT share page (renders JavaScript)
2. Parses the HTML to extract conversation turns
3. Converts assistant responses (headings, lists, code blocks, formatting) to Markdown
4. Outputs a clean `.md` file

## Requirements

- Python 3
- Playwright (`pip install playwright && playwright install`)

## Project Structure

```
chatgpt-to-markdown/
├── SKILL.md                    # Skill definition
├── scripts/
│   └── fetch_chatgpt.py       # Playwright-based page fetcher
├── references/
│   └── selectors.md           # CSS selector reference
└── assets/
.claude/
└── commands/
    └── chatgpt-to-markdown.md  # Slash command definition
example.md                      # Sample output
```

## Example

See [example.md](example.md) for a sample converted conversation.
