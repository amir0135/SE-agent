targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the azd environment; used to derive the resource group.')
param environmentName string

@minLength(1)
@description('Primary location for all resources.')
param location string

@description('Container image for the Cloud MSX Worker. azd sets this after build/push.')
param msxWorkerImage string = ''

@description('Run the worker in dry mode (sample data, no CRM/secrets).')
param dryRun bool = true

param crmUrl string = ''
param entraTenantId string = ''
param entraClientId string = ''

@secure()
param approvalToken string = newGuid()

@secure()
param entraClientSecret string = ''

@description('Enable Entra ID (Easy Auth) on the worker ingress.')
param enableEasyAuth bool = false

@description('Entra app (client) ID fronting the worker for Easy Auth.')
param easyAuthClientId string = ''

var tags = { 'azd-env-name': environmentName }

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    namePrefix: environmentName
    location: location
    msxWorkerImage: empty(msxWorkerImage) ? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' : msxWorkerImage
    dryRun: dryRun
    crmUrl: crmUrl
    entraTenantId: entraTenantId
    entraClientId: entraClientId
    approvalToken: approvalToken
    entraClientSecret: entraClientSecret
    enableEasyAuth: enableEasyAuth
    easyAuthClientId: easyAuthClientId
  }
}

output MSX_WORKER_URL string = resources.outputs.MSX_WORKER_URL
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.AZURE_CONTAINER_REGISTRY_ENDPOINT
output AZURE_KEY_VAULT_NAME string = resources.outputs.AZURE_KEY_VAULT_NAME
output AZURE_RESOURCE_GROUP string = resources.outputs.AZURE_RESOURCE_GROUP
output EASY_AUTH_ENABLED bool = resources.outputs.EASY_AUTH_ENABLED
