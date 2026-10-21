# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅        |

## Reporting a Vulnerability

If you discover a security vulnerability in the Self-Audit skill, please report it responsibly:

1. **Do not open a public issue** for security vulnerabilities
2. Email the maintainer at: [security contact - to be added]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Considerations

### Skill Execution

- The skill runs with `context: fork` and `background: true`, isolating it from the main conversation
- `allowed-tools` grants specific Bash commands for the CLI wrapper only
- No network access unless explicitly configured
- No file system access outside workspace and `.claude/` directories

### Data Handling

- Calibration logs stored locally in `.claude/knowledge/calibration.log.jsonl`
- Memory files stored in `.claude/projects/<proj>/memory/`
- No data transmitted externally
- No credentials or secrets accessed

### Workspace Access

- Skill reads workspace files for convention sampling and assumption testing
- Only reads files relevant to calibration (source code, configs, docs, tests)
- Does not read sensitive files (`.env`, secrets, keys) unless explicitly in scope

## Best Practices for Users

1. Review `allowed-tools` in SKILL.md frontmatter before installing
2. Run in trusted workspaces only
3. Audit calibration logs periodically for unexpected entries
4. Keep Claude Code updated for security patches

## Known Limitations

- Cross-model validation spawns subagents (inherits parent session permissions)
- CLI scripts execute with workspace permissions
- Memory system writes to `.claude/` directory (ensure appropriate permissions)