#!/bin/bash

echo "=== Docker Build Context Analysis ==="
echo

# Check total size of project directory
echo "Total project directory size:"
du -sh . 2>/dev/null | head -1
echo

# Check storage directory size
if [ -d "storage/project_storage" ]; then
    echo "Storage directory size:"
    du -sh storage/project_storage 2>/dev/null
    echo
    
    echo "Largest files in storage:"
    find storage/project_storage -type f -exec du -h {} + 2>/dev/null | sort -hr | head -10
    echo
fi

# Check what would be included in build context (excluding .dockerignore)
echo "Files that would be included in build context:"
echo "(This shows files that are NOT excluded by .dockerignore)"
echo

# Create a temporary file to test .dockerignore
if [ -f ".dockerignore" ]; then
    echo "Testing .dockerignore exclusions..."
    tar --exclude-from=.dockerignore -czf /tmp/build-context-test.tar.gz . 2>/dev/null
    echo "Build context size (after .dockerignore):"
    du -sh /tmp/build-context-test.tar.gz 2>/dev/null
    rm -f /tmp/build-context-test.tar.gz
else
    echo "No .dockerignore file found in root directory"
fi

echo
echo "=== Recommendations ==="
echo "1. Ensure .dockerignore excludes storage/project_storage/"
echo "2. Use 'docker-compose up -d' instead of 'docker-compose up --build -d' when possible"
echo "3. Only rebuild when you've changed code or dependencies" 