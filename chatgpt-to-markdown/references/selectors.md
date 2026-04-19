# ChatGPT Share Page Selectors

Current known selectors for ChatGPT share pages as of April 2026:

- **Message Container:** `div[data-message-author-role]` — each message has a `data-message-author-role` attribute set to `"user"` or `"assistant"`.
- **User Message Text:** `div.whitespace-pre-wrap` inside the user message container.
- **Assistant Response:** `div.markdown` inside the assistant message container. Contains standard HTML elements (`p`, `h2`, `h3`, `ul`, `ol`, `li`, `strong`, `em`, `pre`, `code`, `hr`).
- **Code Blocks:** `pre` tags within `div.markdown`, with `code` children that may have language classes.
- **Page Title:** `<title>` tag contains the conversation title.

## Parsing Logic
1. Find all `div` elements with `data-message-author-role` attribute.
2. Read the role from the attribute value (`user` or `assistant`).
3. User messages: Extract text from the `div.whitespace-pre-wrap` child.
4. Assistant messages: Extract formatted content from the `div.markdown` child, preserving headings, lists, bold/italic, and code blocks.
