#!/usr/bin/env bash
# Botcrew Development Environment Bootstrap
# One-command setup: creates kind cluster, deploys all infrastructure,
# runs migrations, and verifies the stack.
#
# Usage: ./scripts/dev-setup.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# Colors for output
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

CLUSTER_NAME="botcrew-dev"
NAMESPACE="botcrew"
IMAGE_NAME="botcrew-orchestrator:latest"

# ---------------------------------------------------------------------------
# Step 0: Check prerequisites
# ---------------------------------------------------------------------------
info "Checking prerequisites..."

for cmd in kind kubectl helm docker uv; do
    if ! command -v "$cmd" &>/dev/null; then
        error "'$cmd' is not installed. Please install it first."
    fi
done
ok "All prerequisites found."

# ---------------------------------------------------------------------------
# Step 1: Create kind cluster (if not exists)
# ---------------------------------------------------------------------------
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    info "Kind cluster '${CLUSTER_NAME}' already exists, reusing."
else
    info "Creating kind cluster '${CLUSTER_NAME}'..."

    KIND_CONFIG=$(mktemp)
    cat > "$KIND_CONFIG" <<'KINDEOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 8080
    protocol: TCP
KINDEOF

    kind create cluster --name "$CLUSTER_NAME" --config "$KIND_CONFIG"
    rm -f "$KIND_CONFIG"
    ok "Kind cluster '${CLUSTER_NAME}' created."
fi

# Ensure kubectl context is set to the kind cluster
kubectl cluster-info --context "kind-${CLUSTER_NAME}" &>/dev/null || error "Cannot connect to kind cluster."
kubectl config use-context "kind-${CLUSTER_NAME}" &>/dev/null
ok "kubectl context set to kind-${CLUSTER_NAME}."

# ---------------------------------------------------------------------------
# Step 2: Start cloud-provider-kind (for Gateway API LoadBalancer support)
# ---------------------------------------------------------------------------
if docker ps --format '{{.Image}}' | grep -q "cloud-provider-kind"; then
    info "cloud-provider-kind already running."
else
    info "Starting cloud-provider-kind for LoadBalancer support..."
    docker run -d --rm \
        --network kind \
        --name cloud-provider-kind \
        -v /var/run/docker.sock:/var/run/docker.sock \
        registry.k8s.io/cloud-provider-kind/cloud-provider-kind:v0.6.0 2>/dev/null || \
    warn "cloud-provider-kind may already be running or failed to start. Gateway LoadBalancer may not get an IP."
    ok "cloud-provider-kind started."
fi

# ---------------------------------------------------------------------------
# Step 3: Install Gateway API CRDs
# ---------------------------------------------------------------------------
info "Installing Gateway API CRDs..."
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/latest/download/standard-install.yaml 2>&1 | tail -1
ok "Gateway API CRDs installed."

# ---------------------------------------------------------------------------
# Step 4: Build orchestrator Docker image
# ---------------------------------------------------------------------------
info "Building orchestrator Docker image..."
docker build -t "$IMAGE_NAME" .
ok "Docker image '${IMAGE_NAME}' built."

# ---------------------------------------------------------------------------
# Step 5: Load image into kind
# ---------------------------------------------------------------------------
info "Loading image into kind cluster..."
kind load docker-image "$IMAGE_NAME" --name "$CLUSTER_NAME"
ok "Image loaded into kind."

# ---------------------------------------------------------------------------
# Step 6: Deploy with Helm
# ---------------------------------------------------------------------------
info "Deploying with Helm..."
helm upgrade --install botcrew ./helm/botcrew \
    --namespace "$NAMESPACE" \
    --create-namespace \
    --wait \
    --timeout 5m
ok "Helm deployment complete."

# ---------------------------------------------------------------------------
# Step 7: Wait for PostgreSQL to be ready
# ---------------------------------------------------------------------------
info "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=botcrew-postgres -n "$NAMESPACE" --timeout=120s
ok "PostgreSQL is ready."

# ---------------------------------------------------------------------------
# Step 8: Run Alembic migrations via port-forward
# ---------------------------------------------------------------------------
info "Running Alembic migrations..."

# Start port-forward in background
kubectl port-forward svc/botcrew-postgres 5432:5432 -n "$NAMESPACE" &
PF_PID=$!

# Wait for port-forward to establish
sleep 3

# Run migrations
BOTCREW_DATABASE_URL="postgresql+asyncpg://botcrew:botcrew@localhost:5432/botcrew" \
    uv run alembic upgrade head

# Clean up port-forward
kill "$PF_PID" 2>/dev/null || true
wait "$PF_PID" 2>/dev/null || true
ok "Alembic migrations applied."

# ---------------------------------------------------------------------------
# Step 9: Wait for orchestrator to be ready
# ---------------------------------------------------------------------------
info "Waiting for orchestrator to be ready..."
kubectl wait --for=condition=ready pod -l app=botcrew-orchestrator -n "$NAMESPACE" --timeout=120s
ok "Orchestrator is ready."

# ---------------------------------------------------------------------------
# Step 10: Verify the stack
# ---------------------------------------------------------------------------
echo ""
info "========================================="
info "  Stack Verification"
info "========================================="
echo ""

info "Pod status:"
kubectl get pods -n "$NAMESPACE"
echo ""

info "Gateway status:"
kubectl get gateway -n "$NAMESPACE" 2>/dev/null || warn "No Gateway resources found."
echo ""

info "Services:"
kubectl get svc -n "$NAMESPACE"
echo ""

# Health check via port-forward
info "Running health check..."
kubectl port-forward svc/botcrew-orchestrator 8000:8000 -n "$NAMESPACE" &
HC_PID=$!
sleep 3

HEALTH=$(curl -s http://localhost:8000/api/v1/system/health 2>/dev/null || echo "FAILED")
kill "$HC_PID" 2>/dev/null || true
wait "$HC_PID" 2>/dev/null || true

if echo "$HEALTH" | grep -q '"healthy"'; then
    ok "Health check passed!"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
else
    warn "Health check returned: $HEALTH"
    warn "The orchestrator may still be starting up. Try manually:"
    warn "  kubectl port-forward svc/botcrew-orchestrator 8000:8000 -n $NAMESPACE"
    warn "  curl http://localhost:8000/api/v1/system/health"
fi

echo ""
ok "========================================="
ok "  Botcrew dev environment is ready!"
ok "========================================="
echo ""
info "Useful commands:"
info "  kubectl get pods -n $NAMESPACE"
info "  kubectl logs -f deployment/botcrew-orchestrator -n $NAMESPACE"
info "  kubectl port-forward svc/botcrew-orchestrator 8000:8000 -n $NAMESPACE"
info "  curl http://localhost:8000/api/v1/system/health"
echo ""
