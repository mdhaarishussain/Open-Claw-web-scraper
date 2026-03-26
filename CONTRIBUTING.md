# Contributing to Heartisans Autonomous Data Pipeline

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)
- [Documentation](#documentation)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what's best for the project
- Show empathy towards other community members

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/Open-Claw-web-scraper.git
   cd Open-Claw-web-scraper
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original/Open-Claw-web-scraper.git
   ```

4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 💻 Development Setup

### Prerequisites

- Python 3.10+
- pip
- virtualenv
- git

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-mock black flake8 mypy

# Copy environment file
cp .env.example .env

# Edit .env with your test API keys
```

### Project Structure

```
Open-Claw-web-scraper/
├── config/              # Configuration files
│   ├── settings.py     # Central configuration
│   └── seed_urls.yaml  # Target websites
├── src/
│   ├── scraper/        # Web scraping modules
│   ├── extraction/     # LLM extraction modules
│   ├── storage/        # Database modules
│   └── orchestrator/   # Pipeline orchestration
├── prompts/            # LLM prompts
├── tests/              # Test files
├── data/               # Runtime data (gitignored)
├── logs/               # Log files (gitignored)
└── main.py             # Entry point
```

## 🔨 Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-new-llm-provider` - New features
- `fix/rate-limiter-bug` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/cleanup-extractors` - Code refactoring
- `test/add-scraper-tests` - Test additions

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
git commit -m "feat(extraction): add support for Cohere LLM provider"

git commit -m "fix(scraper): handle timeout errors in StealthyFetcher

- Added proper exception handling for timeout errors
- Implemented retry logic with exponential backoff
- Updated tests to cover timeout scenarios

Closes #123"

git commit -m "docs(readme): update installation instructions"
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_scraper.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names
- Include docstrings explaining what's being tested

**Example:**

```python
# tests/test_extraction/test_schema.py

import pytest
from src.extraction.schema import ProductData

def test_product_data_validates_price():
    """Test that ProductData rejects invalid prices"""
    with pytest.raises(ValueError, match="price must be positive"):
        ProductData(
            material_used="Gold",
            origin="India",
            date_of_manufacture="2020",
            scratches=False,
            colour="Gold",
            current_market_price=-100,  # Invalid!
            work_type="Handwork",
            limited_edition=False
        )
```

### Test Coverage

- Aim for >80% code coverage
- Focus on critical paths (extraction, validation, storage)
- Test error handling and edge cases
- Mock external dependencies (APIs, network calls)

## 📤 Submitting Changes

### Before Submitting

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests**:
   ```bash
   pytest
   ```

3. **Format code**:
   ```bash
   black src/ tests/
   ```

4. **Lint code**:
   ```bash
   flake8 src/ tests/
   ```

5. **Type check** (optional but recommended):
   ```bash
   mypy src/
   ```

### Creating a Pull Request

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a Pull Request** on GitHub

3. **Fill out the PR template**:
   - Clear title summarizing the change
   - Detailed description of what changed and why
   - Reference any related issues
   - Include screenshots/examples if applicable

4. **Wait for review**:
   - Address any feedback
   - Make requested changes
   - Push updates to the same branch

### PR Checklist

- [ ] Code follows project coding standards
- [ ] Tests pass locally
- [ ] New code has tests
- [ ] Documentation updated if needed
- [ ] Commit messages are clear and follow conventions
- [ ] No merge conflicts with main

## 📝 Coding Standards

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use [Black](https://github.com/psf/black) for formatting
- Maximum line length: 100 characters
- Use type hints where possible

### Code Organization

- One class per file (generally)
- Group related functions together
- Keep functions small and focused
- Use descriptive variable names
- Add docstrings to all public functions/classes

### Docstrings

Use Google-style docstrings:

```python
def extract_product_links(html: str, selector: str) -> List[str]:
    """
    Extract product URLs from an HTML page.

    Args:
        html: Raw HTML content of the page
        selector: CSS selector for product links

    Returns:
        List of absolute product URLs

    Raises:
        ValueError: If selector is invalid

    Example:
        >>> links = extract_product_links(html, "a.product")
        >>> print(len(links))
        15
    """
    pass
```

### Error Handling

- Use specific exceptions
- Log errors with context
- Don't silently ignore exceptions
- Provide helpful error messages

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise CustomError(f"Failed to complete operation: {e}")  from e
```

### Logging

- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Include context in log messages
- Don't log sensitive information (API keys, passwords)

```python
logger.debug(f"Processing URL: {url[:50]}...")
logger.info(f"Successfully stored {count} products")
logger.warning(f"Circuit breaker opened for {domain}")
logger.error(f"Failed to extract data: {error}", exc_info=True)
```

## 📚 Documentation

### Code Documentation

- Add docstrings to all public modules, classes, and functions
- Include type hints
- Explain complex logic with inline comments
- Keep comments up-to-date with code changes

### README and Docs

- Update README.md if adding major features
- Update ARCHITECTURE.md for architectural changes
- Add examples for new features
- Keep documentation clear and concise

### Configuration

- Document new environment variables in `.env.example`
- Update `config/settings.py` docstrings
- Explain configuration options in README

## 🐛 Reporting Bugs

### Before Reporting

1. Check if the bug is already reported in [Issues](https://github.com/yourusername/Open-Claw-web-scraper/issues)
2. Try to reproduce with the latest code
3. Gather relevant information (logs, error messages, environment)

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Configure with '...'
2. Run command '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- OS: [e.g., Windows 10, Ubuntu 20.04]
- Python version: [e.g., 3.10.5]
- LLM Provider: [e.g., Cerebras]

**Logs**
```
Paste relevant log output here
```

**Additional context**
Any other context about the problem.
```

## 💡 Feature Requests

We welcome feature requests! Please:

1. Check if the feature is already requested
2. Explain the use case
3. Describe the proposed solution
4. Consider alternative approaches

## 🎯 Good First Issues

Look for issues labeled `good first issue` - these are great for newcomers!

## 📞 Questions?

- Open a [Discussion](https://github.com/yourusername/Open-Claw-web-scraper/discussions)
- Reach out to maintainers
- Check existing documentation

## 🙏 Thank You!

Your contributions make this project better for everyone. Thank you for taking the time to contribute!

---

**Happy Coding! 🚀**
