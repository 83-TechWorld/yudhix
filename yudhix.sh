#!/usr/bin/env bash
# ==============================================================================
# Yudhix Platform Controller (yudhix.sh)
# Single unified manager for all microservices, AI pipeline, and frontend
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/.logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

JAVA_CMD="${JAVA_HOME:-/Library/Java/JavaVirtualMachines/temurin-23.jdk/Contents/Home}/bin/java"
MVN_WRAPPER="$SCRIPT_DIR/mvnw"

# Colors for terminal output (White, Orange, Black theme)
ORANGE='\033[38;5;208m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${ORANGE}"
    echo "  ██╗   ██╗██╗   ██╗██████╗ ██╗  ██╗██╗██╗  ██╗"
    echo "  ╚██╗ ██╔╝██║   ██║██╔══██╗██║  ██║██║╚██╗██╔╝"
    echo "   ╚████╔╝ ██║   ██║██║  ██║███████║██║ ╚███╔╝ "
    echo "    ╚██╔╝  ██║   ██║██║  ██║██╔══██║██║ ██╔██╗ "
    echo "     ██║   ╚██████╔╝██████╔╝██║  ██║██║██╔╝ ██╗"
    echo "     ╚═╝    ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝"
    echo -e "${WHITE}  Enterprise Comment Intelligence & Turnaround Platform${NC}"
    echo -e "${GRAY}  -------------------------------------------------------------${NC}"
}

check_ollama() {
    echo -e "${ORANGE}[+]${WHITE} Checking Local Ollama...${NC}"
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo -e "    ${GREEN}✔ Ollama is online at http://localhost:11434${NC}"
    else
        echo -e "    ${GRAY}Starting ollama serve...${NC}"
        ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
        echo $! > "$PID_DIR/ollama.pid"
        sleep 2
    fi
}

start_sense() {
    echo -e "${ORANGE}[+]${WHITE} Starting yudhix-sense (FastAPI AI Engine on :8000)...${NC}"
    cd "$SCRIPT_DIR/services/yudhix-sense"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        ./.venv/bin/pip install --upgrade pip fastapi uvicorn httpx pydantic > /dev/null 2>&1
    fi
    OLLAMA_MODEL="llama3.1:latest" nohup ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/sense.log" 2>&1 &
    echo $! > "$PID_DIR/sense.pid"
    cd "$SCRIPT_DIR"
    echo -e "    ${GREEN}✔ yudhix-sense running on http://localhost:8000${NC}"
}

start_frontend() {
    echo -e "${ORANGE}[+]${WHITE} Starting yudhix-web (Frontend on :3000)...${NC}"
    nohup python3 -m http.server 3000 --directory "$SCRIPT_DIR/frontend/yudhix-web" > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    echo -e "    ${GREEN}✔ yudhix-web running on http://localhost:3000${NC}"
}

start_config() {
    echo -e "${ORANGE}[+]${WHITE} Starting yudhix-config (Config Server on :8888)...${NC}"
    nohup env JAVA_HOME=/Library/Java/JavaVirtualMachines/temurin-23.jdk/Contents/Home ./mvnw spring-boot:run -pl services/yudhix-config > "$LOG_DIR/config.log" 2>&1 &
    echo $! > "$PID_DIR/config.pid"
    echo -e "    ${GREEN}✔ yudhix-config starting on http://localhost:8888${NC}"
}

start_all() {
    print_banner
    check_ollama
    start_sense
    start_frontend
    echo -e "\n${ORANGE}All core servers initiated!${NC}"
    echo -e "${WHITE}Open Dashboard: ${ORANGE}http://localhost:3000${NC}\n"
}

stop_all() {
    print_banner
    echo -e "${ORANGE}[!] Stopping all Yudhix services...${NC}"
    for pidfile in "$PID_DIR"/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            svc=$(basename "$pidfile" .pid)
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
                echo -e "    ${RED}Stopped $svc (PID: $pid)${NC}"
            fi
            rm -f "$pidfile"
        fi
    done
    # Kill any dangling python http.server on 3000 or uvicorn on 8000
    pkill -f "http.server 3000" 2>/dev/null || true
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    echo -e "${GREEN}✔ All processes stopped.${NC}"
}

status_all() {
    print_banner
    echo -e "${WHITE}SERVICE                PORT     STATUS${NC}"
    echo -e "${GRAY}-------------------------------------------${NC}"

    # Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${WHITE}Ollama Engine          ${ORANGE}11434    ${GREEN}ONLINE${NC}"
    else
        echo -e "${WHITE}Ollama Engine          ${ORANGE}11434    ${RED}OFFLINE${NC}"
    fi

    # Sense
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${WHITE}yudhix-sense (AI)      ${ORANGE}8000     ${GREEN}ONLINE${NC}"
    else
        echo -e "${WHITE}yudhix-sense (AI)      ${ORANGE}8000     ${RED}OFFLINE${NC}"
    fi

    # Frontend
    if curl -s -I http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${WHITE}yudhix-web (Frontend)  ${ORANGE}3000     ${GREEN}ONLINE${NC}"
    else
        echo -e "${WHITE}yudhix-web (Frontend)  ${ORANGE}3000     ${RED}OFFLINE${NC}"
    fi
}

run_test() {
    print_banner
    echo -e "${ORANGE}[+] Testing AI Pipeline + Presidio Masker + Local Ollama...${NC}"
    response=$(curl -s -X POST http://localhost:8000/api/v1/analyze \
      -H "Content-Type: application/json" \
      -d '{
        "comment_id": "test-c1",
        "tenant_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
        "raw_text": "Battery on controller dies in 2 hours! Called support at +91 9876543210 with no reply. Broken!"
      }')

    echo -e "\n${WHITE}Response from Pipeline:${NC}"
    echo "$response" | python3 -m json.tool || echo "$response"
    echo -e "\n${GREEN}✔ Verification Test Complete!${NC}"
}

case "$1" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_all
        ;;
    status)
        status_all
        ;;
    test)
        run_test
        ;;
    ui)
        open "http://localhost:3000" || echo "Visit http://localhost:3000"
        ;;
    *)
        print_banner
        echo -e "${WHITE}Usage:${NC} ./yudhix.sh {start|stop|restart|status|test|ui}"
        echo ""
        echo -e "  ${ORANGE}start${NC}    - Launch Ollama, yudhix-sense AI engine, and yudhix-web frontend"
        echo -e "  ${ORANGE}stop${NC}     - Stop all background running services"
        echo -e "  ${ORANGE}status${NC}   - Display health and ports of all services"
        echo -e "  ${ORANGE}test${NC}     - Run live end-to-end PII masking & AI analysis test"
        echo -e "  ${ORANGE}ui${NC}       - Open the white/orange/black frontend in your default browser"
        ;;
esac
