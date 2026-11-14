# AGENTS.md

This file provides guidance to agentic coding agents working with the Xiliux AutoCM codebase.

## Development Commands

```bash
# Run the main agent (immediately, then scheduled: 09:15, 13:30, 19:45 daily)
python main.py

# Run email capture API server (Flask on port 5000)
python lead_capture_api.py

# Test email marketing module standalone
python email_marketing.py

# Verify credentials without publishing (nothing goes out)
python main.py --verify

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Backup subscriber database
cp subscribers.db subscribers_backup_$(date +%Y%m%d).db
```

## Code Style Guidelines

### Import Organization
- Standard library imports first (os, time, logging, etc.)
- Third-party imports second (requests, playwright, openai, etc.)
- Local imports last (email_marketing, email_templates)
- Group imports by type with blank lines between groups
- Use explicit imports over `import *`

### Formatting & Structure
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 120 characters
- Class names: `PascalCase` (e.g., `XiliuxAgent`, `EmailMarketingAgent`)
- Function/method names: `snake_case` (e.g., `observe_and_read`, `publish_mastodon`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `ZONES`, `TARGET_URL`)
- Private methods: prefix with underscore (e.g., `_send_individual_email`)

### Error Handling
- Use try/except blocks for all external API calls
- Log errors with appropriate level (ERROR for failures, WARNING for expected issues)
- Graceful degradation: missing credentials should log warning, not crash
- Return boolean success indicators where appropriate
- Use specific exception types when available (e.g., `sqlite3.IntegrityError`)

### Type Hints
- Add type hints for function parameters and return values
- Use Python 3.9+ syntax (e.g., `dict[str, str]` instead of `Dict[str, str]`)
- Optional parameters: use `| None` syntax (e.g., `nombre: str | None = None`)

### Documentation
- Class-level docstrings explaining purpose and usage
- Method docstrings for complex operations
- Inline comments for business logic decisions
- TODO comments for future improvements

### Database Patterns
- Use parameterized queries to prevent SQL injection
- Close connections properly
- Handle `IntegrityError` for duplicate entries
- Use transactions for multi-table operations

### API Client Patterns
- Initialize clients in `__init__` with try/except blocks
- Store clients in dictionary for organized access
- Check for None before using clients
- Log connection status appropriately

### Configuration Management
- Use `python-dotenv` for environment variables
- Provide sensible defaults in code
- Use `os.getenv()` with fallback values
- Never commit actual `.env` file

### Logging Standards
- Use structured logging with timestamps
- Include context (e.g., platform names in brackets)
- Log levels: DEBUG for detailed flow, INFO for normal operations, WARNING for expected issues, ERROR for failures
- Use emojis for visual clarity in logs (optional)

### Testing Strategy
- No formal test framework currently implemented
- Manual testing via standalone module execution
- Preview modes for email sending (`preview_mode=True`)
- Use test subreddits for Reddit integration

### Security Best Practices
- Never log credentials or tokens
- Use environment variables for secrets
- Validate user inputs (especially email addresses)
- Implement rate limiting awareness for external APIs
- Use unsubscribe tokens for email marketing compliance

### File Organization
- Main orchestration: `main.py`
- Email marketing: `email_marketing.py`, `email_templates.py`, `lead_capture_api.py`
- Configuration: `.env.example` (reference only)
- Documentation: `CLAUDE.md` (project overview)
- Each module should be runnable standalone for testing

### Platform-Specific Patterns
- Each social platform gets its own `publish_[platform]` method
- Methods should return early if platform not configured
- Use platform-appropriate APIs (e.g., media upload for image posts)
- Handle platform-specific error cases (e.g., Reddit rate limits)

### Scheduling & Automation
- Use `schedule` library for recurring tasks
- Random delays to prevent bot detection
- Lo periódico se decide por fecha (`weekday() == 0` para el correo), NO por
  `cycle_count`: cada `job()` construye un agente nuevo y el contador vuelve a 1
- Graceful shutdown handling

### Performance Considerations
- Use timeouts for network requests
- Implement retry logic for transient failures
- Cache expensive operations where appropriate
- Use streaming for large file operations