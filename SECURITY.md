# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by opening an issue with the label `security`.

## Best Practices

- Never commit `.env` files with real API keys
- Use environment variables or a vault for secrets
- All secrets are gitignored by default (see `.gitignore`)
- Container secrets use Docker secrets or env files excluded from version control
