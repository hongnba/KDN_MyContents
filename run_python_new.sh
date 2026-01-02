#!/bin/bash

# Python New Container Management Script

case "$1" in
    "build")
        echo "Building python_new container..."
        docker compose -f docker-compose-python-new.yml build
        ;;
    "up")
        echo "Starting python_new container..."
        docker compose -f docker-compose-python-new.yml up -d
        ;;
    "down")
        echo "Stopping python_new container..."
        docker compose -f docker-compose-python-new.yml down
        ;;
    "logs")
        echo "Showing python_new container logs..."
        docker compose -f docker-compose-python-new.yml logs -f python_new
        ;;
    "shell")
        echo "Opening shell in python_new container..."
        docker exec -it python_new /bin/bash
        ;;
    "restart")
        echo "Restarting python_new container..."
        docker compose -f docker-compose-python-new.yml restart python_new
        ;;
    "status")
        echo "Checking python_new container status..."
        docker compose -f docker-compose-python-new.yml ps
        ;;
    *)
        echo "Usage: $0 {build|up|down|logs|shell|restart|status}"
        echo ""
        echo "Commands:"
        echo "  build   - Build the python_new container"
        echo "  up      - Start the python_new container"
        echo "  down    - Stop the python_new container"
        echo "  logs    - Show container logs"
        echo "  shell   - Open bash shell in container"
        echo "  restart - Restart the container"
        echo "  status  - Show container status"
        exit 1
        ;;
esac
