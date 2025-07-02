#!/bin/bash

# BabylonPiles Mode Switch Script
# This script allows manual switching between Learn and Store modes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:8080/api/v1"
SERVICE_NAME="babylonpiles"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if service is running
check_service() {
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        error "BabylonPiles service is not running. Start it with: systemctl start $SERVICE_NAME"
    fi
}

# Get current mode
get_current_mode() {
    local response
    response=$(curl -s "$API_URL/system/mode" 2>/dev/null || echo '{"success":false}')
    
    if echo "$response" | grep -q '"success":true'; then
        echo "$response" | grep -o '"current_mode":"[^"]*"' | cut -d'"' -f4
    else
        echo "unknown"
    fi
}

# Switch mode
switch_mode() {
    local mode=$1
    local response
    
    log "Switching to $mode mode..."
    
    response=$(curl -s -X POST "$API_URL/system/mode" \
        -H "Content-Type: application/json" \
        -d "{\"mode\":\"$mode\"}" 2>/dev/null || echo '{"success":false}')
    
    if echo "$response" | grep -q '"success":true'; then
        log "Successfully switched to $mode mode"
        return 0
    else
        error "Failed to switch to $mode mode"
        return 1
    fi
}

# Show system status
show_status() {
    local response
    response=$(curl -s "$API_URL/system/status" 2>/dev/null || echo '{"success":false}')
    
    if echo "$response" | grep -q '"success":true'; then
        echo "System Status:"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    else
        warn "Could not retrieve system status"
    fi
}

# Show help
show_help() {
    echo "BabylonPiles Mode Switch Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  learn     Switch to Learn mode (internet sync mode)"
    echo "  store     Switch to Store mode (offline/sharing mode)"
    echo "  status    Show current system status"
    echo "  current   Show current mode"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 learn    # Switch to Learn mode"
    echo "  $0 store    # Switch to Store mode"
    echo "  $0 status   # Show system status"
}

# Main function
main() {
    local command=${1:-help}
    
    case $command in
        "learn")
            check_service
            switch_mode "learn"
            ;;
        "store")
            check_service
            switch_mode "store"
            ;;
        "status")
            check_service
            show_status
            ;;
        "current")
            check_service
            current_mode=$(get_current_mode)
            log "Current mode: $current_mode"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 