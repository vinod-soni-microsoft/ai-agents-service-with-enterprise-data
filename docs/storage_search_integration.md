# Storage Account Integration with AI Search Service

This document explains how the Azure Storage Account is integrated with Azure AI Search service to enable automatic indexing of documents.

## Overview

The integration allows documents uploaded to Azure Blob Storage to be automatically indexed by Azure AI Search, making them searchable through the AI agent. This provides a scalable solution for enterprise data that doesn't require manual embedding generation.

## Architecture

1. **Storage Account**: Contains a `documents` container where files can be uploaded
2. **AI Search Service**: Configured with a data source pointing to the storage container
3. **Indexer**: Automatically crawls the storage container and indexes new/updated documents
4. **Search Index**: Stores the indexed content with metadata for efficient retrieval

## Infrastructure Components

### Storage Account
- Bicep location: `infra/core/storage/storage-account.bicep`
- Container: `documents` (configured in `infra/core/host/ai-environment.bicep`)
- Access: Managed Identity authentication

### AI Search Service
- Bicep location: `infra/core/search/search-services.bicep`
- Features: Semantic search, vector search
- Authentication: API Key + Azure AD

### Role Assignments
The following role assignments are configured:
- **AI Search → Storage Account**: `Storage Blob Data Reader` (read documents)
- **API Container App → Storage Account**: `Storage Blob Data Contributor` (upload/manage documents)
- **AI Services → Storage Account**: `Storage Blob Data Contributor` (access project storage)

## Code Components

### StorageIndexerManager
- Location: `src/api/storage_indexer_manager.py` and `src/backend/api/storage_indexer_manager.py`
- Purpose: Manages AI Search indexers programmatically
- Key methods:
  - `create_or_update_data_source()`: Creates data source connection to blob storage
  - `create_or_update_indexer()`: Creates indexer to automatically index documents
  - `run_indexer()`: Manually triggers indexing
  - `get_indexer_status()`: Checks indexer execution status
  - `setup_storage_indexing()`: Complete setup in one call

### Usage Example

```python
from azure.identity.aio import DefaultAzureCredential
from storage_indexer_manager import StorageIndexerManager

async def setup_indexing():
    credential = DefaultAzureCredential()
    
    manager = StorageIndexerManager(
        search_endpoint="https://<search-service>.search.windows.net",
        credential=credential,
        storage_account_name="<storage-account-name>",
        storage_container_name="documents",
        index_name="my-index"
    )
    
    # Set up complete indexing pipeline
    result = await manager.setup_storage_indexing(schedule_interval_minutes=120)
    
    if result['success']:
        print(f"Indexer created: {result['indexer_name']}")
    else:
        print(f"Error: {result['error']}")
    
    await manager.close()
```

## Supported File Types

The indexer is configured to extract content from the following file types:
- PDF (.pdf)
- Microsoft Word (.docx, .doc)
- Microsoft PowerPoint (.pptx, .ppt)
- Text files (.txt, .md)
- JSON (.json)
- CSV (.csv)
- HTML (.html)

## Indexing Schedule

By default, the indexer runs every 2 hours (120 minutes). This can be customized when creating the indexer:

```python
await manager.create_or_update_indexer(schedule_interval_minutes=60)  # Run every hour
```

## Field Mappings

The indexer maps blob storage metadata to index fields:
- `metadata_storage_name` → `title`: Document filename
- `content` → `token`: Extracted document content

## Environment Variables

The following environment variables are used:
- `AZURE_STORAGE_ACCOUNT_NAME`: Name of the storage account
- `AZURE_STORAGE_CONTAINER_NAME`: Container name (default: "documents")
- `AZURE_AI_SEARCH_ENDPOINT`: AI Search service endpoint
- `AZURE_AI_SEARCH_INDEX_NAME`: Name of the search index

## Testing

Unit tests are available in `tests/test_storage_indexer_manager.py`:

```bash
python -m pytest tests/test_storage_indexer_manager.py -v
```

For live testing with actual Azure resources, set the appropriate environment variables and use the `test_e2e` test (currently skipped by default).

## Deployment

The storage integration is deployed automatically when you run:

```bash
azd up
```

Ensure that `useSearchService` parameter is set to `true` in your deployment configuration to enable AI Search.

## Monitoring

You can monitor indexer execution:

```python
status = await manager.get_indexer_status()
print(f"Indexer status: {status['status']}")
print(f"Last run: {status['last_result']}")
```

## Troubleshooting

### Indexer Not Running
- Check that the storage account is accessible by the AI Search service
- Verify role assignments are correctly configured
- Check indexer status for error messages

### Documents Not Being Indexed
- Verify file types are supported
- Check that files are uploaded to the correct container
- Manually trigger the indexer: `await manager.run_indexer()`

### Permission Errors
- Ensure Managed Identity is enabled for AI Search
- Verify role assignments: `Storage Blob Data Reader` for AI Search
- Check that the storage account allows access from trusted Azure services

## Best Practices

1. **Use Managed Identity**: Avoid using connection strings with keys
2. **Regular Monitoring**: Check indexer status periodically
3. **Batch Uploads**: Upload documents in batches rather than individually
4. **File Naming**: Use descriptive filenames as they become document titles
5. **Content Organization**: Organize documents in the container logically
6. **Schedule Optimization**: Adjust indexing frequency based on upload patterns

## Security Considerations

- Storage account uses Managed Identity authentication (no keys required)
- Network access is restricted to Azure services
- AI Search uses Azure AD authentication where possible
- Role assignments follow principle of least privilege

## Future Enhancements

Potential improvements for the integration:
- Add support for custom skillsets (AI enrichment)
- Implement incremental indexing for large datasets
- Add document change tracking
- Support for multiple containers
- Custom field extractors for specialized document types
