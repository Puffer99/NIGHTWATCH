# NIGHTWATCH Release Checklist

## Pre-Release Checklist

### Code Quality
- [ ] All unit tests passing: `pytest tests/unit/ -v`
- [ ] All integration tests passing: `pytest tests/integration/ -v`
- [ ] Linting passes: `ruff check services/ voice/ tests/`
- [ ] Type checking passes: `mypy services/ --ignore-missing-imports`
- [ ] No security vulnerabilities: `pip-audit`

### Documentation
- [ ] README.md is current
- [ ] CHANGELOG.md updated with all changes
- [ ] Installation guide tested on fresh system
- [ ] Voice commands documented
- [ ] API changes documented

### Safety Verification
- [ ] Safety interlocks tested
- [ ] Emergency stop functionality verified
- [ ] Weather safety thresholds configured correctly
- [ ] Graceful shutdown sequence tested
- [ ] Tool confirmation prompts working

### Version Updates
- [ ] Version updated in `nightwatch/__init__.py`
- [ ] Version updated in `setup.py` or `pyproject.toml`
- [ ] Version updated in install scripts

## Release Process

### 1. Create Release Branch
```bash
git checkout main
git pull origin main
git checkout -b release/v0.1.0
```

### 2. Update Version Numbers

**nightwatch/__init__.py:**
```python
__version__ = "0.1.0"
```

**pyproject.toml (if exists):**
```toml
version = "0.1.0"
```

### 3. Update CHANGELOG.md
```markdown
## [0.1.0] - YYYY-MM-DD

### Added
- Voice-controlled telescope operation
- Weather safety monitoring
- ...

### Changed
- ...

### Fixed
- ...
```

### 4. Run Full Test Suite
```bash
pytest tests/ -v --tb=short
```

### 5. Create Pull Request
- Title: "Release v0.1.0"
- Description: Include changelog excerpt
- Request review from maintainers

### 6. Merge to Main
After approval:
```bash
git checkout main
git merge release/v0.1.0
git push origin main
```

### 7. Create Git Tag
```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

### 8. Create GitHub Release
1. Go to Releases > Draft a new release
2. Select tag: `v0.1.0`
3. Title: `NIGHTWATCH v0.1.0`
4. Description: Copy from CHANGELOG.md
5. Attach artifacts if any
6. Publish release

## Post-Release

### Announcements
- [ ] Update project README with release badge
- [ ] Post announcement (if applicable)
- [ ] Update documentation site (if applicable)

### Cleanup
- [ ] Delete release branch
- [ ] Close related milestone
- [ ] Update project board

### Next Version
- [ ] Create milestone for next version
- [ ] Triage remaining issues
- [ ] Update roadmap

## Hotfix Process

For critical bugs in released versions:

### 1. Create Hotfix Branch
```bash
git checkout v0.1.0
git checkout -b hotfix/v0.1.1
```

### 2. Apply Fix
- Make minimal changes to fix the issue
- Add regression test

### 3. Update Version
- Increment patch version (0.1.0 → 0.1.1)
- Update CHANGELOG.md

### 4. Merge and Tag
```bash
git checkout main
git merge hotfix/v0.1.1
git tag -a v0.1.1 -m "Hotfix v0.1.1"
git push origin main --tags
```

## Version Numbering

NIGHTWATCH follows Semantic Versioning (SemVer):

- **MAJOR** (X.0.0): Breaking changes, incompatible API changes
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, backward compatible

### Pre-release Versions
- Alpha: `0.1.0-alpha.1`
- Beta: `0.1.0-beta.1`
- Release Candidate: `0.1.0-rc.1`
