# Development Guidelines for GroundUp

This repository contains multiple projects: a Django application and two monorepos (deepagents Python packages and OHIF Viewer TypeScript packages).

## Project Structure

```text
/root                 # Django app with apps (accounts, blog, chat, syringly, telemed, etc.)
├── deepagents/       # Python monorepo (SDK, CLI, ACP, Harbor, partners)
└── viewer/           # TypeScript/React monorepo (OHIF medical imaging viewer)
```

---

## Django App (Root Level)

### Commands

```bash
# Run development server
python manage.py runserver

# Run tests
python manage.py test

# Run specific test
python manage.py test <app_name>.<test_class>

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Code Style

- Follow Django conventions and Python PEP 8
- Use Type hints for all function signatures
- Use Google-style docstrings for models and views
- Test files go in `<app>/tests.py` or `<app>/tests/` directory

---

## DeepAgents (Python Monorepo)

Located in `deepagents/`. Uses `uv` for package management and `make` as task runner.

### Commands

```bash
# From deepagents/ root:
make lint         # Lint all packages
make format       # Format all packages
make test         # Run unit tests (no network)
make lock         # Update all lockfiles

# Single package commands (e.g., deepagents SDK):
cd libs/deepagents
make test TEST_FILE=tests/unit_tests/<specific>.py   # Run specific test file
make test TEST_FILE=tests/integration_tests/         # Run integration tests
make lint                                                     # Lint package
make format                                                   # Format package
make type                                                    # Type check
make benchmark                                               # Run benchmarks

# Run specific pytest directly:
uv run --group test pytest tests/unit_tests/test_specific.py
```

### Code Style

- **Type hints**: Required for all functions (no bare `Any`)
- **Docstrings**: Google-style with Args, Returns, Raises sections
- **Imports**: Ruff handles import sorting automatically
- **Formatting**: Ruff (line length 100)
- **Linting**: Ruff + ty for type checking
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Error handling**: No bare `except:`, use specific exception types
- **Testing**: pytest with `asyncio_mode = "auto"` (don't add `@pytest.mark.asyncio`)
- **Tests location**: Mirror source structure in `tests/unit_tests/` and `tests/integration_tests/`
- **Code formatting**: Use single backticks for inline code (`code`), not double backticks

### Key Files

- `pyproject.toml`: Package configuration
- `Makefile`: Development tasks
- `uv.lock`: Locked dependencies

---

## Viewer (TypeScript/React Monorepo)

Located in `viewer/`. Uses `yarn` and `lerna` for package management.

### Commands

```bash
cd viewer

# Install dependencies
yarn install --frozen-lockfile

# Development
yarn dev                          # Run all packages in dev mode
yarn dev:fast                    # Fast dev mode (platform/app)
yarn dev:project .scripts/dev.sh  # Project-specific dev

# Build
yarn build                       # Build all packages
yarn build:dev                   # Dev build
yarn build:demo                  # Demo build

# Testing
yarn test                        # Run unit tests (Jest)
yarn test:unit                   # Same as test
yarn test:unit <package>         # Run tests for specific package
yarn test-watch                  # Watch mode
yarn test:e2e                    # E2E tests (Playwright)
yarn test:e2e:ui                 # E2E tests with UI
yarn test:e2e:headed             # E2E with browser visible

# Linting and Formatting
yarn lint                        # ESLint (if configured)
yarn format                      # Prettier formatting

# Other
yarn clean                       # Clean build artifacts
yarn cli                         # Run platform CLI
```

### Code Style

- **Language**: TypeScript with React
- **Linting**: ESLint (extends react-app, @typescript-eslint, prettier)
- **Formatting**: Prettier (with tailwindcss plugin), single quotes, trailing commas
- **Naming**: camelCase for variables/functions, PascalCase for components
- **Imports**: Relative imports within packages, absolute for cross-package
- **React patterns**: Functional components with hooks
- **Testing**: Jest for unit, Playwright for e2e
- **Test location**: `src/__tests__/` or `*.test.ts` / `*.spec.ts` alongside source

### Key Files

- `package.json`: Root workspace configuration
- `.eslintrc.json`: ESLint configuration
- `lerna.json`: (if exists) Lerna configuration

---

## General Guidelines

### Security

- Never commit secrets, API keys, or credentials
- Use environment variables for sensitive data
- No `eval()`, `exec()`, or `pickle` on user-controlled input

### Git / PRs

- Conventional Commits format for PR titles: `type(scope): description`
- Example: `feat(sdk): add new feature`, `fix(cli): resolve bug`
- All lowercase except proper nouns
- Include scope with no exceptions

### Important Notes

- Do NOT use Sphinx-style double backtick formatting (` ``code`` `)
- Use single backticks (`code`) for inline code references
- Prefer inline `# noqa: RULE` over global ignores for lint exceptions
- Mark experimental features with clear warnings in docstrings