# Substack MCP Server

A Model Context Protocol (MCP) server for Substack integration with Claude Code and other MCP-compatible AI tools.

## Features

- **Create and manage drafts** - Create, update, and publish Substack posts programmatically
- **Image upload** - Upload images to Substack's CDN with proper metadata
- **Live blogging** - Real-time post updates with timestamps
- **Notes** - Post short-form content to Substack Notes
- **Full ProseMirror support** - Proper document structure for Substack's editor

## Installation

```bash
# Clone the repo
git clone https://github.com/acolle/substack-mcp.git
cd substack-mcp

# Install dependencies
pip install -r requirements.txt
```

## Testing

```bash
python -m unittest discover -s tests
```

## Setup

### 1. Get your Substack credentials

1. Go to your Substack dashboard in Chrome/Safari
2. Open DevTools (Cmd+Option+I or F12)
3. Go to Application tab → Cookies → your-substack.substack.com
4. Find `substack.sid` and copy its value

### 2. Create credentials file

```bash
# Create ~/.substackrc
cat > ~/.substackrc << 'EOF'
export SUBSTACK_PUBLICATION="your-publication.substack.com"
export SUBSTACK_SID="your-cookie-value-here"
EOF
```

### 3. Add to Claude Code

```bash
# Add the MCP server to Claude Code
claude mcp add substack \
  --command "bash" \
  --args "-c" "source ~/.substackrc && python3 $(pwd)/substack_mcp/server.py"
```

Or manually add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "substack": {
      "command": "bash",
      "args": ["-c", "source ~/.substackrc && python3 /path/to/substack-mcp/substack_mcp/server.py"]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `substack_create_draft` | Create a new draft post |
| `substack_update_draft` | Update an existing draft |
| `substack_append_to_draft` | Append content (for live blogging) |
| `substack_add_code_block` | Add a code block to a draft |
| `substack_add_image` | Add an image to a draft |
| `substack_publish` | Publish a draft |
| `substack_post_note` | Post a short note |
| `substack_get_drafts` | List all drafts |
| `substack_get_posts` | List published posts |
| `substack_live_blog_start` | Start a live blogging session |
| `substack_live_blog_end` | End live blogging session |

## Usage Examples

### Create a post with Claude Code

```
You: Create a new Substack post about AI tools

Claude: I'll create a draft for you...
[Uses substack_create_draft tool]
Created draft 12345. Edit at: https://your-pub.substack.com/publish/post/12345
```

### Upload and embed images

```
You: Add this diagram to my post [image path]

Claude: I'll upload the image and add it to your draft...
[Uses substack_add_image tool]
Image added successfully.
```

### Live blogging

```
You: Start a live blog for the product launch

Claude: Starting live blog session...
[Uses substack_live_blog_start tool]
Live blog started. I'll append updates as they happen.
```

## API Reference

### SubstackClient

The core client for interacting with Substack's API.

```python
from substack_client import SubstackClient, SubstackDocument

# rate_limit is seconds between requests; timeout is per-request timeout.
client = SubstackClient(token="your-sid", publication="your-pub.substack.com", rate_limit=0.5, timeout=30.0)

# Upload an image
img = client.upload_image("/path/to/image.png")
# Returns: {"url": "https://...", "width": 800, "height": 600, "bytes": 12345, "contentType": "image/png"}

# Create a document
doc = SubstackDocument()
doc.heading("My Post", level=2)
doc.paragraph("Hello world!")
doc.image(src=img['url'], width=img['width'], height=img['height'],
          bytes_size=img['bytes'], content_type=img['contentType'])

# Create and publish
draft = client.create_draft(title="My Post", body=doc)
client.publish_draft(draft.id, send_email=False)
```

## Key Technical Details

### Image Node Structure

Substack uses ProseMirror and requires specific attributes for images:

```json
{
  "type": "captionedImage",
  "content": [{
    "type": "image2",
    "attrs": {
      "src": "https://substack-post-media.s3.amazonaws.com/...",
      "width": 800,
      "height": 600,
      "bytes": 12345,
      "type": "image/png",
      "internalRedirect": "https://pub.substack.com/i/{draft_id}?img={encoded_url}",
      "belowTheFold": false,
      "topImage": false,
      "isProcessing": false
    }
  }]
}
```

The `internalRedirect` field is **required** - without it, Substack's editor fails to render the document.

### Image Handling Notes

- `create_draft` and `update_draft` automatically add missing `internalRedirect` values for any image nodes.
- Image captions are emitted as separate italic paragraphs (not `imageCaption` nodes) to avoid editor rendering issues.
- For best rendering results, upload images through `upload_image()` and use the returned metadata.

## Credits

- Built on [Jakub Slys's Substack API reverse engineering](https://iam.slys.dev/p/no-official-api-no-problem-how-i)
- Uses [Anthropic's MCP Python SDK](https://github.com/anthropics/mcp)

## License

MIT

## Disclaimer

This uses Substack's unofficial/internal API which may change without notice. Use at your own risk.
