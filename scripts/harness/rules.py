"""Static rules used by harness scanners and validators."""

from __future__ import annotations

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".cache",
    "__pycache__",
    ".agent",
    "vendor",
    "third_party",
    "target",
    "out",
    "coverage",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    ".gradle",
    ".idea",
    ".vscode",
}

SKIP_DIR_PREFIXES = (
    "bazel-",
)

CI_CONFIG_NAMES = {
    ".travis.yml",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "appveyor.yml",
}

CI_CONFIG_DIRS = {
    ".github",
    ".gitlab",
    ".circleci",
    ".buildkite",
}

SCRIPT_DIRS = (
    "scripts",
    "bin",
    "tools",
    "hack",
    "ci",
)

MANIFEST_NAMES = {
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "bun.lockb",
    "pyproject.toml",
    "requirements.txt",
    "poetry.lock",
    "Pipfile",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "Makefile",
    "docker-compose.yml",
    "Dockerfile",
    "pnpm-workspace.yaml",
    "lerna.json",
    "turbo.json",
    "nx.json",
    "go.work",
}

TEST_HINTS = (
    "test",
    "tests",
    "__tests__",
    "spec",
    "e2e",
)

RISK_KEYWORDS = {
    "auth": "auth or authentication",
    "authentication": "auth or authentication",
    "permission": "permissions",
    "permissions": "permissions",
    "billing": "billing",
    "payment": "payments",
    "payments": "payments",
    "migration": "database migrations",
    "migrations": "database migrations",
    "infra": "infrastructure",
    "deploy": "deployment",
    "secret": "secrets",
    "secrets": "secrets",
    "generated": "generated files",
    "openapi": "public API or generated clients",
    "swagger": "public API or generated clients",
    "proto": "public API or generated clients",
}

GENERATED_HINTS = (
    "generated",
    ".generated.",
    ".pb.",
    "openapi",
    "swagger",
    "graphql",
)

DOC_NAMES = {
    "README.md",
    "CLAUDE.md",
    "CLAUDE_ARCH.md",
    "AGENTS.md",
    "GEMINI.md",
}

CONFIG_NAMES = {
    # JavaScript / TypeScript
    "vite.config.ts",
    "vite.config.js",
    "vite.config.mts",
    "tsconfig.json",
    "tsconfig.node.json",
    "tailwind.config.js",
    "tailwind.config.ts",
    "eslint.config.js",
    ".eslintrc",
    ".eslintrc.js",
    ".prettierrc",
    # Python
    "setup.py",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
    "ruff.toml",
    ".ruff.toml",
    "mypy.ini",
    ".flake8",
    "pyrightconfig.json",
    # Go
    ".golangci.yml",
    ".golangci.yaml",
    # Rust
    "rustfmt.toml",
    "clippy.toml",
    # Java / JVM
    "checkstyle.xml",
}

IMPORTANT_FLOW_HINTS = {
    # JavaScript / TypeScript frontend
    "main.tsx": "frontend app bootstrap",
    "main.ts": "app bootstrap",
    "App.tsx": "React app root",
    "router": "routing",
    "AuthGuard": "route guard or auth guard",
    "routeAuth": "route authorization",
    "request": "HTTP request boundary",
    "permission": "permission state or checks",
    "workflow": "workflow domain",
    "swagger": "API documentation surface",
    # Node backend
    "server.js": "Node server entrypoint",
    # Python backend
    "main.py": "Python app entrypoint",
    "app.py": "Python app entrypoint",
    "manage.py": "Django management entrypoint",
    "wsgi.py": "WSGI server entrypoint",
    "asgi.py": "ASGI server entrypoint",
    "settings.py": "framework settings",
    "urls.py": "Django URL routing",
    # Go backend
    "main.go": "Go app entrypoint",
    "cmd/": "Go command entrypoints",
}

REQUIRED_FILES = [
    "AGENTS.md",
    "docs/project-map.md",
    "docs/testing.md",
    "docs/dangerous-areas.md",
    "docs/debugging.md",
    "docs/agent-plan-template.md",
    "scripts/check.sh",
    ".agent/repo-facts.json",
]

REQUIRED_AGENTS_REFERENCES = [
    "docs/project-map.md",
    "docs/testing.md",
    "docs/dangerous-areas.md",
    "docs/debugging.md",
    "docs/agent-plan-template.md",
]

RISK_TERMS = [
    "auth",
    "permission",
    "billing",
    "payments",
    "migration",
    "deployment",
    "infra",
    "secret",
    "generated",
    "public api",
]

UNVERIFIED_COMMANDS = [
    "pnpm test",
    "npm test",
    "yarn test",
    "bun test",
    "pytest",
    "make test",
    "cargo test",
    "go test",
    "mvn test",
]

RUNTIME_GUESS_PATTERNS = [
    "pnpm run | grep",
    "npm run | grep",
    "yarn run | grep",
    "command -v pytest",
    "command -v pnpm",
    "command -v npm",
    "grep -qE '^test:' Makefile",
    "grep -q '^test:' Makefile",
]
