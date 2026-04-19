#!/usr/bin/env python3
"""Convert a ChatGPT share link to a clean Markdown document.

Usage:
    python convert.py <url> [output.md]
    python convert.py                    # prompts for URL interactively
"""

import asyncio
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. Fetch HTML via Playwright
# ---------------------------------------------------------------------------

async def fetch_html(url: str) -> str:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        try:
            print(f"Fetching {url} ...", file=sys.stderr)
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                await page.wait_for_selector(
                    "[data-message-author-role]", timeout=30000
                )
            except Exception:
                print("Warning: timed out waiting for message selectors.",
                      file=sys.stderr)
            await asyncio.sleep(5)
            return await page.content()
        finally:
            await browser.close()


# ---------------------------------------------------------------------------
# 2. Split HTML into per-message fragments
# ---------------------------------------------------------------------------

def extract_messages(html: str) -> list[dict]:
    pattern = r'data-message-author-role="(user|assistant)"'
    matches = list(re.finditer(pattern, html))
    messages = []
    for i, m in enumerate(matches):
        role = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        messages.append({"role": role, "html": html[start:end]})
    return messages


# ---------------------------------------------------------------------------
# 3. HTML → Markdown converter
# ---------------------------------------------------------------------------

class _HtmlToMarkdown(HTMLParser):
    """Convert a ChatGPT message HTML fragment to Markdown.

    ChatGPT's current (2026) share-page HTML uses:
    - <pre> containing nested <div>s with a CodeMirror viewer (no <code> tag).
      The language label sits in a div with class containing "font-medium".
      Code lines are <span>s separated by <br>.
    - <li> containing <p> children.
    - Standard <table>/<thead>/<th>/<td> for tables.
    """

    SKIP_TAGS = {"button", "svg", "path", "style", "script"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

        # code-block state
        self.in_pre = False
        self.in_code_block = False       # inside the cm-content div
        self.code_lang: str | None = None
        self.found_lang_label = False     # grabbed the language label
        self.pre_depth = 0               # div nesting depth inside <pre>

        # list state
        self.in_li = False
        self.li_has_content = False
        self.ol_counter: list[int] = []

        # table state
        self.current_row_cols = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return

        cls = dict(attrs).get("class", "")

        # ---- code blocks (inside <pre>) ----
        if tag == "pre":
            self.in_pre = True
            self.pre_depth = 0
            self.code_lang = None
            self.found_lang_label = False
            self.in_code_block = False
            return

        if self.in_pre:
            if tag == "div":
                self.pre_depth += 1
                # The CodeMirror content div
                if "cm-content" in cls:
                    lang = self.code_lang or ""
                    self.parts.append(f"\n```{lang}\n")
                    self.in_code_block = True
                return
            if tag == "br" and self.in_code_block:
                self.parts.append("\n")
                return
            if tag == "span":
                # Language label is in a span/div with "font-medium" before cm-content
                if not self.found_lang_label and "font-medium" in cls:
                    pass  # text handler will grab the label
                return
            return  # ignore other tags inside <pre>

        # ---- code (outside <pre>) = inline code ----
        if tag == "code":
            lang = re.search(r"language-(\S+)", cls)
            if lang:
                self.parts.append(f"\n```{lang.group(1)}\n")
                self.in_code_block = True
            else:
                self.parts.append("`")
            return

        if self.in_code_block:
            return

        # ---- block elements ----
        if tag == "p":
            if not self.in_li or self.li_has_content:
                self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "ol":
            self.ol_counter.append(0)
        elif tag == "li":
            self.in_li = True
            self.li_has_content = False
            if self.ol_counter:
                self.ol_counter[-1] += 1
                self.parts.append(f"\n{self.ol_counter[-1]}. ")
            else:
                self.parts.append("\n- ")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.parts.append("\n\n" + "#" * level + " ")
        elif tag in ("strong", "b"):
            self.parts.append("**")
        elif tag in ("em", "i"):
            self.parts.append("*")
        elif tag == "table":
            self.parts.append("\n\n")
        elif tag == "tr":
            self.current_row_cols = 0
        elif tag in ("th", "td"):
            self.parts.append("| ")
            self.current_row_cols += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return

        if tag == "pre":
            if self.in_code_block:
                self.parts.append("\n```\n")
                self.in_code_block = False
            self.in_pre = False
            return

        if self.in_pre:
            if tag == "div":
                self.pre_depth -= 1
            return

        if tag == "code":
            if self.in_code_block:
                self.parts.append("\n```\n")
                self.in_code_block = False
            else:
                self.parts.append("`")
            return

        if self.in_code_block:
            return

        if tag in ("strong", "b"):
            self.parts.append("**")
        elif tag in ("em", "i"):
            self.parts.append("*")
        elif tag == "ol":
            if self.ol_counter:
                self.ol_counter.pop()
        elif tag == "li":
            self.in_li = False
            self.li_has_content = False
        elif tag in ("th", "td"):
            self.parts.append(" ")
        elif tag == "tr":
            self.parts.append("|\n")
        elif tag == "thead":
            cols = self.current_row_cols
            if cols > 0:
                self.parts.append(
                    "|" + "|".join(" --- " for _ in range(cols)) + "|\n"
                )

    def handle_data(self, data):
        if self.skip_depth:
            return

        # Inside <pre> but before cm-content: grab the language label
        if self.in_pre and not self.in_code_block:
            stripped = data.strip()
            if stripped and not self.found_lang_label:
                # The first non-empty text inside <pre> is the language label
                self.code_lang = stripped.lower()
                self.found_lang_label = True
            return

        if self.in_li:
            if data.strip():
                self.li_has_content = True
            elif not self.li_has_content:
                return  # suppress whitespace before first content in <li>

        self.parts.append(data)

    def get_markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_markdown(html_fragment: str) -> str:
    parser = _HtmlToMarkdown()
    parser.feed(html_fragment)
    return parser.get_markdown()


# ---------------------------------------------------------------------------
# 4. Clean up ChatGPT UI noise
# ---------------------------------------------------------------------------

_NOISE_PATTERNS = [
    r"\*\]:pointer-events-auto[^\n]*",
    r"\[content-visibility[^\n]*",
    r"^Copy\s*$",
    r"^\s*Edit\s*$",
    r"Thought for .*?seconds?",
    r"^#{1,6}\s*(ChatGPT said|You said):?\s*$",
    r'^message-id="[^"]*"[^>]*>',
    r'^data-message-id="[^"]*"[^>]*>',
    r'^data-turn-start-message="[^"]*"[^>]*>',
    r"ChatGPT is AI and can make mistakes.*$",
]


def clean_text(text: str) -> str:
    for pat in _NOISE_PATTERNS:
        text = re.sub(pat, "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# 5. Extract title
# ---------------------------------------------------------------------------

def extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL)
    if m:
        title = m.group(1).strip()
        title = re.sub(r"\s*[\|–—-]\s*ChatGPT\s*$", "", title)
        if title and title.lower() != "chatgpt":
            return title
    return "ChatGPT Conversation"


# ---------------------------------------------------------------------------
# 6. Assemble final Markdown
# ---------------------------------------------------------------------------

def build_markdown(title: str, messages: list[dict]) -> str:
    lines = [f"# {title}\n"]

    # Merge consecutive assistant messages (thinking + response)
    merged: list[dict] = []
    for msg in messages:
        if (merged
                and merged[-1]["role"] == "assistant"
                and msg["role"] == "assistant"):
            merged[-1]["md"] += "\n\n" + msg["md"]
        else:
            merged.append({**msg})

    for msg in merged:
        lines.append("\n---\n")
        if msg["role"] == "user":
            lines.append(f"\n**User:** {msg['md']}\n")
        else:
            lines.append(f"\n**ChatGPT:**\n\n{msg['md']}\n")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) >= 2 and sys.argv[1].startswith("http"):
        url = sys.argv[1]
    else:
        url = input("Paste a ChatGPT share URL: ").strip()

    if not re.match(r"https?://chatgpt\.com/share/", url):
        print("Error: URL must start with https://chatgpt.com/share/",
              file=sys.stderr)
        sys.exit(1)

    output_path = sys.argv[2] if len(sys.argv) >= 3 else None

    html = asyncio.run(fetch_html(url))

    title = extract_title(html)
    raw_messages = extract_messages(html)

    if not raw_messages:
        print("Error: no messages found on the page.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(raw_messages)} messages.", file=sys.stderr)

    for msg in raw_messages:
        msg["md"] = clean_text(html_to_markdown(msg["html"]))

    # Drop tiny assistant "thinking" stubs
    raw_messages = [
        m for m in raw_messages
        if not (m["role"] == "assistant"
                and len(m["md"]) < 80
                and "checking" in m["md"].lower())
    ]

    md = build_markdown(title, raw_messages)

    if output_path is None:
        slug = re.sub(r"[^\w\s-]", "", title).strip().lower()
        slug = re.sub(r"[\s]+", "-", slug)[:60]
        output_path = f"{slug}.md"

    Path(output_path).write_text(md, encoding="utf-8")
    print(f"Saved to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
