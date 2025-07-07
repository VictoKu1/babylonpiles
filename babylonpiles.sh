#!/bin/bash

# BabylonPiles Unified Management Script
# Interactive script for managing BabylonPiles with storage

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DOCKER_COMPOSE_FILE="docker-compose.yml"
MOUNT_BASE="/media"
DOCKER_MOUNT_BASE="/mnt"
API_BASE_URL="http://localhost:8080/api/v1"

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  BabylonPiles Management${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_step() {
    echo -e "${CYAN}→ $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running or user not in docker group"
        exit 1
    fi
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
}

check_api_available() {
    print_info "Checking if BabylonPiles API is available..."
    if curl -s --max-time 5 "$API_BASE_URL/storage/status" > /dev/null 2>&1; then
        print_success "BabylonPiles API is available"
        API_AVAILABLE=1
    else
        print_warning "BabylonPiles API is not available yet"
        API_AVAILABLE=0
    fi
}

start_services() {
    print_step "Starting BabylonPiles services..."
    
    # Stop any existing containers
    print_info "Stopping any existing containers..."
    docker-compose down
    
    # Build and start the services
    print_info "Building and starting services..."
    docker-compose up --build -d
    
    # Wait for services to be ready
    print_info "Waiting for services to start..."
    sleep 15
    
    # Check if services are running
    print_info "Checking service status..."
    docker-compose ps
    
    # Check API availability
    check_api_available
    
    # Show current storage configuration
    echo ""
    show_current_storage
    
    # Ask user if they want to allocate additional storage
    if [ "$API_AVAILABLE" -eq 1 ]; then
        echo ""
        print_info "You can manage storage through the web interface or continue here."
        read -p "Would you like to add storage locations now? (y/N): " add_more
        if [[ $add_more =~ ^[Yy]$ ]]; then
            allocate_system_drive
        fi
    else
        echo ""
        print_info "System Drive Allocation"
        print_info "Would you like to allocate specific storage locations?"
        list_available_drives
        
        read -p "Allocate storage locations now? (y/N): " allocate_drive
        if [[ $allocate_drive =~ ^[Yy]$ ]]; then
            allocate_system_drive
        fi
    fi
    
    # Show logs
    print_info "Recent logs:"
    docker-compose logs --tail=20
    
    print_success "BabylonPiles is now running!"
    echo ""
    echo -e "${GREEN}🌐 Backend API: http://localhost:8080${NC}"
    echo -e "${GREEN}📚 API Documentation: http://localhost:8080/docs${NC}"
    echo -e "${GREEN}🎨 Frontend: http://localhost:3000${NC}"
    echo -e "${GREEN}💾 Storage Management: Dashboard → Storage${NC}"
    echo ""
}

stop_services() {
    print_step "Stopping BabylonPiles services..."
    docker-compose down
    print_success "Services stopped"
}

restart_services() {
    print_step "Restarting BabylonPiles services..."
    docker-compose restart
    print_success "Services restarted"
}

show_status() {
    print_step "Checking service status..."
    docker-compose ps
    
    echo ""
    print_info "Storage Configuration:"
    show_current_storage
    
    echo ""
    print_info "Storage Status:"
    if [ "$API_AVAILABLE" -eq 1 ]; then
        storage_status=$(curl -s "$API_BASE_URL/storage/status" 2>/dev/null || echo "{}")
        if echo "$storage_status" | grep -q "total_drives"; then
            echo "$storage_status" | jq '.' 2>/dev/null || echo "$storage_status"
        else
            print_warning "Could not reach storage service"
        fi
    else
        print_warning "Storage API not available yet"
    fi
}

show_logs() {
    print_step "Showing recent logs..."
    docker-compose logs --tail=50
}

show_storage_logs() {
    print_step "Showing storage service logs..."
    docker-compose logs --tail=50 storage
}

list_available_drives() {
    print_info "Available Hardware Drives:"
    echo
    lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E "(sd|hd|nvme)"
    echo
}

list_mounted_drives() {
    print_info "Currently mounted drives:"
    echo
    if [ -d "$MOUNT_BASE" ]; then
        ls -la "$MOUNT_BASE" | grep hdd
    else
        print_warning "No mounted drives found"
    fi
    echo
}

show_current_storage() {
    print_info "Current Storage Configuration:"
    echo
    
    # Check API availability first
    check_api_available
    
    if [ "$API_AVAILABLE" -eq 1 ]; then
        # Get drives from storage service API
        print_info "Fetching current drives from storage service..."
        drives_response=$(curl -s "$API_BASE_URL/storage/drives" 2>/dev/null || echo "{}")
        
        if echo "$drives_response" | grep -q "drives" && [ "$(echo "$drives_response" | jq -r '.drives | length')" -gt 0 ]; then
            print_info "Current drives from storage service:"
            echo "$drives_response" | jq -r '.drives[] | "  Drive \(.id): \(.path) (\((.total_space/1024/1024/1024) | floor)GB total, \((.free_space/1024/1024/1024) | floor)GB free)"' 2>/dev/null || echo "$drives_response"
        else
            print_info "No drives currently configured in storage service"
        fi
    else
        print_warning "Storage API not available - showing docker-compose configuration only"
    fi
    
    # Also show docker-compose.yml configuration as backup
    print_info "Docker-compose.yml storage mounts:"
    echo
    existing_mounts=""
    mount_count=0
    
    while IFS= read -r line; do
        if [[ $line =~ ^[[:space:]]*-[[:space:]]*(.+):(.+)$ ]]; then
            host_path="${BASH_REMATCH[1]}"
            docker_path="${BASH_REMATCH[2]}"
            if [[ $docker_path == /mnt/hdd* ]]; then
                ((mount_count++))
                if [ -z "$existing_mounts" ]; then
                    existing_mounts="$host_path"
                else
                    existing_mounts="$existing_mounts;$host_path"
                fi
                print_info "  Storage Location $mount_count: $host_path -> $docker_path"
            fi
        fi
    done < <(grep -A 10 "storage:" "$DOCKER_COMPOSE_FILE" | grep "volumes:" -A 10 | grep "^-")
    
    if [ -z "$existing_mounts" ]; then
        print_info "No existing storage locations configured in docker-compose.yml"
        has_existing=0
    else
        print_info "Found $mount_count existing storage location(s) in docker-compose.yml"
        has_existing=1
    fi
    echo
}

show_storage_comparison() {
    print_info "Storage Drive Comparison"
    echo
    
    # Show available hardware drives
    print_info "Available Hardware Drives:"
    echo
    lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E "(sd|hd|nvme)"
    echo
    
    # Show current storage service drives
    print_info "Currently Used Storage Locations (from storage service):"
    echo
    check_api_available
    if [ "$API_AVAILABLE" -eq 1 ]; then
        drives_response=$(curl -s "$API_BASE_URL/storage/drives" 2>/dev/null || echo "{}")
        if echo "$drives_response" | grep -q "drives" && [ "$(echo "$drives_response" | jq -r '.drives | length')" -gt 0 ]; then
            echo "$drives_response" | jq -r '.drives[] | "  \(.id): \(.path) (\((.total_space/1024/1024/1024) | floor)GB total, \((.free_space/1024/1024/1024) | floor)GB free)"' 2>/dev/null || echo "$drives_response"
        else
            print_info "  No drives currently configured"
        fi
    else
        print_info "  Storage API not available"
    fi
    echo
}

get_next_drive_number() {
    local max_num=0
    for i in {1..10}; do
        if [ -d "$MOUNT_BASE/hdd$i" ]; then
            max_num=$i
        fi
    done
    echo $((max_num + 1))
}

add_drive() {
    print_header
    print_info "Adding a new storage drive"
    echo
    
    # Show current storage configuration and available drives
    show_current_storage
    show_storage_comparison
    
    # List available drives
    list_available_drives
    
    # Get drive selection
    read -p "Enter the device name (e.g., sdb1, sdc1): " device_name
    
    if [ -z "$device_name" ]; then
        print_error "Device name is required"
        return 1
    fi
    
    # Check if device exists
    if [ ! -b "/dev/$device_name" ]; then
        print_error "Device /dev/$device_name does not exist"
        return 1
    fi
    
    # Get next drive number
    local drive_num=$(get_next_drive_number)
    local mount_point="$MOUNT_BASE/hdd$drive_num"
    
    print_info "Will mount /dev/$device_name to $mount_point"
    
    # Confirm action
    read -p "Continue? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_info "Operation cancelled"
        return 0
    fi
    
    # Create mount point
    print_info "Creating mount point..."
    sudo mkdir -p "$mount_point"
    
    # Mount the drive
    print_info "Mounting drive..."
    sudo mount "/dev/$device_name" "$mount_point"
    
    # Set permissions
    print_info "Setting permissions..."
    sudo chown -R 1000:1000 "$mount_point"
    sudo chmod 755 "$mount_point"
    
    # Update docker-compose.yml
    print_info "Updating docker-compose.yml..."
    local docker_mount="$DOCKER_MOUNT_BASE/hdd$drive_num"
    
    # Add volume mount to docker-compose.yml
    if ! grep -q "$docker_mount" "$DOCKER_COMPOSE_FILE"; then
        # Find the storage service volumes section
        local line_num=$(grep -n "volumes:" "$DOCKER_COMPOSE_FILE" | grep -A 10 "storage" | head -1 | cut -d: -f1)
        
        if [ -n "$line_num" ]; then
            # Insert the new volume mount
            sed -i "${line_num}a\      - $mount_point:$docker_mount" "$DOCKER_COMPOSE_FILE"
            print_success "Added volume mount to docker-compose.yml"
        else
            print_warning "Could not automatically update docker-compose.yml"
            print_info "Please manually add: - $mount_point:$docker_mount"
        fi
    else
        print_warning "Volume mount already exists in docker-compose.yml"
    fi
    
    # Update MAX_DRIVES
    local current_max=$(grep "MAX_DRIVES=" "$DOCKER_COMPOSE_FILE" | cut -d= -f2)
    local new_max=$((current_max + 1))
    sed -i "s/MAX_DRIVES=$current_max/MAX_DRIVES=$new_max/" "$DOCKER_COMPOSE_FILE"
    print_success "Updated MAX_DRIVES to $new_max"
    
    # Restart storage service
    print_info "Restarting storage service..."
    docker-compose restart storage
    
    # Wait for storage service to be ready and scan for new drives
    print_info "Waiting for storage service to restart..."
    sleep 10
    
    check_api_available
    if [ "$API_AVAILABLE" -eq 1 ]; then
        print_info "Triggering drive scan in storage service..."
        curl -s -X POST "$API_BASE_URL/storage/drives/scan" > /dev/null 2>&1 || print_warning "Drive scan failed"
    fi
    
    print_success "Drive added successfully!"
    print_info "Drive is mounted at: $mount_point"
    print_info "Docker mount point: $docker_mount"
    print_info "Drive number: hdd$drive_num"
}

remove_drive() {
    print_header
    print_info "Removing a storage drive"
    echo
    
    # Show current storage configuration
    show_current_storage
    show_storage_comparison
    
    # List mounted drives
    list_mounted_drives
    
    # Get drive selection
    read -p "Enter the drive number to remove (e.g., 1, 2, 3): " drive_num
    
    if [ -z "$drive_num" ]; then
        print_error "Drive number is required"
        return 1
    fi
    
    local mount_point="$MOUNT_BASE/hdd$drive_num"
    
    if [ ! -d "$mount_point" ]; then
        print_error "Drive hdd$drive_num is not mounted"
        return 1
    fi
    
    print_warning "This will unmount drive hdd$drive_num at $mount_point"
    print_warning "Make sure to migrate any data first!"
    
    # Confirm action
    read -p "Continue? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_info "Operation cancelled"
        return 0
    fi
    
    # Unmount the drive
    print_info "Unmounting drive..."
    sudo umount "$mount_point"
    
    # Remove mount point
    print_info "Removing mount point..."
    sudo rmdir "$mount_point"
    
    # Update docker-compose.yml
    print_info "Updating docker-compose.yml..."
    local docker_mount="$DOCKER_MOUNT_BASE/hdd$drive_num"
    
    # Remove volume mount from docker-compose.yml
    sed -i "/$mount_point:$docker_mount/d" "$DOCKER_COMPOSE_FILE"
    print_success "Removed volume mount from docker-compose.yml"
    
    # Update MAX_DRIVES
    local current_max=$(grep "MAX_DRIVES=" "$DOCKER_COMPOSE_FILE" | cut -d= -f2)
    local new_max=$((current_max - 1))
    sed -i "s/MAX_DRIVES=$current_max/MAX_DRIVES=$new_max/" "$DOCKER_COMPOSE_FILE"
    print_success "Updated MAX_DRIVES to $new_max"
    
    # Restart storage service
    print_info "Restarting storage service..."
    docker-compose restart storage
    
    # Wait for storage service to be ready and scan for drives
    print_info "Waiting for storage service to restart..."
    sleep 10
    
    check_api_available
    if [ "$API_AVAILABLE" -eq 1 ]; then
        print_info "Triggering drive scan in storage service..."
        curl -s -X POST "$API_BASE_URL/storage/drives/scan" > /dev/null 2>&1 || print_warning "Drive scan failed"
    fi
    
    print_success "Drive removed successfully!"
}

allocate_system_drive() {
    print_header
    print_info "Allocating Storage Locations"
    echo
    
    # Show existing storage configuration
    show_current_storage
    
    # Show drive comparison when user is actually allocating storage
    show_storage_comparison
    
    echo ""
    print_info "You can choose multiple storage locations:"
    echo "  - A whole drive (e.g., /dev/sdb1)"
    echo "  - A specific folder (e.g., /media/data)"
    echo "  - A subfolder (e.g., /home/user/babylonpiles)"
    echo ""
    
    # Initialize storage locations array
    storage_locations=()
    location_count=0
    
    while true; do
        ((location_count++))
        echo ""
        print_info "Adding Storage Location #$location_count"
        
        read -p "Enter storage path (e.g., /dev/sdb1, /media/data, /home/user/babylonpiles): " storage_path
        
        if [ -z "$storage_path" ]; then
            print_error "Storage path is required"
            return 1
        fi
        
        # Check if path exists
        if [ ! -e "$storage_path" ]; then
            print_warning "Path $storage_path does not exist"
            read -p "Create this path? (y/N): " create_path
            if [[ $create_path =~ ^[Yy]$ ]]; then
                print_info "Creating path: $storage_path"
                sudo mkdir -p "$storage_path"
                if [ $? -ne 0 ]; then
                    print_error "Failed to create path $storage_path"
                    return 1
                fi
            else
                print_info "Skipping this location"
                ((location_count--))
                continue
            fi
        fi
        
        # Check available space
        if [ -d "$storage_path" ]; then
            free_space=$(df -h "$storage_path" | awk 'NR==2 {print $4}')
            print_info "Available space at $storage_path: $free_space"
        fi
        
        # Add to storage locations array
        storage_locations+=("$storage_path")
        print_success "Added storage location: $storage_path"
        
        echo ""
        read -p "Add another storage location? (y/N): " more_locations
        if [[ ! $more_locations =~ ^[Yy]$ ]]; then
            break
        fi
    done
    
    # Show summary of all storage locations
    echo ""
    print_info "Storage Configuration Summary:"
    print_info "Total locations: $location_count"
    for location in "${storage_locations[@]}"; do
        print_info "  - $location"
    done
    
    read -p "Continue with this storage configuration? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_info "Storage allocation cancelled"
        return 0
    fi
    
    # Create mount points for each storage location
    print_info "Setting up storage mounts..."
    docker_mounts=()
    
    for location in "${storage_locations[@]}"; do
        # Find next available mount number
        mount_num=1
        for i in {1..10}; do
            if [ ! -d "$MOUNT_BASE/hdd$i" ]; then
                mount_num=$i
                break
            fi
        done
        
        mount_point="$MOUNT_BASE/hdd$mount_num"
        docker_mount="$DOCKER_MOUNT_BASE/hdd$mount_num"
        
        print_info "Creating mount point: $mount_point -> $location"
        sudo mkdir -p "$mount_point"
        
        # Handle different types of storage locations
        if [[ $location == /dev/* ]]; then
            # It's a device, mount it
            print_info "Mounting device $location to $mount_point"
            sudo mount "$location" "$mount_point"
            sudo chown -R 1000:1000 "$mount_point"
            sudo chmod 755 "$mount_point"
        else
            # It's a directory, copy contents or create symlink
            if [ -d "$location" ] && [ "$(ls -A "$location" 2>/dev/null)" ]; then
                print_info "Copying contents from $location"
                sudo cp -r "$location"/* "$mount_point/" 2>/dev/null || true
            fi
            # Create symbolic link to the actual location
            sudo ln -sf "$location" "$mount_point/link" 2>/dev/null || true
        fi
        
        docker_mounts+=("$mount_point:$docker_mount")
    done
    
    # Update docker-compose.yml with all storage mounts
    print_info "Updating docker-compose.yml..."
    for mount in "${docker_mounts[@]}"; do
        IFS=':' read -r host_path docker_path <<< "$mount"
        
        # Check if mount already exists
        if ! grep -q "$docker_path" "$DOCKER_COMPOSE_FILE"; then
            # Find the storage service volumes section and add mount
            local line_num=$(grep -n "volumes:" "$DOCKER_COMPOSE_FILE" | grep -A 10 "storage" | head -1 | cut -d: -f1)
            if [ -n "$line_num" ]; then
                sed -i "${line_num}a\      - $host_path:$docker_path" "$DOCKER_COMPOSE_FILE"
                print_success "Added mount: $host_path -> $docker_path"
            else
                print_warning "Could not automatically add mount: $host_path -> $docker_path"
            fi
        else
            print_warning "Mount already exists: $docker_path"
        fi
    done
    
    # Update MAX_DRIVES to match the number of locations
    sed -i "s/MAX_DRIVES=[0-9]*/MAX_DRIVES=$location_count/" "$DOCKER_COMPOSE_FILE"
    print_success "Updated MAX_DRIVES to $location_count"
    
    # Restart storage service to pick up new mounts
    print_info "Restarting storage service..."
    docker-compose restart storage
    
    # Wait for storage service to be ready and scan for drives
    print_info "Waiting for storage service to restart..."
    sleep 10
    
    check_api_available
    if [ "$API_AVAILABLE" -eq 1 ]; then
        print_info "Triggering drive scan in storage service..."
        curl -s -X POST "$API_BASE_URL/storage/drives/scan" > /dev/null 2>&1 || print_warning "Drive scan failed"
    fi
    
    print_success "Storage allocation completed successfully!"
    print_info "Total storage locations: $location_count"
    print_info "All data will be distributed across these locations"
    echo ""
}

scan_drives() {
    print_step "Scanning for new drives..."
    
    check_api_available
    if [ "$API_AVAILABLE" -eq 1 ]; then
        local api_url="$API_BASE_URL/storage/drives/scan"
        
        print_info "Calling storage service..."
        response=$(curl -s -X POST "$api_url" 2>/dev/null || echo "{}")
        
        if echo "$response" | grep -q "drives"; then
            print_success "Drive scan completed successfully"
            echo "$response" | jq '.' 2>/dev/null || echo "$response"
        else
            print_warning "Scan failed or could not reach storage service"
        fi
    else
        print_warning "Storage API not available"
    fi
    
    print_success "Drive scan completed"
}

setup_auto_mount() {
    print_header
    print_info "Setting up auto-mount for drives"
    echo
    
    print_info "This will add entries to /etc/fstab for automatic mounting"
    print_warning "Make sure drives are properly formatted first!"
    
    # List available drives
    list_available_drives
    
    read -p "Enter the device name (e.g., sdb1, sdc1): " device_name
    
    if [ -z "$device_name" ]; then
        print_error "Device name is required"
        return 1
    fi
    
    # Check if device exists
    if [ ! -b "/dev/$device_name" ]; then
        print_error "Device /dev/$device_name does not exist"
        return 1
    fi
    
    # Get UUID
    local uuid=$(sudo blkid -s UUID -o value "/dev/$device_name")
    if [ -z "$uuid" ]; then
        print_error "Could not get UUID for device"
        return 1
    fi
    
    # Get next drive number
    local drive_num=$(get_next_drive_number)
    local mount_point="$MOUNT_BASE/hdd$drive_num"
    
    print_info "Device UUID: $uuid"
    print_info "Mount point: $mount_point"
    
    # Confirm action
    read -p "Continue? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_info "Operation cancelled"
        return 0
    fi
    
    # Create mount point
    sudo mkdir -p "$mount_point"
    
    # Add to fstab
    local fstab_entry="UUID=$uuid $mount_point ext4 defaults 0 2"
    echo "$fstab_entry" | sudo tee -a /etc/fstab
    
    # Test mount
    print_info "Testing mount..."
    sudo mount -a
    
    # Set permissions
    sudo chown -R 1000:1000 "$mount_point"
    sudo chmod 755 "$mount_point"
    
    print_success "Auto-mount configured successfully!"
    print_info "Drive will be mounted automatically on boot"
}

test_storage() {
    print_step "Testing storage API endpoints..."
    
    if command -v python3 &> /dev/null; then
        if [ -f "test_storage_api.py" ]; then
            python3 test_storage_api.py
        else
            print_warning "test_storage_api.py not found"
        fi
    else
        print_warning "Python3 not available for testing"
    fi
}

show_help() {
    print_header
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  start         Start all BabylonPiles services"
    echo "  stop          Stop all services"
    echo "  restart       Restart all services"
    echo "  status        Show service status and storage info"
    echo "  logs          Show recent logs"
    echo "  storage-logs  Show storage service logs only"
    echo "  add-drive     Add a new storage drive"
    echo "  remove-drive  Remove a storage drive"
    echo "  scan-drives   Scan for new drives"
    echo "  auto-mount    Setup auto-mount for drives"
    echo "  test          Test storage API endpoints"
    echo "  interactive   Interactive mode (default)"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 add-drive"
    echo "  $0 status"
    echo "  $0            # Interactive mode"
}

interactive_menu() {
    while true; do
        print_header
        echo "Choose an option:"
        echo ""
        echo -e "${GREEN}1)${NC} Start BabylonPiles services"
        echo -e "${GREEN}2)${NC} Stop all services"
        echo -e "${GREEN}3)${NC} Restart services"
        echo -e "${GREEN}4)${NC} Show status"
        echo -e "${GREEN}5)${NC} Show logs"
        echo -e "${GREEN}6)${NC} Show storage logs"
        echo ""
        echo -e "${YELLOW}7)${NC} Add storage drive"
        echo -e "${YELLOW}8)${NC} Remove storage drive"
        echo -e "${YELLOW}9)${NC} Scan for new drives"
        echo -e "${YELLOW}10)${NC} Setup auto-mount"
        echo -e "${YELLOW}11)${NC} Test storage API"
        echo ""
        echo -e "${RED}0)${NC} Exit"
        echo ""
        
        read -p "Enter your choice (0-11): " choice
        
        case $choice in
            1) start_services ;;
            2) stop_services ;;
            3) restart_services ;;
            4) show_status ;;
            5) show_logs ;;
            6) show_storage_logs ;;
            7) add_drive ;;
            8) remove_drive ;;
            9) scan_drives ;;
            10) setup_auto_mount ;;
            11) test_storage ;;
            0) 
                print_info "Goodbye!"
                exit 0
                ;;
            *) 
                print_error "Invalid option. Please try again."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Main script
main() {
    check_docker
    check_docker_compose
    
    case "${1:-interactive}" in
        start) start_services ;;
        stop) stop_services ;;
        restart) restart_services ;;
        status) show_status ;;
        logs) show_logs ;;
        storage-logs) show_storage_logs ;;
        add-drive) add_drive ;;
        remove-drive) remove_drive ;;
        scan-drives) scan_drives ;;
        auto-mount) setup_auto_mount ;;
        test) test_storage ;;
        interactive) interactive_menu ;;
        help|--help|-h) show_help ;;
        *) 
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 