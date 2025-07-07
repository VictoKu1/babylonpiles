#!/bin/bash

# BabylonPiles Storage Access Script
# This script helps you access Docker volume data from your local file system

echo "=== BabylonPiles Storage Access ==="
echo

# Function to show volume info
show_volume_info() {
    local volume_name=$1
    local description=$2
    
    echo "📁 $description"
    echo "   Volume: $volume_name"
    
    # Get volume path
    local volume_path=$(docker volume inspect $volume_name --format '{{.Mountpoint}}' 2>/dev/null)
    if [ -n "$volume_path" ]; then
        echo "   Location: $volume_path"
        echo "   Size: $(du -sh $volume_path 2>/dev/null | cut -f1)"
    else
        echo "   Status: Not created yet"
    fi
    echo
}

# Function to copy data from volume to local directory
copy_from_volume() {
    local volume_name=$1
    local local_path=$2
    local description=$3
    
    echo "📋 Copying $description from Docker volume to local directory..."
    
    # Create local directory if it doesn't exist
    mkdir -p "$local_path"
    
    # Create temporary container to copy data
    docker run --rm -v "$volume_name:/source" -v "$(pwd)/$local_path:/dest" alpine sh -c "
        if [ -d /source ] && [ \"\$(ls -A /source)\" ]; then
            cp -r /source/* /dest/ 2>/dev/null || true
            echo '✅ Data copied successfully'
        else
            echo '⚠️  Volume is empty or does not exist'
        fi
    "
    echo
}

# Function to copy data from local directory to volume
copy_to_volume() {
    local local_path=$1
    local volume_name=$2
    local description=$3
    
    echo "📋 Copying $description from local directory to Docker volume..."
    
    if [ -d "$local_path" ] && [ "$(ls -A $local_path 2>/dev/null)" ]; then
        # Create temporary container to copy data
        docker run --rm -v "$(pwd)/$local_path:/source" -v "$volume_name:/dest" alpine sh -c "
            cp -r /source/* /dest/ 2>/dev/null || true
            echo '✅ Data copied successfully'
        "
    else
        echo "⚠️  Local directory is empty or does not exist"
    fi
    echo
}

# Show current volume information
echo "🔍 Current Docker Volumes:"
show_volume_info "babylonpiles_data" "Backend Data (SQLite, etc.)"
show_volume_info "babylonpiles_piles" "ZIM Files and Pile Content"
show_volume_info "babylonpiles_storage" "Storage Service Data"
show_volume_info "babylonpiles_service_data" "Storage Service Internal Data"

# Menu
echo "📋 Available Actions:"
echo "1. Copy all data from Docker volumes to local storage/project_storage/"
echo "2. Copy data from local storage/project_storage/ to Docker volumes"
echo "3. Show volume details"
echo "4. Open volume in file manager (if available)"
echo "5. Exit"
echo

read -p "Choose an action (1-5): " choice

case $choice in
    1)
        echo "📥 Copying data FROM Docker volumes TO local directory..."
        copy_from_volume "babylonpiles_data" "storage/project_storage/data" "Backend Data"
        copy_from_volume "babylonpiles_piles" "storage/project_storage/piles" "ZIM Files"
        copy_from_volume "babylonpiles_storage" "storage/project_storage/info" "Storage Service Data"
        copy_from_volume "babylonpiles_service_data" "storage/project_storage/service_data" "Service Internal Data"
        echo "✅ All data copied to storage/project_storage/"
        ;;
    2)
        echo "📤 Copying data FROM local directory TO Docker volumes..."
        copy_to_volume "storage/project_storage/data" "babylonpiles_data" "Backend Data"
        copy_to_volume "storage/project_storage/piles" "babylonpiles_piles" "ZIM Files"
        copy_to_volume "storage/project_storage/info" "babylonpiles_storage" "Storage Service Data"
        copy_to_volume "storage/project_storage/service_data" "babylonpiles_service_data" "Service Internal Data"
        echo "✅ All data copied to Docker volumes"
        ;;
    3)
        echo "🔍 Detailed volume information:"
        docker volume ls | grep babylonpiles
        echo
        for volume in babylonpiles_data babylonpiles_piles babylonpiles_storage babylonpiles_service_data; do
            echo "=== $volume ==="
            docker volume inspect $volume 2>/dev/null || echo "Volume not found"
            echo
        done
        ;;
    4)
        echo "🔍 Opening volume locations in file manager..."
        for volume in babylonpiles_data babylonpiles_piles babylonpiles_storage babylonpiles_service_data; do
            volume_path=$(docker volume inspect $volume --format '{{.Mountpoint}}' 2>/dev/null)
            if [ -n "$volume_path" ]; then
                echo "Opening: $volume_path"
                if command -v xdg-open >/dev/null 2>&1; then
                    xdg-open "$volume_path" 2>/dev/null &
                elif command -v open >/dev/null 2>&1; then
                    open "$volume_path" 2>/dev/null &
                elif command -v explorer >/dev/null 2>&1; then
                    explorer "$volume_path" 2>/dev/null &
                else
                    echo "File manager not available. Path: $volume_path"
                fi
            fi
        done
        ;;
    5)
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo
echo "💡 Tips:"
echo "- Docker volumes are faster and don't slow down builds"
echo "- Use this script to backup/restore data when needed"
echo "- Volumes persist even when containers are removed"
echo "- Use 'docker volume ls' to see all volumes" 