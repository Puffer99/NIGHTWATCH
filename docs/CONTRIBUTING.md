# Contributing to NIGHTWATCH

Thank you for your interest in contributing to NIGHTWATCH! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and constructive in all interactions. We're building software that controls expensive equipment in remote locations - quality and safety are paramount.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/NIGHTWATCH.git`
3. Create a virtual environment: `python -m venv venv && source venv/bin/activate`
4. Install dev dependencies: `pip install -r services/requirements.txt && pip install pytest ruff mypy`
5. Create a branch: `git checkout -b feature/your-feature-name`

## Branch Naming

Use descriptive branch names with prefixes:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation only
- `refactor/` - Code refactoring
- `test/` - Test additions/changes

Examples:
- `feature/voice-volume-control`
- `fix/weather-timeout-handling`
- `docs/installation-guide`

## Git Workflow

### Branch Protection (Recommended for Repository Admins)

For the `main` branch, we recommend enabling:

1. **Require pull request reviews**
   - At least 1 approval required
   - Dismiss stale reviews on new commits

2. **Require status checks**
   - Unit tests must pass
   - Linting must pass

3. **Require branches to be up to date**
   - Branch must be current with main before merging

4. **Restrict force pushes**
   - Prevent rewriting history on main

### Setting Up Branch Protection

Repository admins can configure this at:
`Settings > Branches > Add branch protection rule`

Rule pattern: `main`

Recommended settings:
```
[x] Require a pull request before merging
    [x] Require approvals: 1
    [x] Dismiss stale pull request approvals when new commits are pushed
[x] Require status checks to pass before merging
    [x] Require branches to be up to date before merging
    Status checks: unit-tests, lint
[x] Do not allow bypassing the above settings
```

## Making Changes

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Run `ruff check` before committing
- Maximum line length: 100 characters

### Testing

- Write tests for new functionality
- Ensure existing tests pass: `pytest tests/`
- Aim for good coverage on safety-critical code

### Documentation

- Add docstrings to public functions and classes
- Update relevant documentation if behavior changes
- Include voice command examples for new features

## Pull Request Process

1. **Update your branch** with the latest main:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Run tests locally**:
   ```bash
   pytest tests/unit/ -v
   ruff check services/ voice/
   ```

3. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create a Pull Request**:
   - Use the PR template
   - Link related issues
   - Add appropriate labels
   - Request review from maintainers

5. **Address feedback**:
   - Respond to review comments
   - Make requested changes
   - Re-request review when ready

## Safety-Critical Code

Code that affects telescope movement, enclosure operation, or safety systems requires extra scrutiny:

### Requirements for Safety Changes

- Explicit review from a maintainer familiar with the safety architecture
- Test coverage for error conditions and edge cases
- Documentation of safety implications
- No bypassing of existing safety interlocks without explicit approval

### Safety Principles

1. **Fail safe**: When in doubt, park the telescope and close the roof
2. **Defense in depth**: Multiple layers of safety checks
3. **User confirmation**: Destructive actions require explicit confirmation
4. **Weather priority**: Weather safety always takes precedence
5. **Graceful degradation**: System should remain safe even with partial failures

## Commit Messages

Write clear, descriptive commit messages:

```
Short summary (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain what and why, not how (the code shows how).

- Bullet points are okay
- Use present tense: "Add feature" not "Added feature"

Fixes #123
```

## Release Process

Releases are managed by maintainers following the release checklist in `docs/RELEASE_CHECKLIST.md`.

## Questions?

- Open a Discussion for general questions
- Open an Issue for bugs or feature requests
- Check existing documentation first

Thank you for contributing to NIGHTWATCH!
