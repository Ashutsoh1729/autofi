# Release Plan — Publishing autofi as a CLI Tool

## Description

Steps to publish `autofi` across package management platforms so users can install it as a CLI with a single command. Covers PyPI (primary), Homebrew, Docker, and GitHub Releases.

---

## Pre-Release Checklist

- [ ] Fill out `pyproject.toml` metadata: author, description, license, `[project.urls]` (Homepage, Source, Issues)
- [ ] Choose an OSI-approved license and add a `LICENSE` file
- [ ] Write a proper `README.md` with install/usage examples
- [ ] Bump version in `pyproject.toml` following [SemVer](https://semver.org/)
- [ ] Tag the release in git: `git tag v0.1.0 && git push --tags`
- [ ] Run tests: `uv run pytest`
- [ ] Run lint: `uv run ruff check`

---

## 1. PyPI (pip / uv tool install)

**Most important target.** Once published, anyone can `pip install autofi` or `uv tool install autofi`.

### Steps

- [ ] Create a [PyPI account](https://pypi.org/account/register/)
- [ ] Generate an [API token](https://pypi.org/manage/account/token/) (set scope to "entire account" or per-project)
- [ ] Save the token locally (e.g. in `~/.pypirc` or as `UV_PUBLISH_TOKEN`)
- [ ] Build the package: `uv build`
- [ ] Publish to PyPI: `uv publish`

### Requirements

| Item | Detail |
|---|---|
| Package name | Must be unique on PyPI (`autofi` is 1st-come-1st-served) |
| Metadata | `pyproject.toml` must have `name`, `version`, `description`, `requires-python`, `dependencies` |
| Entry point | `[project.scripts] autofi = "cli.main:autofi"` (already set) |
| Build system | `uv build` uses the `[build-system]` from `pyproject.toml` (or auto-detects setuptools) |

---

## 2. Homebrew (macOS / Linux)

Allows `brew install autofi`.

### Options

**A. Homebrew-core (official tap)** — more visibility, but PR review is strict.

- Formula goes in [homebrew-core](https://github.com/Homebrew/homebrew-core)
- Formula installs via PyPI: `resource :pypi` downloads the `.tar.gz` from PyPI
- Must pass `brew audit --strict` and `brew test`

**B. Custom tap** — easier, no review.

- Create a repo `homebrew-autofi` on GitHub
- Write a formula `Formula/autofi.rb` that runs:
  ```ruby
  resource "autofi" do
    url "https://files.pythonhosted.org/packages/.../autofi-0.1.0.tar.gz"
    sha256 "..."
  end
  ```
- Users install with `brew install ashutoshhota/autofi/autofi`

### Requirements

| Item | Detail |
|---|---|
| PyPI tarball | Must be published on PyPI first (source of truth for Homebrew) |
| Formula | Must specify `url`, `sha256`, `depends_on "python@3.13"`, and test block |
| SHA-256 | Updated every release; can be automated |

---

## 3. Docker Hub / GHCR

Allows `docker pull ghcr.io/ashutoshhota/autofi`.

### Steps

- [ ] Write a `Dockerfile`:
  ```dockerfile
  FROM python:3.13-slim
  pip install autofi
  ENTRYPOINT ["autofi"]
  ```
- [ ] Build: `docker build -t autofi .`
- [ ] Tag: `docker tag autofi ghcr.io/ashutoshhota/autofi:0.1.0`
- [ ] Push: `docker push ghcr.io/ashutoshhota/autofi:0.1.0`
- [ ] (Optional) Set up GitHub Actions to build & push on tags automatically

### Requirements

| Item | Detail |
|---|---|
| Container registry | Docker Hub or GitHub Container Registry (GHCR) |
| Authentication | `docker login` with access token |
| PyPI or local build | Dockerfile either `pip install autofi` (from PyPI) or COPY + pip install from local build |

---

## 4. GitHub Releases

Downloads available without any package manager.

### Steps

- [ ] Run `uv build` → produces `dist/autofi-0.1.0.tar.gz` and `dist/autofi-0.1.0-py3-none-any.whl`
- [ ] Create a Release on GitHub from the `v0.1.0` tag
- [ ] Attach both `dist/*` files as release assets
- [ ] Write release notes (changelog, breaking changes, upgrade instructions)

### Requirements

| Item | Detail |
|---|---|
| Tag | `git tag v<version>` pushed to GitHub |
| Build artifacts | `.tar.gz` (source dist) + `.whl` (wheel) |
| Release notes | Manual or auto-generated from commit log |

---

## Automated Release Workflow (GitHub Actions)

- [ ] Create `.github/workflows/release.yml` that triggers on `v*` tags
- [ ] Steps: `uv sync` → `uv run pytest` → `uv run ruff check` → `uv build` → `uv publish`
- [ ] Optionally also build & push Docker image, and attach artifacts to the Release

---

## Versioning Strategy

- Use `0.x.0` for pre-1.0 development releases
- Bump minor for new features, patch for bug fixes
- After v1.0, follow strict SemVer: MAJOR.MINOR.PATCH
