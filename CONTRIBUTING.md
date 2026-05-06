# Contributing to pruna-mcp-server

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/charlesrapp/pruna-mcp-server.git
cd pruna-mcp-server
uv sync --dev
```

## Running Tests

```bash
uv run pytest --cov
```

## Code Quality

```bash
uv run ruff check src/ tests/
uv run mypy src/
```

## Pull Request Guidelines

1. Fork the repository and create a feature branch
2. Write tests for new functionality
3. Ensure all tests pass and coverage stays above 90%
4. Ensure `ruff check` and `mypy` pass with no errors
5. Use [conventional commits](https://www.conventionalcommits.org/) for commit messages
6. Open a PR with a clear description of the change

## Commit Message Format

```
feat: add new tool for batch generation
fix: handle timeout on video polling
docs: update README with Docker instructions
test: add integration tests for prompts
```
