# Configure Puzzle Sources

> **See also**:
>
> - [How-To: Create Adapter](./create-adapter.md) — Building custom adapters
> - [Architecture: Adapters](../../architecture/backend/adapters.md) — Adapter design
> - [Reference: Adapters](../../reference/adapters/) — Per-adapter configs
> - [Troubleshoot](./troubleshoot.md) — Common issues

**Last Updated**: 2026-02-01

Guide to configuring puzzle sources for the pipeline.

---

## Configuration File

All sources are configured in:

```text
backend/puzzle_manager/config/sources.json
```

---

## Basic Structure

```json
{
  "active_adapter": "source_name",
  "sources": [
    {
      "id": "source_name",
      "name": "source_name Collection",
      "adapter": "source_name",
      "enabled": true,
      "config": {
        "path": "external-sources/source_name"
      }
    }
  ]
}
```

### Required Fields

| Field     | Type    | Description                                          |
| --------- | ------- | ---------------------------------------------------- |
| `id`      | string  | Unique source identifier (used with `--source` flag) |
| `name`    | string  | Human-readable display name                          |
| `adapter` | string  | Adapter registration name                            |
| `enabled` | boolean | Whether source is active                             |
| `config`  | object  | Adapter-specific configuration                       |

---

## The `active_adapter` Setting

The `active_adapter` field defines the **default source** for pipeline runs:

```json
{
  "active_adapter": "source_name"
}
```

### Behavior

1. **Single Source Design**: The pipeline processes ONE source per run
2. **CLI Override**: Use `--source` to specify a different source
3. **Safety Check**: Mixing sources requires explicit override

### Example Workflow

```bash
# Uses active_adapter (source_name)
python -m backend.puzzle_manager run

# Explicitly specify source
python -m backend.puzzle_manager run --source source_name
```

---

## The `--source-override` Flag

When the requested source differs from `active_adapter`, you'll see:

```text
Source `abc` differs from active_adapter `source_name`. Use `--source-override` to proceed.
```

This safety check prevents accidentally mixing data from different sources in the same staging directory.

### When to Use `--source-override`

Use when you **intentionally** want to process a different source:

```bash
# Override safety check
python -m backend.puzzle_manager run --source source_name --source-override
```

### When NOT to Use

- Don't use if you made a typo in the source name
- Don't use if you're unsure which source to use
- Check `python -m backend.puzzle_manager sources` first

---

## Adding a New Source

1. **Register the adapter** (if new adapter type):

   ```python
   @register_adapter("my-source")
   class MyAdapter(BaseAdapter):
       ...
   ```

2. **Add to sources.json**:

   ```json
   {
     "id": "my-source",
     "name": "My Puzzle Source",
     "adapter": "my-source",
     "enabled": true,
     "config": {
       "base_url": "https://example.com/api"
     }
   }
   ```

3. **Verify registration**:

   ```bash
   python -m backend.puzzle_manager sources
   ```

## Environment Variables in Config

Use `${VAR_NAME}` for sensitive values:

```json
{
  "config": {
    "api_key": "${MY_SOURCE_API_KEY}",
    "secret": "${MY_SOURCE_SECRET}"
  }
}
```

Set environment variables before running:

```bash
export MY_SOURCE_API_KEY="abc123"
python -m backend.puzzle_manager run --source my-source
```

---

## Common Configurations

### API-Based Source

```json
{
  "id": "api-source",
  "adapter": "api",
  "config": {
    "base_url": "https://api.example.com",
    "request_timeout_seconds": 30,
    "max_retries": 3,
    "rate_limit_delay_seconds": 1
  }
}
```

### File-Based Source

```json
{
  "id": "local-files",
  "adapter": "local",
  "config": {
    "base_path": "external-sources/my-collection",
    "pattern": "**/*.sgf"
  }
}
```

### GitHub Raw Source

```json
{
  "id": "github-collection",
  "adapter": "url",
  "config": {
    "base_url": "https://raw.githubusercontent.com/user/repo/main/",
    "directories": ["easy", "medium", "hard"]
  }
}
```

---

## CI/Container Configuration

### Custom Runtime Directory

In CI/containers, override the default runtime directory:

```bash
export YENGO_RUNTIME_DIR=/tmp/yengo-runtime
python -m backend.puzzle_manager run --source source_name
```

### Read-Only Config

For containerized deployments with read-only config:

```bash
export YENGO_CONFIG_DIR=/app/config
python -m backend.puzzle_manager run --source source_name
```

### GitHub Actions Example

```yaml
- name: Run Pipeline
  env:
    YENGO_RUNTIME_DIR: ${{ runner.temp }}/yengo
  run: |
    python -m backend.puzzle_manager run --source source_name --batch-size 50
```

### Docker Example

```dockerfile
ENV YENGO_RUNTIME_DIR=/app/runtime
ENV YENGO_CONFIG_DIR=/app/config
CMD ["python", "-m", "backend.puzzle_manager", "run", "--source", "source_name"]
```

---

## Troubleshooting

### Source Not Found

```bash
# List available sources
python -m backend.puzzle_manager sources

# Output shows configured sources
# yengo-source (enabled)
# yengo-source (enabled)
```

### Adapter Not Registered

Ensure the adapter has `@register_adapter` decorator and is imported in `adapters/__init__.py`.

### Config Validation Errors

```bash
# Validate configuration
python -m backend.puzzle_manager validate
```
