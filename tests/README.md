# BabylonPiles Test Suite

This directory contains comprehensive test scripts for BabylonPiles functionality. All tests are designed to validate the system's features and ensure reliability.

## 🧪 Test Files Overview

### Core Functionality Tests

#### `test_storage_api.py`
**Purpose**: Tests the storage API endpoints and functionality
- **Features Tested**:
  - Storage status retrieval
  - Drive scanning and management
  - Storage calculations and metrics
  - Multi-location storage allocation
- **Usage**: `python tests/test_storage_api.py`

#### `test_storage_calculation.py`
**Purpose**: Validates storage calculation accuracy
- **Features Tested**:
  - File size calculations
  - Directory size computations
  - Storage space validation
  - Disk usage accuracy
- **Usage**: `python tests/test_storage_calculation.py`

#### `test_download_functionality.py`
**Purpose**: Tests content download and pile management
- **Features Tested**:
  - Pile download functionality
  - Download progress tracking
  - Content source validation
  - Download error handling
- **Usage**: `python tests/test_download_functionality.py`

### User Management Tests

#### `test_user_config.py`
**Purpose**: Tests user configuration and settings
- **Features Tested**:
  - User profile management
  - Configuration persistence
  - Settings validation
  - User preferences
- **Usage**: `python tests/test_user_config.py`

#### `test_permissions.py`
**Purpose**: Tests file permission management
- **Features Tested**:
  - File permission toggling
  - Public/private file access
  - Permission validation
  - Error handling for permissions
- **Usage**: `python tests/test_permissions.py`

### System Integration Tests

#### `test_hotspot.py`
**Purpose**: Tests WiFi hotspot functionality
- **Features Tested**:
  - Hotspot creation and management
  - Network configuration
  - Device connectivity
  - Hotspot security
- **Usage**: `python tests/test_hotspot.py`

#### `test_cross_platform.py`
**Purpose**: Tests cross-platform compatibility
- **Features Tested**:
  - Docker container functionality
  - Platform-specific features
  - Cross-platform file operations
  - System compatibility
- **Usage**: `python tests/test_cross_platform.py`

#### `test_metadata.py`
**Purpose**: Tests metadata handling and content indexing
- **Features Tested**:
  - Content metadata extraction
  - File information parsing
  - Index management
  - Metadata validation
- **Usage**: `python tests/test_metadata.py`

## 🚀 Running Tests

### Prerequisites
- BabylonPiles backend running on `http://localhost:8080`
- Docker containers started
- Python 3.7+ with required dependencies

### Individual Test Execution
```bash
# Run a specific test
python tests/test_storage_api.py

# Run all tests using the test runner
python tests/run_all_tests.py

# Run all tests (if you have a test runner)
python -m pytest tests/
```

### Test Categories

#### **API Tests**
- `test_storage_api.py` - Storage API functionality
- `test_permissions.py` - Permission management

#### **System Tests**
- `test_hotspot.py` - Network and hotspot features
- `test_cross_platform.py` - Platform compatibility

#### **Functionality Tests**
- `test_storage_calculation.py` - Storage calculations
- `test_download_functionality.py` - Content downloads
- `test_user_config.py` - User management
- `test_metadata.py` - Content metadata

## 📊 Test Results

### Expected Outcomes
- **API Tests**: Should return 200 status codes and expected data
- **System Tests**: Should validate system functionality without errors
- **Functionality Tests**: Should complete operations successfully

### Common Test Patterns
1. **Setup**: Initialize test environment
2. **Execution**: Perform test operations
3. **Validation**: Verify expected results
4. **Cleanup**: Restore original state

## 🔧 Test Configuration

### Environment Variables
```bash
# Test configuration
BASE_URL=http://localhost:8080
TEST_TIMEOUT=30
DEBUG_MODE=false
```

### Test Data
- Test files are created temporarily during tests
- Cleanup is performed automatically
- No permanent data is modified

## 📝 Writing New Tests

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
    print("🧪 Testing [Feature Name]")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test implementation
        pass

if __name__ == "__main__":
    asyncio.run(test_feature_name())
```

### Best Practices
1. **Clear Naming**: Use descriptive test names
2. **Isolation**: Tests should be independent
3. **Cleanup**: Always clean up test data
4. **Documentation**: Include clear descriptions
5. **Error Handling**: Proper error reporting

## 🐛 Troubleshooting

### Common Issues
1. **Connection Errors**: Ensure backend is running
2. **Timeout Errors**: Increase timeout values
3. **Permission Errors**: Check file permissions
4. **Docker Issues**: Verify containers are running
5. **Unicode Encoding Errors**: On Windows, tests may fail due to emoji characters

### Unicode Encoding Issues (Windows)
If you encounter Unicode encoding errors on Windows:
```bash
# Set UTF-8 encoding before running tests
set PYTHONIOENCODING=utf-8
python tests/run_all_tests.py

# Or use the test runner which handles encoding automatically
python tests/run_all_tests.py
```

### Debug Mode
Set `DEBUG_MODE=true` in test scripts for verbose output.

## 📈 Test Coverage

### Current Coverage
- ✅ Storage API functionality
- ✅ File permission management
- ✅ User configuration
- ✅ Hotspot functionality
- ✅ Cross-platform compatibility
- ✅ Download functionality
- ✅ Metadata handling
- ✅ Storage calculations

### Planned Tests
- 🔄 UI component testing
- 🔄 End-to-end user workflows
- 🔄 Performance testing
- 🔄 Security testing

## 🤝 Contributing

When adding new tests:
1. Follow the existing naming convention
2. Include comprehensive documentation
3. Ensure proper cleanup
4. Add to this README
5. Test thoroughly before committing

---

*These tests ensure BabylonPiles functionality and reliability across all features and platforms.* 