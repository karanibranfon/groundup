# Development Guidelines for GroundUp

## General Guidelines

### Communication and Clarification
- Do not make wrong assumptions without checking
- Ask for clarification when confused or uncertain
- Surface inconsistencies in requirements or code
- Present trade-offs when multiple approaches exist
- Push back when necessary with reasoning

### Code Quality Standards
- Do not overcomplicate code or APIs
- Avoid bloated abstractions
- Clean dead code proactively
- **CRITICAL**: Do not change or remove comments without fully understanding them, even if the task is hard
- Do not remove comments just because you don't like them

---

## Project Structure

```text
/root                 # Django app (accounts, blog, chat, syringly, telemed)
├── deepagents/       # Python monorepo (SDK, CLI, ACP, Harbor, partners)
└── viewer/           # TypeScript/React monorepo (OHIF medical imaging viewer)
```

---

## Django App (Root Level)

### Commands
```bash
# Run development server
python manage.py runserver

# Run all tests
python manage.py test

# Run specific test class
python manage.py test telemed.tests.DNACryptoServiceTest

# Run specific test method
python manage.py test telemed.tests.DNACryptoServiceTest.test_encrypt_decrypt_roundtrip

# Migrations
python manage.py makemigrations && python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Code Style
- Follow Django conventions and Python PEP 8
- Type hints required for all function signatures
- Google-style docstrings for models and views
- Test files: `<app>/tests.py` or `<app>/tests/`

---

## DeepAgents (Python Monorepo)

Uses `uv` for package management and `make` as task runner.

### Commands
```bash
# From deepagents/ root
make lint         # Lint all packages
make format      # Format all packages
make test        # Run unit tests (no network)
make lock        # Update all lockfiles

# Single package (e.g., SDK)
cd libs/deepagents
make test TEST_FILE=tests/unit_tests/test_specific.py   # Run specific test file
make test TEST_FILE=tests/integration_tests/           # Run integration tests
make test TEST_FILE=tests/unit_tests/                  # Run all unit tests
make lint                                                     # Lint package
make format                                                   # Format package
make type                                                    # Type check
make benchmark                                               # Run benchmarks

# Run pytest directly
uv run --group test pytest tests/unit_tests/test_specific.py
```

### Code Style
- **Type hints**: Required (no bare `Any`)
- **Docstrings**: Google-style with Args, Returns, Raises sections
- **Imports**: Ruff handles import sorting
- **Formatting**: Ruff (line length 100)
- **Linting**: Ruff + ty for type checking
- **Naming**: snake_case (functions/variables), PascalCase (classes)
- **Error handling**: No bare `except:` - use specific exceptions
- **Testing**: pytest with `asyncio_mode = "auto"` (don't add `@pytest.mark.asyncio`)
- **Tests location**: Mirror source in `tests/unit_tests/` and `tests/integration_tests/`
- Use single backticks for inline code (`code`), not double backticks

### Key Files
- `pyproject.toml`: Package configuration
- `Makefile`: Development tasks
- `uv.lock`: Locked dependencies

### CLI-Specific (libs/cli/)
- Uses Textual for terminal UI
- Startup performance matters - defer heavy imports
- SDK dependency pinned in `pyproject.toml` - bump in same PR
- Slash commands: add to `COMMANDS` tuple in `command_registry.py` (alphabetical order)

---

## Viewer (TypeScript/React Monorepo)

Uses `yarn` and `lerna` for package management.

### Commands
```bash
cd viewer

# Install
yarn install --frozen-lockfile

# Development
yarn dev                    # Run all packages in dev mode
yarn dev:fast             # Fast dev mode (platform/app)
yarn dev:project .scripts/dev.sh  # Project-specific dev

# Build
yarn build                 # Build all packages
yarn build:dev            # Dev build
yarn build:demo           # Demo build

# Testing
yarn test                 # Unit tests (Jest)
yarn test:unit            # Same as test
yarn test:unit <package>  # Tests for specific package
yarn test-watch           # Watch mode
yarn test:e2e            # E2E tests (Playwright)
yarn test:e2e:ui         # E2E tests with UI
yarn test:e2e:headed      # Browser visible

# Linting and Formatting
yarn lint                 # ESLint
yarn format               # Prettier formatting
yarn clean                # Clean build artifacts
```

### Code Style
- **Language**: TypeScript with React
- **Linting**: ESLint (extends react-app, @typescript-eslint, prettier)
- **Formatting**: Prettier (single quotes, trailing commas)
- **Naming**: camelCase (variables/functions), PascalCase (components)
- **React patterns**: Functional components with hooks
- **Testing**: Jest (unit), Playwright (e2e)
- **Test location**: `src/__tests__/` or `*.test.ts` alongside source

### Key Files
- `package.json`: Root workspace configuration
- `.eslintrc.json`: ESLint configuration

---

## Security

- Never commit secrets, API keys, or credentials
- Use environment variables for sensitive data
- No `eval()`, `exec()`, or `pickle` on user-controlled input

---

## Git / PRs

- Conventional Commits: `type(scope): description` (lowercase, include scope)
- Examples: `feat(sdk): add feature`, `fix(cli): resolve bug`
- Mark experimental features with clear docstring warnings
- Prefer inline `# noqa: RULE` over global ignores

---

## Common Cleanup Tasks

```bash
# Regenerate viewer dependencies
cd viewer && yarn install --frozen-lockfile

# Clean Python bytecode cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete

# Verify viewer builds after cleanup
cd viewer && yarn build
```
