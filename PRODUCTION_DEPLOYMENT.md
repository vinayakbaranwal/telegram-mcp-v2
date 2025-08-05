# Telegram MCP - Production Deployment Guide

## Telethon Session Management for Docker/Production

### Prerequisites

1. **Generate Session String** (CRITICAL for production):
   ```bash
   # Run this OUTSIDE Docker to generate session string
   python session_string_generator.py
   ```

2. **Set Environment Variables**:
   ```bash
   # Required
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_SESSION_STRING=your_generated_session_string

   # Optional for SSE mode
   TELEGRAM_MCP_HOST=0.0.0.0
   TELEGRAM_MCP_PORT=3001
   TELEGRAM_MCP_SSE_API_KEY=your_secret_key
   ```

### Production Deployment Options

#### Option 1: Docker Compose (Recommended)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  telegram-mcp-sse:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: telegram-mcp-prod
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_SESSION_STRING=${TELEGRAM_SESSION_STRING}
      - TELEGRAM_MCP_HOST=0.0.0.0
      - TELEGRAM_MCP_PORT=3001
      - TELEGRAM_MCP_SSE_API_KEY=${TELEGRAM_MCP_SSE_API_KEY}
    ports:
      - "3001:3001"
    command: ["python", "main.py", "-t", "sse"]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3001/sse"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Option 2: Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: telegram-mcp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: telegram-mcp
  template:
    metadata:
      labels:
        app: telegram-mcp
    spec:
      containers:
      - name: telegram-mcp
        image: telegram-mcp:latest
        ports:
        - containerPort: 3001
        env:
        - name: TELEGRAM_API_ID
          valueFrom:
            secretKeyRef:
              name: telegram-secrets
              key: api-id
        - name: TELEGRAM_API_HASH
          valueFrom:
            secretKeyRef:
              name: telegram-secrets
              key: api-hash
        - name: TELEGRAM_SESSION_STRING
          valueFrom:
            secretKeyRef:
              name: telegram-secrets
              key: session-string
        args: ["python", "main.py", "-t", "sse"]
---
apiVersion: v1
kind: Service
metadata:
  name: telegram-mcp-service
spec:
  selector:
    app: telegram-mcp
  ports:
  - port: 3001
    targetPort: 3001
  type: LoadBalancer
```

### Critical Production Considerations

#### 1. Session String Security
- ⚠️ **NEVER** commit session strings to version control
- Use secrets management (Docker secrets, K8s secrets, etc.)
- Rotate session strings periodically
- Monitor for unauthorized access

#### 2. Network Configuration
```dockerfile
# Add to Dockerfile for better networking
ENV TELETHON_TIMEOUT=30
ENV TELETHON_RETRY_DELAY=1
ENV TELETHON_CONNECTION_RETRIES=5
```

#### 3. Logging Configuration
```python
# Production logging setup (already in main.py)
logger.setLevel(logging.ERROR)  # Reduce log verbosity
```

#### 4. Health Checks
```bash
# Test SSE endpoint
curl -f http://localhost:3001/sse

# Test with authentication
curl -H "Authorization: Bearer your_api_key" http://localhost:3001/sse
```

### Troubleshooting Common Issues

#### Issue 1: "Database is locked"
**Cause**: Multiple instances or improper shutdown
**Solution**: Use string sessions only in production

#### Issue 2: "Connection timeout"
**Cause**: Network/firewall issues
**Solution**: 
```bash
# Test Telegram connectivity
telnet 149.154.167.50 443
```

#### Issue 3: "Invalid session"
**Cause**: Expired or corrupted session string
**Solution**: Regenerate session string using `session_string_generator.py`

#### Issue 4: Container startup fails
**Cause**: Missing environment variables
**Solution**: Verify all required env vars are set:
```bash
docker run --env-file .env telegram-mcp env | grep TELEGRAM
```

### Performance Optimization

1. **Memory Limits**:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 512M
       reservations:
         memory: 256M
   ```

2. **Connection Pooling**: Telethon handles this automatically

3. **Graceful Shutdown**:
   ```python
   # Already implemented in main.py
   await client.disconnect()
   ```

### Security Best Practices

1. **Use Read-Only Containers**:
   ```dockerfile
   USER appuser
   RUN chmod -R 555 /app
   ```

2. **Network Policies**: Restrict outbound connections to Telegram IPs only

3. **Secret Rotation**: Implement automated session string rotation

4. **Monitoring**: Set up alerts for authentication failures

### Monitoring & Alerting

```bash
# Check container health
docker ps --filter "name=telegram-mcp"

# Monitor logs
docker logs -f telegram-mcp

# Check resource usage
docker stats telegram-mcp
```

## Summary

✅ **Production Ready**: The current Telethon implementation is production-ready when using string sessions
⚠️ **Critical**: MUST use `TELEGRAM_SESSION_STRING` in Docker/production
🔒 **Security**: Implement proper secrets management
📊 **Monitoring**: Set up health checks and logging
