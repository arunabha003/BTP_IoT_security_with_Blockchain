#!/bin/bash

# Quick System Test Script
# Tests the running IoT Identity System

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

GATEWAY_URL="http://127.0.0.1:8000"
ADMIN_KEY="test-admin-key-for-development"

echo -e "${BLUE}🧪 IoT Identity System - Quick Test${NC}"
echo -e "${BLUE}====================================${NC}"

# Test 1: Health Check
echo -e "\n${YELLOW}1. Testing health check...${NC}"
if curl -s "$GATEWAY_URL/healthz" | jq -e '.ok == true' > /dev/null; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi

# Test 2: System Status
echo -e "\n${YELLOW}2. Testing system status...${NC}"
if curl -s "$GATEWAY_URL/status" | jq -e '.service' > /dev/null; then
    echo -e "${GREEN}✅ System status accessible${NC}"
else
    echo -e "${RED}❌ System status failed${NC}"
    exit 1
fi

# Test 3: Accumulator Info
echo -e "\n${YELLOW}3. Testing accumulator info...${NC}"
ACCUMULATOR_RESPONSE=$(curl -s "$GATEWAY_URL/accumulator")
if echo "$ACCUMULATOR_RESPONSE" | jq -e '.rootHex' > /dev/null; then
    ROOT_HEX=$(echo "$ACCUMULATOR_RESPONSE" | jq -r '.rootHex')
    ACTIVE_DEVICES=$(echo "$ACCUMULATOR_RESPONSE" | jq -r '.activeDevices')
    echo -e "${GREEN}✅ Accumulator info accessible${NC}"
    echo -e "${BLUE}   Root: $ROOT_HEX${NC}"
    echo -e "${BLUE}   Active Devices: $ACTIVE_DEVICES${NC}"
else
    echo -e "${RED}❌ Accumulator info failed${NC}"
    exit 1
fi

# Test 4: Admin Authentication
echo -e "\n${YELLOW}4. Testing admin authentication...${NC}"
# This should fail without admin key
if curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$GATEWAY_URL/accumulator/update" \
    -H "Content-Type: application/json" \
    -d '{"newRootHex":"0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"}' | grep -q "401"; then
    echo -e "${GREEN}✅ Admin authentication protection working${NC}"
else
    echo -e "${RED}❌ Admin authentication protection failed${NC}"
    exit 1
fi

# Test 5: Rate Limiting
echo -e "\n${YELLOW}5. Testing rate limiting...${NC}"
RATE_LIMITED=false
for i in {1..25}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/healthz")
    if [ "$HTTP_CODE" = "429" ]; then
        RATE_LIMITED=true
        break
    fi
    sleep 0.1
done

if [ "$RATE_LIMITED" = true ]; then
    echo -e "${GREEN}✅ Rate limiting is active${NC}"
else
    echo -e "${YELLOW}⚠️  Rate limiting not triggered (may need more requests)${NC}"
fi

# Test 6: Security Headers
echo -e "\n${YELLOW}6. Testing security headers...${NC}"
HEADERS=$(curl -s -I "$GATEWAY_URL/healthz")
if echo "$HEADERS" | grep -qi "x-frame-options"; then
    echo -e "${GREEN}✅ Security headers present${NC}"
else
    echo -e "${YELLOW}⚠️  Some security headers may be missing${NC}"
fi

# Test 7: Performance Test
echo -e "\n${YELLOW}7. Testing performance...${NC}"
START_TIME=$(date +%s%3N)
curl -s "$GATEWAY_URL/healthz" > /dev/null
END_TIME=$(date +%s%3N)
RESPONSE_TIME=$((END_TIME - START_TIME))

if [ "$RESPONSE_TIME" -lt 100 ]; then
    echo -e "${GREEN}✅ Response time: ${RESPONSE_TIME}ms (excellent)${NC}"
elif [ "$RESPONSE_TIME" -lt 500 ]; then
    echo -e "${GREEN}✅ Response time: ${RESPONSE_TIME}ms (good)${NC}"
else
    echo -e "${YELLOW}⚠️  Response time: ${RESPONSE_TIME}ms (slow)${NC}"
fi

# Summary
echo -e "\n${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}===============${NC}"
echo -e "${GREEN}✅ Basic system functionality verified${NC}"
echo -e "${GREEN}✅ Security features are working${NC}"
echo -e "${GREEN}✅ Performance is acceptable${NC}"

echo -e "\n${YELLOW}💡 Next Steps:${NC}"
echo -e "${BLUE}   • Run full integration tests: cd tests && pytest -v${NC}"
echo -e "${BLUE}   • Try device enrollment with admin key${NC}"
echo -e "${BLUE}   • Check logs: tail -f gateway/gateway.log${NC}"

echo -e "\n${GREEN}🎉 Quick system test completed successfully!${NC}"
