targetScope = 'resourceGroup'

@minLength(1)
@description('Name prefix for all resources (e.g., seagent).')
param namePrefix string = 'seagent'

@minLength(1)
@description('Primary location for all resources.')
param location string = resourceGroup().location

@description('Container image for the Cloud MSX Worker. azd sets this after build/push.')
param msxWorkerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Run the worker in dry mode (sample data, no CRM/secrets). Set to false for live CRM.')
param dryRun bool = true

@description('Dynamics CRM org URL, e.g. https://contoso.crm.dynamics.com. Empty in dry mode.')
param crmUrl string = ''

@description('Entra tenant ID for CRM app-only auth. Empty in dry mode.')
param entraTenantId string = ''

@description('Entra client (app) ID for CRM app-only auth. Empty in dry mode.')
param entraClientId string = ''

@description('Approval token required to commit MSX writes. Generate a strong random value.')
@secure()
param approvalToken string = newGuid()

@description('Entra client secret for CRM app-only auth. Leave empty to use dry mode / federated credentials.')
@secure()
param entraClientSecret string = ''

@description('Enable Entra ID (Easy Auth) on the worker ingress, rejecting unauthenticated calls.')
param enableEasyAuth bool = false

@description('Entra app (client) ID that fronts the worker for Easy Auth. Required when enableEasyAuth is true.')
param easyAuthClientId string = ''

@description('Tenant ID for the Easy Auth login authority. Defaults to the subscription tenant.')
param easyAuthTenantId string = subscription().tenantId

@description('Minimum container replicas. 0 = scale-to-zero (cheapest, cold starts); 1 = always warm (no cold start).')
@minValue(0)
@maxValue(5)
param minReplicas int = 0

var tags = { 'azd-env-name': namePrefix, app: 'cloud-msx-worker' }
var resourceToken = uniqueString(subscription().id, resourceGroup().id, namePrefix)

// ---------------------------------------------------------------------------------------
// Observability
// ---------------------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-ai-${resourceToken}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ---------------------------------------------------------------------------------------
// Identity + registry
// ---------------------------------------------------------------------------------------
resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-${resourceToken}'
  location: location
  tags: tags
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: 'acr${resourceToken}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

// AcrPull for the worker identity
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, uami.id, 'acrpull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------------------
// Key Vault (secrets resolved by the worker identity)
// ---------------------------------------------------------------------------------------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

// Key Vault Secrets User for the worker identity
resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, uami.id, 'kvsecretsuser')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource secretApprovalToken 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'approval-token'
  properties: { value: approvalToken }
}

resource secretClientSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(entraClientSecret)) {
  parent: keyVault
  name: 'entra-client-secret'
  properties: { value: entraClientSecret }
}

// ---------------------------------------------------------------------------------------
// Container Apps environment + worker
// ---------------------------------------------------------------------------------------
resource caeEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-cae-${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

var baseEnv = [
  { name: 'SEAGENT_DRY_RUN', value: dryRun ? '1' : '' }
  { name: 'SEAGENT_CRM_URL', value: crmUrl }
  { name: 'SEAGENT_ENTRA_TENANT_ID', value: entraTenantId }
  { name: 'SEAGENT_ENTRA_CLIENT_ID', value: entraClientId }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
  { name: 'SEAGENT_APPROVAL_TOKEN', secretRef: 'approval-token' }
]

var secretEnv = empty(entraClientSecret) ? [] : [
  { name: 'SEAGENT_ENTRA_CLIENT_SECRET', secretRef: 'entra-client-secret' }
]

resource worker 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-msx-worker'
  location: location
  tags: union(tags, { 'azd-service-name': 'msx-worker' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${uami.id}': {} }
  }
  properties: {
    managedEnvironmentId: caeEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        { server: acr.properties.loginServer, identity: uami.id }
      ]
      secrets: union(
        [ { name: 'approval-token', keyVaultUrl: secretApprovalToken.properties.secretUri, identity: uami.id } ],
        empty(entraClientSecret) ? [] : [
          { name: 'entra-client-secret', keyVaultUrl: secretClientSecret.?properties.secretUri ?? '', identity: uami.id }
        ]
      )
    }
    template: {
      containers: [
        {
          name: 'msx-worker'
          image: msxWorkerImage
          resources: { cpu: json('0.5'), memory: '1.0Gi' }
          env: union(baseEnv, secretEnv)
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/healthz', port: 8000 }
              initialDelaySeconds: 5
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: { minReplicas: minReplicas, maxReplicas: 3 }
    }
  }
  dependsOn: [ acrPull, kvSecretsUser ]
}

// Entra ID (Easy Auth) front door: when enabled, unauthenticated requests are rejected
// (return401), so only callers with a valid Entra token for easyAuthClientId reach the app.
resource workerAuth 'Microsoft.App/containerApps/authConfigs@2024-03-01' = if (enableEasyAuth) {
  parent: worker
  name: 'current'
  properties: {
    platform: { enabled: true }
    globalValidation: {
      unauthenticatedClientAction: 'Return401'
      redirectToProvider: 'azureactivedirectory'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          openIdIssuer: '${environment().authentication.loginEndpoint}${easyAuthTenantId}/v2.0'
          clientId: easyAuthClientId
        }
        validation: {
          allowedAudiences: [
            'api://${easyAuthClientId}'
            easyAuthClientId
          ]
        }
      }
    }
  }
}

output MSX_WORKER_URL string = 'https://${worker.properties.configuration.ingress.fqdn}'
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.properties.loginServer
output AZURE_KEY_VAULT_NAME string = keyVault.name
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output EASY_AUTH_ENABLED bool = enableEasyAuth
