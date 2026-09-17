<#
Deploy the StudyOS API (Point & Ask backend) to AWS App Runner from a container image.

Prereqs: aws cli v2 signed in (aws configure / aws sso login), Docker running, Bedrock model access enabled in the region.
Usage:
  .\scripts\deploy_aws.ps1 -Region us-east-1
  .\scripts\deploy_aws.ps1 -Region us-east-1 -DatabaseUrl "postgresql+psycopg://user:pw@host:5432/lp"   # RDS
Without -DatabaseUrl the service runs SQLite inside the container (demo only; data resets on redeploy).
#>
param(
  [string]$Region = "us-east-1",
  [string]$Service = "studyos-point-ask",
  [string]$Repo = "studyos-api",
  [string]$DatabaseUrl = "",
  [string]$JwtSecret = "",
  [string]$BedrockModel = "amazon.nova-lite-v1:0",
  [string]$Cpu = "1 vCPU",
  [string]$Memory = "2 GB"
)
$ErrorActionPreference = "Stop"
if (-not $JwtSecret) { $JwtSecret = -join ((1..48) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) }) }
$account = (aws sts get-caller-identity --query Account --output text)
$registry = "$account.dkr.ecr.$Region.amazonaws.com"
$image = "$registry/${Repo}:latest"

Write-Host "== ECR repo + login"
aws ecr describe-repositories --repository-names $Repo --region $Region 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { aws ecr create-repository --repository-name $Repo --region $Region | Out-Null }
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $registry

Write-Host "== build + push $image"
docker build -f docker/Dockerfile.api -t $image .
docker push $image

Write-Host "== IAM: access role (ECR pull) + instance role (Bedrock)"
$trustAccess = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"build.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
$trustTasks  = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"tasks.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
$bedrockPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream","bedrock:Converse","bedrock:ConverseStream"],"Resource":"*"}]}'
$accessRoleName = "AppRunnerECRAccessRole-$Service"
$instanceRoleName = "AppRunnerInstanceRole-$Service"
aws iam get-role --role-name $accessRoleName 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { aws iam create-role --role-name $accessRoleName --assume-role-policy-document $trustAccess | Out-Null; Start-Sleep 8 }
aws iam get-role --role-name $instanceRoleName 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { aws iam create-role --role-name $instanceRoleName --assume-role-policy-document $trustTasks | Out-Null; Start-Sleep 8 }
aws iam attach-role-policy --role-name $accessRoleName --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
aws iam put-role-policy --role-name $instanceRoleName --policy-name bedrock-invoke --policy-document $bedrockPolicy
$accessRole = "arn:aws:iam::${account}:role/$accessRoleName"
$instanceRole = "arn:aws:iam::${account}:role/$instanceRoleName"

$dbUrl = if ($DatabaseUrl) { $DatabaseUrl } else { "sqlite:////workspace/services/api/.data/prod.db" }
$envVars = [ordered]@{
  ENVIRONMENT = "production"; JWT_SECRET_KEY = $JwtSecret; PORT = "8000"
  DATABASE_URL = $dbUrl; STORAGE_BACKEND = "local"; ASYNC_INGESTION = "false"
  SPATIAL_PROVIDERS = "bedrock"; BEDROCK_ENABLED = "1"; AWS_REGION = $Region
  BEDROCK_MODEL = $BedrockModel; BEDROCK_VISION_MODEL = $BedrockModel
  SPATIAL_TTS = "0"; SPATIAL_OCR = "0"
  SPATIAL_ANONYMOUS_DAILY_LIMIT = "20"; SPATIAL_USER_DAILY_LIMIT = "200"; SPATIAL_DAILY_COST_CAP_USD = "0.25"
}
$source = @{
  ImageRepository = @{
    ImageIdentifier = $image; ImageRepositoryType = "ECR"
    ImageConfiguration = @{ Port = "8000"; RuntimeEnvironmentVariables = $envVars }
  }
  AutoDeploymentsEnabled = $false
  AuthenticationConfiguration = @{ AccessRoleArn = $accessRole }
} | ConvertTo-Json -Depth 6 -Compress
$health = '{"Protocol":"HTTP","Path":"/api/health","Interval":10,"Timeout":5,"HealthyThreshold":1,"UnhealthyThreshold":5}'
$instance = @{ Cpu = $Cpu; Memory = $Memory; InstanceRoleArn = $instanceRole } | ConvertTo-Json -Compress
$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value $source -Encoding utf8

$arn = (aws apprunner list-services --region $Region --query "ServiceSummaryList[?ServiceName=='$Service'].ServiceArn" --output text)
if ($arn) {
  Write-Host "== update $arn"
  aws apprunner update-service --region $Region --service-arn $arn --source-configuration "file://$tmp" --instance-configuration $instance --health-check-configuration $health | Out-Null
} else {
  Write-Host "== create $Service"
  $arn = (aws apprunner create-service --region $Region --service-name $Service --source-configuration "file://$tmp" --instance-configuration $instance --health-check-configuration $health --query Service.ServiceArn --output text)
}
Write-Host "== waiting for RUNNING"
do {
  Start-Sleep 15
  $status = (aws apprunner describe-service --region $Region --service-arn $arn --query Service.Status --output text)
  Write-Host "   $status"
} while ($status -in @("OPERATION_IN_PROGRESS", "CREATE_IN_PROGRESS"))
$url = "https://" + (aws apprunner describe-service --region $Region --service-arn $arn --query Service.ServiceUrl --output text)
Write-Host ""
Write-Host "API:      $url/api/health"
Write-Host "Landing:  $url/point-and-ask/"
Write-Host "Privacy:  $url/point-and-ask/privacy.html"
Write-Host "Next:     py -3.12 scripts/package_extension.py --api-base $url"
