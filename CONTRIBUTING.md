# Contributing to Self-Audit Skill

Thank you for your interest in contributing! This document outlines the guidelines for contributing to the Self-Audit skill.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/rexrayf3-prog/self-audit-skill/issues) first
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (OS, Claude Code version, Python version)
   - Relevant logs/error messages

### Suggesting Features

1. Open a [GitHub Discussion](https://github.com/rexrayf3-prog/self-audit-skill/discussions) for design discussion
2. For small improvements, a PR with clear description is welcome

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run validation: `claude plugin validate . --strict`
5. Run evals if possible: `claude plugin eval . --trust-plugin --threshold 0.8`
6. Submit PR with clear description

## Development Setup

```bash
# Clone
git clone https://github.com/rexrayf3-prog/self-audit-skill.git
cd self-audit-skill

# Install Claude Code
npm install -g @anthropic-ai/claude-code@latest

# Install Python dependencies (for scripts)
pip install -r requirements.txt  # if exists

# Validate
claude plugin validate . --strict --json

# Test skill locally
claude plugin install . --scope project --trust-plugin
/self-audit --mode quick
```

## Skill Development Guidelines

### SKILL.md Changes

- Keep body under 500 lines (reference `reference.md` for details)
- Update frontmatter `version` for significant changes
- Maintain epistemic discipline rules (non-negotiable)
- Test all 3 depth modes

### Adding New Phases/Features

1. Update `reference.md` with architecture changes
2. Add corresponding templates in `templates/`
3. Add eval cases in `evals/`
4. Update CLI scripts if needed
5. Update documentation in `docs/`

### CLI Scripts

- Keep scripts standalone runnable
- Use environment variables for configuration
- Output valid JSON/JSONL for machine consumption
- Handle errors gracefully with clear messages

## Testing

### Validation

```bash
# Plugin validation
claude plugin validate . --strict --json

# Skill validation
claude plugin validate ./skills/self-audit --strict --json
```

### Evals

```bash
# Full eval suite (requires ANTHROPIC_API_KEY)
claude plugin eval . --trust-plugin --threshold 0.8 --model claude-sonnet-5 --judge-model claude-haiku-4-5 --no-publish --max-cost-usd 10

# Single case
claude plugin eval . --trust-plugin --case case-quick-mode --threshold 0.8 --no-publish
```

### Manual Testing

Test on diverse workspaces:
- Python projects (FastAPI, Django, Flask)
- TypeScript/JavaScript (Next.js, React, Node)
- Go, Rust, Java projects
- Monorepos, polyglot repos
- Projects with/without existing `.claude/` structure

## Documentation

- Update `README.md` for user-facing changes
- Update `docs/` for architecture/configuration/integration changes
- Update `CHANGELOG.md` with each release
- Keep `examples.md` current with new features

## Release Process

Releases are automated via GitHub Actions on tag push (`v*`).

1. Update version in `plugin.json` (or let release workflow do it)
2. Update `CHANGELOG.md`
3. Create and push tag: `git tag v1.0.1 && git push origin v1.0.1`
4. GitHub Action creates release, runs validation, verifies installable

## Questions?

Open a [GitHub Discussion](https://github.com/rexrayf3-prog/self-audit-skill/discussions) or issue.