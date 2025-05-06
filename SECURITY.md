# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Auto Vertical Spread Trader, please email [your-email@example.com](mailto:your-email@example.com) with details. We take all security issues seriously and will respond promptly.

Please do not disclose security vulnerabilities publicly until we've had a chance to address them.

## Security Review Checklist

### For Contributors

When contributing to this project, please ensure your changes adhere to these security guidelines:

1. **Credentials & Sensitive Data**
   - Never commit API keys, passwords, or tokens
   - Use environment variables for all sensitive configuration
   - Check your PR diff carefully for accidental credential leaks

2. **Dependency Management**
   - Only add dependencies that are actively maintained
   - Specify minimum version requirements for security patches
   - Review new dependency licenses before adding them

3. **Input Validation**
   - Validate all user and third-party input
   - Sanitize file paths and URLs
   - Use safe data parsing methods

4. **Error Handling & Logging**
   - Don't expose sensitive information in error messages
   - Implement appropriate exception handling
   - Sanitize log output to avoid credential leakage

5. **API Security**
   - Always use HTTPS for API connections
   - Implement rate limiting when making external API calls
   - Validate API responses before processing

### For Maintainers

Periodic security audits should include:

1. **Dependency Scanning**
   - Run `pip-audit` or similar tools regularly
   - Monitor GitHub security alerts
   - Update dependencies promptly when security patches are released

2. **CI/CD Security**
   - Review GitHub Actions workflows for security issues
   - Ensure secrets are properly stored in repository settings
   - Validate that test/build artifacts don't contain sensitive data

3. **Code Review Guidelines**
   - Conduct thorough security reviews for code touching authentication
   - Check for SQL injection in database queries
   - Verify proper error handling

## Security Tools

We recommend using these tools to maintain security:

- [pip-audit](https://pypi.org/project/pip-audit/) - For scanning dependencies
- [bandit](https://pypi.org/project/bandit/) - For Python code security scanning
- [pre-commit](https://pre-commit.com/) - For running security checks locally 