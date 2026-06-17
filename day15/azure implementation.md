# Step-by-Step Azure Portal Implementation Guide

## Architecture Overview

This guide covers building an asynchronous, data-driven architecture on Azure using:

- **Input Queue:** Azure Service Bus (Queue)
- **Store:** Azure Cosmos DB (NoSQL API)
- **Container Registry:** Azure Container Registry (ACR)
- **Deployment Host:** Azure Container Apps (ACA)

**Data Flow:**
1. A FastAPI ingestion endpoint receives a request and drops a message into the Azure Service Bus Queue
2. A background worker picks up the message, processes it, and saves the record to Azure Cosmos DB
3. Another FastAPI endpoint reads data from Cosmos DB, sends it to the Anthropic Claude API for enrichment/analysis, and returns the final payload

---

## Step 1: Create the Managed Database (Azure Cosmos DB)

1. Sign in to the **Azure Portal**
2. Click **Create a resource**, search for **Azure Cosmos DB**, and click **Create**
3. Select **Azure Cosmos DB for NoSQL** and click **Create**
4. Configure the settings:
   - **Resource Group:** Create new (e.g., `rg-pipeline-prod`)
   - **Account Name:** Unique name (e.g., `cosmos-pipeline-data`)
   - **Capacity mode:** Select **Serverless** (highly cost-effective for development/testing)
5. Click **Review + create**, then click **Create**
6. Once deployed, navigate to the resource, go to **Keys** under settings, and copy the **URI** and **Primary Key**

---

## Step 2: Create the Input Queue (Azure Service Bus)

1. Click **Create a resource**, search for **Service Bus**, and click **Create**
2. Configure the Namespace:
   - **Resource Group:** Select `rg-pipeline-prod`
   - **Namespace name:** Unique name (e.g., `sb-pipeline-queue`)
   - **Pricing tier:** Standard (required for SQL filters and fundamental queueing features)
3. Click **Review + create**, then click **Create**
4. Once deployed, navigate to the Service Bus Namespace, click **Queues** under the left menu, and click **+ Queue**
5. Name your queue `input-queue` and leave defaults, then click **Create**
6. Go to **Shared access policies** under the namespace settings, click **RootManageSharedAccessKey**, and copy the **Primary Connection String**

---

## Step 3: Create the Container App (Azure Container Apps)

1. Click **Create a resource**, search for **Container Apps**, and click **Create**
2. Fill in the **Basics** tab:
   - **Subscription:** Select your subscription (e.g., Learner Account)
   - **Resource Group:** Select `rg-pipeline-prod`
   - **Container app name:** e.g., `fastapi-container`
   - **Deployment source:** Select **Container image**
   - **Region:** e.g., West US 2
3. Proceed to the **Container**, **Ingress**, **Tags** tabs and configure as needed
4. Click **Review + create**, then click **Create**

---

## Step 4: Containerize & Create Azure Container Registry (ACR)

1. In the Azure Portal, click **Create a resource**, search for **Container Registry**, and click **Create**
2. Select your resource group, name your registry (e.g., `acrpipelineprod`), and select **Standard** SKU. Click **Review + create**, then **Create**
3. Once created, go to the registry resource, select **Access keys** under settings, and enable **Admin user**. Copy the username and password
4. Open your local terminal, build and push your image to ACR using Docker:

```bash
docker login acrpipelineprod.azurecr.io -u <AdminUsername> -p <AdminPassword>
docker build -t acrpipelineprod.azurecr.io/pipeline-app:v1 .
docker push acrpipelineprod.azurecr.io/pipeline-app:v1
```

---

## Summary of Resources Created

| Resource | Name Example | Purpose |
|---|---|---|
| Resource Group | `rg-pipeline-prod` | Organizes all resources |
| Cosmos DB Account | `cosmos-pipeline-data` | NoSQL data store |
| Service Bus Namespace | `sb-pipeline-queue` | Input message queue |
| Service Bus Queue | `input-queue` | Message intake |
| Container Registry | `acrpipelineprod` | Stores Docker images |
| Container App | `fastapi-container` | Hosts the FastAPI app |
