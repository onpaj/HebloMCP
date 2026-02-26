#!/bin/bash
set -e

echo "=== HebloMCP Deployment Validation ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

WEBAPP_NAME="${AZURE_WEBAPP_NAME:-heblomcp}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rgHeblo}"
DOCKERHUB_USER="${DOCKERHUB_USERNAME:-remiiik}"

echo "1. Checking DockerHub image..."
if docker pull ${DOCKERHUB_USER}/heblo-mcp:latest > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} DockerHub image found: ${DOCKERHUB_USER}/heblo-mcp:latest"
else
    echo -e "${RED}✗${NC} DockerHub image not found"
    exit 1
fi

echo ""
echo "2. Checking Azure Web App status..."
APP_STATE=$(az webapp show \
    --resource-group ${RESOURCE_GROUP} \
    --name ${WEBAPP_NAME} \
    --query "state" -o tsv 2>/dev/null || echo "NotFound")

if [ "$APP_STATE" = "Running" ]; then
    echo -e "${GREEN}✓${NC} Azure Web App is running"
else
    echo -e "${RED}✗${NC} Azure Web App state: $APP_STATE"
    exit 1
fi

echo ""
echo "3. Testing health endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://${WEBAPP_NAME}.azurewebsites.net/ || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓${NC} Health endpoint returned 200 OK"
else
    echo -e "${RED}✗${NC} Health endpoint returned: $HTTP_STATUS"
    echo -e "${YELLOW}Note: App may still be starting up. Wait 30 seconds and try again.${NC}"
fi

echo ""
echo "4. Checking container image..."
CURRENT_IMAGE=$(az webapp config container show \
    --resource-group ${RESOURCE_GROUP} \
    --name ${WEBAPP_NAME} \
    --query "[0].value" -o tsv 2>/dev/null || echo "unknown")

echo -e "${GREEN}✓${NC} Current image: $CURRENT_IMAGE"

echo ""
echo "5. Checking app settings..."
SETTINGS=$(az webapp config appsettings list \
    --resource-group ${RESOURCE_GROUP} \
    --name ${WEBAPP_NAME} \
    --query "[?name=='HEBLO_TRANSPORT' || name=='WEBSITES_PORT'].{name:name, value:value}" \
    -o table 2>/dev/null)

if echo "$SETTINGS" | grep -q "sse"; then
    echo -e "${GREEN}✓${NC} App settings configured correctly"
    echo "$SETTINGS"
else
    echo -e "${YELLOW}⚠${NC} App settings may need configuration"
    echo "$SETTINGS"
fi

echo ""
echo -e "${GREEN}=== Validation Complete ===${NC}"
echo ""
echo "Access your MCP server at: https://${WEBAPP_NAME}.azurewebsites.net/"
echo "View logs: az webapp log tail --resource-group ${RESOURCE_GROUP} --name ${WEBAPP_NAME}"
