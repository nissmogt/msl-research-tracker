#!/bin/bash

# 🔧 MSL Research Tracker - Development Environment Manager
# Automated setup and management for isolated development environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print colored output
print_header() {
    echo -e "${BLUE}🔧 MSL Development Environment Manager${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Check if we're in the project root
check_project_root() {
    if [[ ! -d "frontend" || ! -d "backend" ]]; then
        print_error "Must be run from project root directory"
        print_info "Navigate to the MSL project root and try again"
        exit 1
    fi
}

# Setup development environment
setup_dev_env() {
    print_header
    echo -e "${GREEN}Setting up ISOLATED development environment...${NC}"
    echo
    
    # Backup any existing production database
    if [[ -f "backend/msl_research.db" ]]; then
        cp "backend/msl_research.db" "backend/msl_research_PRODUCTION_BACKUP.db"
        print_success "Backed up production database"
    fi
    
    # Create frontend development environment
    cat > frontend/.env.development << EOF
# 🔧 DEVELOPMENT ENVIRONMENT
# Forces frontend to connect to localhost backend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development
GENERATE_SOURCEMAP=true
BROWSER=none
EOF
    print_success "Created frontend/.env.development"
    
    # Create backend development environment
    cat > backend/.env.development << EOF
# 🔧 DEVELOPMENT ENVIRONMENT
# Isolated database and configuration
DATABASE_URL=sqlite:///./dev_msl_research.db
ENVIRONMENT=development
PORT=8000
DEBUG=true
# Development secret (NOT FOR PRODUCTION)
SECRET_KEY=dev_secret_key_not_for_production_$(date +%s)
EOF
    print_success "Created backend/.env.development"
    
    # Remove existing dev database to start fresh
    if [[ -f "backend/dev_msl_research.db" ]]; then
        rm "backend/dev_msl_research.db"
        print_success "Cleared existing development database"
    fi
    
    echo
    print_success "Development environment setup complete!"
    echo
    print_info "🛡️  SAFETY: Your production Railway server is completely isolated"
    print_info "📁 Development database: backend/dev_msl_research.db"
    print_info "🌐 Development API: http://localhost:8000"
    print_info "🖥️  Development frontend: http://localhost:3000"
    echo
    print_warning "To start development: $0 start"
}

# Start development environment
start_dev_env() {
    print_header
    
    # Check if environment is set up
    if [[ ! -f "frontend/.env.development" || ! -f "backend/.env.development" ]]; then
        print_error "Development environment not set up"
        print_info "Run: $0 setup"
        exit 1
    fi
    
    echo -e "${GREEN}Starting development environment...${NC}"
    echo
    
    # Kill any existing processes
    pkill -f "python main.py" 2>/dev/null || true
    pkill -f "react-scripts" 2>/dev/null || true
    sleep 2
    
    print_info "Starting backend server..."
    cd backend
    python main.py &
    BACKEND_PID=$!
    cd ..
    
    sleep 3
    
    print_info "Starting frontend server..."
    cd frontend
    npm start &
    FRONTEND_PID=$!
    cd ..
    
    echo
    print_success "🚀 Development environment started!"
    print_info "📱 Frontend: http://localhost:3000"
    print_info "🔧 Backend: http://localhost:8000"
    print_info "📊 API Docs: http://localhost:8000/docs"
    echo
    print_warning "Press Ctrl+C to stop, or run: $0 stop"
    
    # Wait for user to stop
    wait
}

# Stop development environment
stop_dev_env() {
    print_header
    echo -e "${YELLOW}Stopping development environment...${NC}"
    
    pkill -f "python main.py" 2>/dev/null || true
    pkill -f "react-scripts" 2>/dev/null || true
    
    print_success "Development environment stopped"
}

# Clear development database
clear_dev_db() {
    print_header
    echo -e "${YELLOW}Clearing development database...${NC}"
    
    if [[ -f "backend/dev_msl_research.db" ]]; then
        rm "backend/dev_msl_research.db"
        print_success "Development database cleared"
    else
        print_info "Development database already empty"
    fi
    
    # Also clear via API if backend is running
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        curl -s -X POST http://localhost:8000/debug/clear-db > /dev/null
        print_success "Cleared database via API"
    fi
}

# Teardown development environment (switch back to production)
teardown_dev_env() {
    print_header
    echo -e "${RED}Switching back to PRODUCTION mode...${NC}"
    echo
    
    # Stop development processes
    stop_dev_env
    
    # Remove development environment files
    if [[ -f "frontend/.env.development" ]]; then
        rm "frontend/.env.development"
        print_success "Removed frontend/.env.development"
    fi
    
    if [[ -f "backend/.env.development" ]]; then
        rm "backend/.env.development"
        print_success "Removed backend/.env.development"
    fi
    
    # Optionally remove dev database
    echo
    read -p "Remove development database? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ -f "backend/dev_msl_research.db" ]]; then
            rm "backend/dev_msl_research.db"
            print_success "Removed development database"
        fi
    fi
    
    echo
    print_success "🚀 Switched back to PRODUCTION mode"
    print_warning "Frontend will now connect to Railway production server"
    print_info "Your production data is safe and untouched"
}

# Show current status
show_status() {
    print_header
    echo -e "${CYAN}Current Environment Status:${NC}"
    echo
    
    # Check environment files
    if [[ -f "frontend/.env.development" && -f "backend/.env.development" ]]; then
        echo -e "${GREEN}🔧 DEVELOPMENT MODE${NC}"
        echo "  📁 Frontend config: ✅ frontend/.env.development"
        echo "  📁 Backend config: ✅ backend/.env.development"
        
        # Check what frontend connects to
        FRONTEND_URL=$(grep REACT_APP_API_URL frontend/.env.development | cut -d'=' -f2)
        echo "  🌐 Frontend connects to: $FRONTEND_URL"
        
        # Check database
        if [[ -f "backend/dev_msl_research.db" ]]; then
            echo "  📊 Dev database: ✅ backend/dev_msl_research.db"
        else
            echo "  📊 Dev database: ❌ Not created yet"
        fi
        
    else
        echo -e "${YELLOW}🚀 PRODUCTION MODE${NC}"
        echo "  🌐 Frontend connects to: Railway production server"
        echo "  📊 Database: Railway PostgreSQL"
    fi
    
    echo
    
    # Check running processes
    if pgrep -f "python main.py" > /dev/null; then
        echo -e "${GREEN}🔧 Backend: ✅ Running${NC}"
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            ARTICLE_COUNT=$(curl -s http://localhost:8000/debug/db-count | grep -o '"article_count":[0-9]*' | cut -d':' -f2 || echo "unknown")
            echo "  📊 Database articles: $ARTICLE_COUNT"
        fi
    else
        echo -e "${RED}🔧 Backend: ❌ Not running${NC}"
    fi
    
    if pgrep -f "react-scripts" > /dev/null; then
        echo -e "${GREEN}📱 Frontend: ✅ Running${NC}"
        echo "  🌐 URL: http://localhost:3000"
    else
        echo -e "${RED}📱 Frontend: ❌ Not running${NC}"
    fi
}

# Run tests
run_tests() {
    print_header
    echo -e "${CYAN}Running development environment tests...${NC}"
    echo
    
    # Test 1: Backend health
    print_info "Test 1: Backend health check"
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "Backend is responding"
    else
        print_error "Backend not responding"
        return 1
    fi
    
    # Test 2: Database isolation
    print_info "Test 2: Database isolation"
    ARTICLE_COUNT=$(curl -s http://localhost:8000/debug/db-count | grep -o '"article_count":[0-9]*' | cut -d':' -f2)
    if [[ "$ARTICLE_COUNT" == "0" ]]; then
        print_success "Development database is isolated (0 articles)"
    else
        print_warning "Development database has $ARTICLE_COUNT articles"
    fi
    
    # Test 3: PubMed search
    print_info "Test 3: PubMed search (no auto-save)"
    BEFORE_COUNT=$(curl -s http://localhost:8000/debug/db-count | grep -o '"article_count":[0-9]*' | cut -d':' -f2)
    curl -s -X POST http://localhost:8000/articles/search-pubmed \
        -H "Content-Type: application/json" \
        -d '{"therapeutic_area": "test", "days_back": 7, "use_case": "clinical"}' > /dev/null
    AFTER_COUNT=$(curl -s http://localhost:8000/debug/db-count | grep -o '"article_count":[0-9]*' | cut -d':' -f2)
    
    if [[ "$BEFORE_COUNT" == "$AFTER_COUNT" ]]; then
        print_success "PubMed search doesn't auto-save to database"
    else
        print_error "PubMed search auto-saved to database"
    fi
    
    echo
    print_success "All tests completed!"
}

# Self-destruct function
self_destruct() {
    print_header
    echo -e "${RED}Self-destruct sequence initiated...${NC}"
    echo
    
    print_warning "This will:"
    echo "  • Switch back to production mode"
    echo "  • Remove all development files"
    echo "  • Delete this script"
    echo
    
    read -p "Are you sure? Type 'DELETE' to confirm: " -r
    if [[ $REPLY == "DELETE" ]]; then
        teardown_dev_env
        rm -f "backend/dev_msl_research.db"
        rm -f "backend/msl_research_PRODUCTION_BACKUP.db"
        print_success "Environment cleaned up"
        print_warning "Removing this script in 3 seconds..."
        sleep 3
        rm -- "$0"
        echo "Self-destruct complete. 💥"
    else
        print_info "Self-destruct cancelled"
    fi
}

# Show help
show_help() {
    print_header
    echo "Usage: $0 {command}"
    echo
    echo "Commands:"
    echo "  setup      Set up isolated development environment"
    echo "  start      Start both frontend and backend servers"
    echo "  stop       Stop all development processes"
    echo "  status     Show current environment status"
    echo "  clear-db   Clear development database"
    echo "  test       Run development environment tests"
    echo "  teardown   Switch back to production mode"
    echo "  destruct   Remove everything and switch to production"
    echo "  help       Show this help message"
    echo
    echo "Quick workflow:"
    echo "  $0 setup && $0 start    # Set up and start development"
    echo "  $0 teardown             # Switch back to production"
    echo
    echo "🛡️  Safety: Development is completely isolated from production"
}

# Main script logic
check_project_root

case "${1:-help}" in
    setup)
        setup_dev_env
        ;;
    start)
        start_dev_env
        ;;
    stop)
        stop_dev_env
        ;;
    status)
        show_status
        ;;
    clear-db)
        clear_dev_db
        ;;
    test)
        run_tests
        ;;
    teardown)
        teardown_dev_env
        ;;
    destruct)
        self_destruct
        ;;
    help)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
