# Vault on Kubernetes Integration Guide

This guide demonstrates how to deploy and configure HashiCorp Vault on Kubernetes, integrate it with a FastAPI application, and manage MongoDB credentials using the Vault Secrets Operator (VSO).

## Prerequisites

- Kubernetes cluster (e.g., Minikube, kind, or a cloud-managed cluster)
- kubectl CLI tool
- Helm package manager
- Basic understanding of Kubernetes and HashiCorp Vault

## Installation Steps

### 1. Deploy Vault using Helm

```bash
# Add the HashiCorp Helm repository
helm repo add hashicorp https://helm.releases.hashicorp.com

# Update the repository
helm repo update

# Install Vault
helm install vault hashicorp/vault -f vault-values.yaml
```

The `vault-values.yaml` configuration enables the dev server mode, standalone deployment, and UI access:

```yaml
server:
  dev:
    enabled: true
  standalone:
    enabled: true
    config: |
      ui = true
      listener "tcp" {
        tls_disable = 1
        address = "[::]:8200"
        cluster_address = "[::]:8201"
      }
      storage "file" {
        path = "/vault/data"
      }

ui:
  enabled: true
  serviceType: NodePort
```

### 2. Initialize and Unseal Vault

After deployment, initialize Vault to get the unseal key and root token:

```bash
# Port forward the Vault service
kubectl port-forward service/vault 8200:8200

# Initialize Vault
vault operator init -key-shares=1 -key-threshold=1
```

Save the Unseal Key and Root Token securely. They will be needed for administrative tasks.

### 3. Install Vault Secrets Operator (VSO)

```bash
# Install the Vault Secrets Operator
helm install vault-secrets-operator hashicorp/vault-secrets-operator
```

### 4. Configure Vault Authentication

Set up Kubernetes authentication in Vault:

```bash
# Enable Kubernetes auth method
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
    kubernetes_host="https://kubernetes.default.svc.cluster.local:443"

# Create a policy for the application
vault policy write webapp - <<EOF
path "secret/data/mongodb/credentials" {
  capabilities = ["read"]
}
EOF

# Create a Kubernetes auth role
vault write auth/kubernetes/role/webapp \
    bound_service_account_names=default \
    bound_service_account_namespaces=default \
    policies=webapp \
    ttl=1h
```

### 5. Configure VSO Resources

Apply the VSO configuration to manage MongoDB credentials:

```yaml
# vso-config.yaml
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultConnection
metadata:
  name: vault-connection
spec:
  address: http://vault.default.svc.cluster.local:8200
---
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultAuth
metadata:
  name: vault-auth
spec:
  method: kubernetes
  mount: kubernetes
  vaultConnectionRef: vault-connection
  kubernetes:
    role: webapp
    serviceAccount: default
---
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultStaticSecret
metadata:
  name: mongodb-credentials
spec:
  vaultAuthRef: vault-auth
  mount: secret
  type: kv-v2
  path: mongodb/credentials
  refreshAfter: 1h
  destination:
    name: mongodb-secret
    create: true
```

Apply the configuration:

```bash
kubectl apply -f vso-config.yaml
```

### 6. Store MongoDB Credentials in Vault

```bash
# Store MongoDB credentials
vault kv put secret/mongodb/credentials \
    MONGO_INITDB_ROOT_USERNAME=admin \
    MONGO_INITDB_ROOT_PASSWORD=password
```

### 7. Deploy the Application

Deploy the FastAPI application and MongoDB using the provided deployment configuration:

```bash
kubectl apply -f app/deployment.yaml
```

## Verification

1. Check if the VSO resources are created:
```bash
kubectl get vaultconnection
kubectl get vaultauth
kubectl get vaultstaticsecret
```

2. Verify the MongoDB secret is created:
```bash
kubectl get secret mongodb-secret
```

3. Check if the application pods are running:
```bash
kubectl get pods
```

## Accessing the Application

Access the FastAPI application:

```bash
kubectl port-forward service/fastapi-app 8000:8000
```

Visit http://localhost:8000 to access the API.

## Cleanup

To remove all resources:

```bash
# Delete the application and MongoDB
kubectl delete -f app/deployment.yaml

# Delete VSO resources
kubectl delete -f vso-config.yaml

# Uninstall Vault and VSO
helm uninstall vault
helm uninstall vault-secrets-operator
```

## Security Considerations

- In production, disable development mode and configure proper TLS
- Use proper secret management for Vault's unseal key and root token
- Implement proper RBAC policies in Vault
- Configure resource limits and requests appropriately
- Use dedicated service accounts with minimal permissions

## Troubleshooting

1. If pods can't access Vault:
   - Verify the Vault service is running
   - Check Kubernetes authentication configuration
   - Verify service account permissions

2. If secrets aren't syncing:
   - Check VSO operator logs
   - Verify VaultStaticSecret configuration
   - Ensure the secret exists in Vault

3. If the application can't connect to MongoDB:
   - Verify MongoDB credentials in Vault
   - Check if the secret is properly mounted
   - Verify MongoDB service is running