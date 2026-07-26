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
    "bitbucket-pipelines.yml",
    ".drone.yml",
    ".woodpecker.yml",
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
    # Node.js
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "bun.lockb",
    "pnpm-workspace.yaml",
    "lerna.json",
    "turbo.json",
    "nx.json",
    # Python
    "pyproject.toml",
    "requirements.txt",
    "poetry.lock",
    "Pipfile",
    # Go
    "go.mod",
    "go.work",
    # Rust
    "Cargo.toml",
    # Ruby
    "Gemfile",
    "Gemfile.lock",
    # PHP
    "composer.json",
    "composer.lock",
    # Elixir
    "mix.exs",
    "mix.lock",
    # C++
    "CMakeLists.txt",
    "conanfile.txt",
    "conanfile.py",
    # Java / JVM
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    # Bazel
    "BUILD",
    "WORKSPACE",
    # toolchain version managers
    ".tool-versions",
    # container / infra
    "Makefile",
    "docker-compose.yml",
    "Dockerfile",
}

# Maps manifest filename → ecosystem tag; used by detect_ecosystem_hypotheses.
# Only include manifests that strongly imply a single ecosystem.
MANIFEST_ECOSYSTEM: dict[str, str] = {
    "package.json": "node",
    "pnpm-lock.yaml": "node",
    "yarn.lock": "node",
    "package-lock.json": "node",
    "bun.lockb": "node",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "poetry.lock": "python",
    "Pipfile": "python",
    "go.mod": "go",
    "go.work": "go",
    "Cargo.toml": "rust",
    "Gemfile": "ruby",
    "Gemfile.lock": "ruby",
    "composer.json": "php",
    "composer.lock": "php",
    "mix.exs": "elixir",
    "mix.lock": "elixir",
    "CMakeLists.txt": "cpp",
    "conanfile.txt": "cpp",
    "conanfile.py": "cpp",
    "pom.xml": "java",
    "build.gradle": "java",
    "settings.gradle": "java",
    "BUILD": "bazel",
    "WORKSPACE": "bazel",
}

TEST_HINTS = (
    "test",
    "tests",
    "__tests__",
    "spec",
    "e2e",
)

TEST_EXACT_FILENAMES = {"conftest.py"}

RISK_KEYWORDS = {
    "auth": "auth or authentication",
    "authentication": "auth or authentication",
    "permission": "permissions",
    "permissions": "permissions",
    "billing": "billing",
    "payment": "payments",
    "payments": "payments",
    "stripe": "payment processing (Stripe)",
    "migration": "database migrations",
    "migrations": "database migrations",
    "infra": "infrastructure",
    "deploy": "deployment",
    "terraform": "infrastructure-as-code (Terraform)",
    "kubernetes": "Kubernetes or K8s orchestration",
    "k8s": "Kubernetes or K8s orchestration",
    "helm": "Helm chart or Kubernetes package",
    "secret": "secrets",
    "secrets": "secrets",
    "iam": "IAM or access control",
    "rbac": "role-based access control",
    "pii": "personally identifiable information",
    "generated": "generated files",
    "openapi": "public API or generated clients",
    "swagger": "public API or generated clients",
    "proto": "public API or generated clients",
}

GENERATED_HINTS = (
    "generated",
    ".generated.",
    ".pb.",
    ".gen.",
    "_pb2.",
    ".d.ts",
    "__generated__",
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
