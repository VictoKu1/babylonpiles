# 🤝 Contributing to BabylonPiles

Thank you for your interest in contributing! We welcome all contributions—code, documentation, bug reports, and feature requests.

## 🚀 Quick Start for Contributors (Docker-Only)

The only supported way to develop and test BabylonPiles is with Docker. This ensures your environment matches production and other contributors.

### 1. Prerequisites
- Docker (with Docker Compose support)
- Git for version control
- Python 3.7+ for running tests

### 2. Clone the repository
```bash
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
```

### 3. Start the development environment
```bash
# Option 1: Use the unified script (recommended)
./babylonpiles.sh

# Option 2: Manual Docker commands
docker-compose up --build -d
```

**Note:** The unified script now includes multi-location storage allocation during startup, allowing you to configure specific storage locations for development.

### 4. Access the app
- Backend API: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- Frontend: http://localhost:3000

### 5. Making changes
- Edit code in your local repo as usual.
- Docker volumes ensure your changes are reflected in the running containers.
- Use `docker-compose restart` to restart services if needed.

### 6. Running tests
- **Test Suite**: All tests are located in the `tests/` directory
- **Individual Tests**: Run specific tests with `python tests/test_name.py`
- **Test Categories**: API, System, and Functionality tests
- **Prerequisites**: Ensure backend is running on `http://localhost:8080`
- **Documentation**: See [Test Suite README](tests/README.md) for detailed information

### 7. Writing new tests
- Follow the test structure in `tests/README.md`
- Use descriptive test names and clear documentation
- Ensure proper cleanup and error handling
- Add new tests to the test documentation

### 8. Running all tests
```bash
# Run the test suite
python tests/run_all_tests.py

# Run specific test categories
python tests/test_storage_api.py
python tests/test_permissions.py
```

---

## 📝 Code Style & Guidelines

### Python (Backend)
- Follow PEP8 for Python code
- Use type hints where possible
- Write docstrings for all functions and classes
- Use async/await for asynchronous operations
- Handle exceptions properly with meaningful error messages

### TypeScript/React (Frontend)
- Use TypeScript for type safety
- Follow React best practices
- Use functional components with hooks
- Implement proper error boundaries
- Write meaningful component documentation

### General Guidelines
- Use clear, descriptive commit messages
- Write comprehensive docstrings and comments
- Follow the existing code structure and patterns
- Test your changes thoroughly
- Update documentation when adding new features

---

## 🧪 Testing Guidelines

### Test Structure
```python
#!/usr/bin/env python3
"""
Test script for [feature name]
"""

import asyncio
import aiohttp
import json

# Test configuration
BASE_URL = "http://localhost:8080"

async def test_feature_name():
    """Test description"""
    print("Testing [Feature Name]")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test implementation
        pass

if __name__ == "__main__":
    asyncio.run(test_feature_name())
```

### Test Best Practices
1. **Clear Naming**: Use descriptive test names
2. **Isolation**: Tests should be independent
3. **Cleanup**: Always clean up test data
4. **Documentation**: Include clear descriptions
5. **Error Handling**: Proper error reporting

### Test Categories
- **API Tests**: Test backend endpoints and responses
- **System Tests**: Test system functionality and integration
- **Functionality Tests**: Test specific features and workflows

---

## 🔧 Development Workflow

### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes
- Write your code following the style guidelines
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes
```bash
# Run all tests
python tests/run_all_tests.py

# Test specific functionality
python tests/test_your_feature.py
```

### 4. Commit Your Changes
```bash
git add .
git commit -m "feat: add your feature description"
```

### 5. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

---

## 📋 Pull Request Guidelines

### Before Submitting
- [ ] Code follows style guidelines
- [ ] Tests pass successfully
- [ ] Documentation is updated
- [ ] No breaking changes (or clearly documented)
- [ ] Error handling is implemented
- [ ] Security considerations addressed

### Pull Request Template
```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Test addition
- [ ] Performance improvement

## Testing
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Documentation
- [ ] README updated
- [ ] API docs updated (if applicable)
- [ ] Code comments added

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] No console errors
- [ ] Cross-platform compatibility verified
```

---

## 🐛 Bug Reports

### Bug Report Template
```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [Windows/Linux/macOS]
- Docker Version: [version]
- Browser: [if applicable]

## Additional Information
Screenshots, logs, or other relevant information
```

---

## 💡 Feature Requests

### Feature Request Template
```markdown
## Feature Description
Clear description of the requested feature

## Use Case
How this feature would be used

## Proposed Implementation
Optional: How you think this could be implemented

## Alternatives Considered
Other approaches that were considered

## Additional Information
Any other relevant information
```

---

## 🔒 Security

### Security Guidelines
- Never commit sensitive information (passwords, API keys)
- Use environment variables for configuration
- Validate all user inputs
- Implement proper authentication and authorization
- Follow security best practices for web applications

### Reporting Security Issues
- **DO NOT** create a public issue for security vulnerabilities
- Email security issues to the maintainers
- Include detailed information about the vulnerability
- Allow time for the issue to be addressed before public disclosure

---

## 📚 Documentation

### Documentation Guidelines
- Write clear, concise documentation
- Include examples where helpful
- Keep documentation up to date with code changes
- Use consistent formatting and style
- Include troubleshooting sections

### Documentation Structure
- **README.md**: Project overview and quick start
- **docs/**: Detailed documentation
- **tests/README.md**: Test documentation
- **API.md**: API reference
- **CONTRIBUTING.md**: Development guidelines

---

## 🎯 Contribution Areas

### High Priority
- **Bug Fixes**: Critical issues affecting functionality
- **Security Improvements**: Vulnerabilities and security enhancements
- **Performance Optimizations**: Speed and resource usage improvements
- **Documentation**: Improving guides and tutorials

### Medium Priority
- **Feature Enhancements**: Improving existing functionality
- **UI/UX Improvements**: Better user experience
- **Testing**: Adding more test coverage
- **Code Quality**: Refactoring and improvements

### Low Priority
- **Nice-to-have Features**: Non-critical enhancements
- **Documentation**: Additional guides and examples
- **Examples**: Sample content and configurations

---

## 🤝 Community

### Getting Help
- [Open an Issue](https://github.com/VictoKu1/babylonpiles/issues)
- Join our (coming soon) chat/Discord/Matrix
- Email the maintainers (see README)

### Ways to Contribute
- 🐛 **Report Bugs**: If you spot a bug, [open an Issue](https://github.com/VictoKu1/babylonpiles/issues)
- ✨ **Suggest Features**: Have an idea? Suggest it in [Discussions](https://github.com/VictoKu1/babylonpiles/discussions)
- 💻 **Code Contributions**: Submit bugfixes, improvements, or new features via Pull Request
- 📝 **Improve Documentation**: Better docs, guides, or translations
- 🌍 **Localization**: Help translate the UI or documentation
- 🧪 **Testing**: Help improve test coverage and quality

---

## 📄 License

By contributing to BabylonPiles, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for helping build the offline library of civilization!  
**The BabylonPiles Maintainers**
