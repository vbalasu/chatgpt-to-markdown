Convert a ChatGPT chat share link to a Markdown document. The user will provide a URL like https://chatgpt.com/share/...

# ChatGPT Chat to Markdown

This command automates the process of fetching a ChatGPT share conversation and converting it into a clean Markdown document. It uses Playwright to load the dynamic page content.

## Workflow

1. **Fetch Content:** Use the bundled Python script to fetch the page.
   ```bash
   python chatgpt-to-markdown/scripts/fetch_chatgpt.py "$ARGUMENTS" "temp.html" "temp.txt"
   ```
2. **Analyze HTML:** Read the generated `temp.html` (or `temp.txt` if HTML is too large) to identify the conversation structure.
3. **Format as Markdown:** Convert the extracted dialogue into a Markdown document.
   - Use `#` for the title.
   - Use `**User:**` and `**ChatGPT:**` to distinguish speakers.
   - Preserve all code blocks with their respective language tags.
   - Preserve headings, lists, bold/italic formatting from assistant responses.
4. **Cleanup:** Delete the temporary files.

## Reference
See [chatgpt-to-markdown/references/selectors.md](chatgpt-to-markdown/references/selectors.md) for detailed CSS selectors if parsing fails.
