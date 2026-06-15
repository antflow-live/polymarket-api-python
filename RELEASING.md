# Releasing

Releases are published to [PyPI](https://pypi.org/project/polymarket-api-python/)
automatically by `.github/workflows/publish.yml` when a GitHub Release is
published. Publishing uses **PyPI Trusted Publishing** (OpenID Connect), so there
are **no API tokens or secrets** stored anywhere.

## One-time setup (maintainer, on pypi.org)

Do this once, before the first release. It can be configured *before* the project
exists on PyPI ("pending publisher"):

1. Sign in at <https://pypi.org> and open **Account → Publishing**.
2. Under **Add a new pending publisher**, fill in:
   - **PyPI Project Name:** `polymarket-api-python`
   - **Owner:** `antflow-live`
   - **Repository name:** `polymarket-api-python`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
3. (Optional but recommended) In the GitHub repo, create an **Environment** named
   `pypi` (Settings → Environments) so releases can be gated/reviewed.

That's it — no token is ever copied or stored.

## Cutting a release

1. Bump `version` in `pyproject.toml` (semver, e.g. `0.1.0` → `0.1.1`).
2. Commit and tag:
   ```bash
   git commit -am "release: v0.1.1"
   git tag v0.1.1
   git push origin main --tags
   ```
3. Create a **GitHub Release** for the tag (Releases → Draft a new release →
   choose the tag → Publish).
4. The `Publish to PyPI` workflow runs automatically: it builds the sdist + wheel,
   runs `twine check`, and uploads to PyPI via OIDC.

## Building locally (to verify before a release)

```bash
uv build              # writes dist/*.tar.gz and dist/*.whl
uvx twine check dist/*
```

Both artifacts should report `PASSED` before you tag a release.
