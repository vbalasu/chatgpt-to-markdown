import asyncio
import sys
import os
from playwright.async_api import async_playwright

async def fetch_chatgpt_share(url, output_html, output_text):
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print(f"Navigating to {url}...", file=sys.stderr)
            # ChatGPT pages never reach networkidle due to persistent connections
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for conversation content to render
            try:
                await page.wait_for_selector("[data-message-author-role], .markdown, .whitespace-pre-wrap", timeout=30000)
                print("Found message selectors, waiting for content to stabilize...", file=sys.stderr)
            except:
                print("Warning: Timed out waiting for message selectors. Trying fallback...", file=sys.stderr)

            # Give dynamic content time to fully render
            await asyncio.sleep(5)

            content = await page.content()
            text_content = await page.evaluate("() => document.body.innerText")

            with open(output_html, "w", encoding="utf-8") as f:
                f.write(content)

            with open(output_text, "w", encoding="utf-8") as f:
                f.write(text_content)

            print(f"Successfully saved content to {output_html} and {output_text}", file=sys.stderr)
            return True

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            # Save whatever we have if we got to the page at least
            try:
                content = await page.content()
                with open(output_html, "w", encoding="utf-8") as f:
                    f.write(content)
            except:
                pass
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_chatgpt.py <url> [output_html] [output_text]")
        sys.exit(1)

    share_url = sys.argv[1]
    html_out = sys.argv[2] if len(sys.argv) > 2 else "chatgpt_share.html"
    text_out = sys.argv[3] if len(sys.argv) > 3 else "chatgpt_share.txt"

    success = asyncio.run(fetch_chatgpt_share(share_url, html_out, text_out))
    sys.exit(0 if success else 1)
