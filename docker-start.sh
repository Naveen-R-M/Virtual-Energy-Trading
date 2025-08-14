#!/bin/bash
# Docker Setup and Start Script for Virtual Energy Trading Platform

echo "⚡ Virtual Energy Trading Platform - Docker Setup"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker Desktop first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is running${NC}"
}

# Function to check if docker-compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        # Try docker compose (newer syntax)
        if ! docker compose version &> /dev/null; then
            echo -e "${RED}❌ docker-compose is not installed${NC}"
            exit 1
        else
            DOCKER_COMPOSE="docker compose"
            echo -e "${GREEN}✅ Docker Compose is available (new syntax)${NC}"
        fi
    else
        DOCKER_COMPOSE="docker-compose"
        echo -e "${GREEN}✅ Docker Compose is available${NC}"
    fi
}

# Main setup process
main() {
    echo -e "${BLUE}📋 Checking prerequisites...${NC}"
    check_docker
    check_docker_compose
    
    echo ""
    echo -e "${BLUE}🧹 Cleaning up any existing containers...${NC}"
    $DOCKER_COMPOSE down -v 2>/dev/null || true
    
    echo ""
    echo -e "${BLUE}🏗️  Building Docker images...${NC}"
    $DOCKER_COMPOSE build
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Build failed. Please check the error messages above.${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${BLUE}🗄️  Initializing database...${NC}"
    $DOCKER_COMPOSE run --rm backend python scripts/init_db.py
    
    echo ""
    echo -e "${BLUE}📊 Generating mock market data...${NC}"
    TODAY=$(date +%Y-%m-%d)
    $DOCKER_COMPOSE run --rm backend python scripts/fetch_prices.py --node PJM_RTO --date $TODAY --mock --da --rt
    
    echo ""
    echo -e "${BLUE}🚀 Starting services...${NC}"
    $DOCKER_COMPOSE up -d
    
    # Wait for services to be ready
    echo ""
    echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
    
    # Wait for backend
    MAX_TRIES=30
    TRIES=0
    while [ $TRIES -lt $MAX_TRIES ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Backend is ready${NC}"
            break
        fi
        TRIES=$((TRIES + 1))
        sleep 2
        echo -n "."
    done
    
    if [ $TRIES -eq $MAX_TRIES ]; then
        echo -e "${RED}❌ Backend failed to start. Check logs with: docker-compose logs backend${NC}"
    fi
    
    # Check frontend
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready${NC}"
    else
        echo -e "${YELLOW}⚠️  Frontend may still be starting. Check: http://localhost:5173${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Virtual Energy Trading Platform is running!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "📊 Access the application at:"
    echo -e "   ${BLUE}Frontend:${NC} http://localhost:5173"
    echo -e "   ${BLUE}Backend API:${NC} http://localhost:8000"
    echo -e "   ${BLUE}API Docs:${NC} http://localhost:8000/docs"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs:        $DOCKER_COMPOSE logs -f"
    echo "   Stop services:    $DOCKER_COMPOSE down"
    echo "   Restart services: $DOCKER_COMPOSE restart"
    echo "   View status:      $DOCKER_COMPOSE ps"
    echo ""
    echo "🎮 Quick Start:"
    echo "   1. Open http://localhost:5173 in your browser"
    echo "   2. View market prices on the Dashboard"
    echo "   3. Create Day-Ahead orders (before 11 AM EST)"
    echo "   4. Create Real-Time orders (anytime)"
    echo "   5. Match orders and view P&L"
    echo ""
}

# Run main function
main
