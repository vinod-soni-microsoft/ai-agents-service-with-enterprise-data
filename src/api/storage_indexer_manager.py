"""
Storage Indexer Manager for Azure AI Search integration with Azure Blob Storage.

This module provides functionality to create and manage Azure AI Search indexers
that automatically index documents from Azure Blob Storage.
"""

import logging
from typing import Optional
from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.indexes.aio import SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndexer,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataContainer,
    IndexingSchedule,
    IndexingParameters,
    FieldMapping,
)
from azure.core.exceptions import ResourceExistsError, HttpResponseError

logger = logging.getLogger(__name__)


class StorageIndexerManager:
    """
    Manages Azure AI Search indexers for blob storage integration.
    
    :param search_endpoint: The Azure AI Search service endpoint
    :param credential: The credential to authenticate with Azure services
    :param storage_account_name: The name of the storage account
    :param storage_container_name: The name of the blob container to index
    :param index_name: The name of the search index to populate
    :param data_source_name: Optional custom name for the data source
    :param indexer_name: Optional custom name for the indexer
    """
    
    def __init__(
        self,
        search_endpoint: str,
        credential: AsyncTokenCredential,
        storage_account_name: str,
        storage_container_name: str = 'documents',
        index_name: str = 'default',
        data_source_name: Optional[str] = None,
        indexer_name: Optional[str] = None
    ) -> None:
        """Initialize the StorageIndexerManager."""
        self._search_endpoint = search_endpoint
        self._credential = credential
        self._storage_account_name = storage_account_name
        self._storage_container_name = storage_container_name
        self._index_name = index_name
        self._data_source_name = data_source_name or f'{storage_container_name}-datasource'
        self._indexer_name = indexer_name or f'{storage_container_name}-indexer'
        self._client: Optional[SearchIndexerClient] = None
    
    async def _get_client(self) -> SearchIndexerClient:
        """Get or create the search indexer client."""
        if self._client is None:
            self._client = SearchIndexerClient(
                endpoint=self._search_endpoint,
                credential=self._credential
            )
        return self._client
    
    async def create_or_update_data_source(self) -> SearchIndexerDataSourceConnection:
        """
        Create or update the data source connection to blob storage.
        
        :return: The data source connection
        """
        client = await self._get_client()
        
        # Build the connection string using managed identity
        storage_connection_string = (
            f'ResourceId=/subscriptions/{{subscription}}/resourceGroups/{{resourceGroup}}/'
            f'providers/Microsoft.Storage/storageAccounts/{self._storage_account_name};'
        )
        
        data_source = SearchIndexerDataSourceConnection(
            name=self._data_source_name,
            type='azureblob',
            connection_string=storage_connection_string,
            container=SearchIndexerDataContainer(name=self._storage_container_name)
        )
        
        try:
            result = await client.create_or_update_data_source_connection(data_source)
            logger.info(f"Data source '{self._data_source_name}' created/updated successfully")
            return result
        except HttpResponseError as e:
            logger.error(f"Failed to create/update data source: {e}")
            raise
    
    async def create_or_update_indexer(
        self,
        schedule_interval_minutes: int = 120
    ) -> SearchIndexer:
        """
        Create or update the indexer to automatically index blob storage.
        
        :param schedule_interval_minutes: How often the indexer should run (default: 120 minutes)
        :return: The created or updated indexer
        """
        client = await self._get_client()
        
        # Configure indexing parameters
        indexing_parameters = IndexingParameters(
            configuration={
                'dataToExtract': 'contentAndMetadata',
                'parsingMode': 'default',
                'indexedFileNameExtensions': '.pdf,.docx,.doc,.pptx,.ppt,.txt,.md,.json,.csv,.html',
                'excludedFileNameExtensions': '.png,.jpg,.jpeg,.gif,.bmp,.ico'
            }
        )
        
        # Map blob storage metadata fields to index fields
        field_mappings = [
            FieldMapping(
                source_field_name='metadata_storage_name',
                target_field_name='title'
            ),
            FieldMapping(
                source_field_name='content',
                target_field_name='token'
            )
        ]
        
        # Create indexing schedule (ISO 8601 duration format)
        schedule = IndexingSchedule(interval=f'PT{schedule_interval_minutes}M')
        
        indexer = SearchIndexer(
            name=self._indexer_name,
            data_source_name=self._data_source_name,
            target_index_name=self._index_name,
            parameters=indexing_parameters,
            field_mappings=field_mappings,
            schedule=schedule
        )
        
        try:
            result = await client.create_or_update_indexer(indexer)
            logger.info(f"Indexer '{self._indexer_name}' created/updated successfully")
            return result
        except HttpResponseError as e:
            logger.error(f"Failed to create/update indexer: {e}")
            raise
    
    async def run_indexer(self) -> None:
        """
        Manually trigger the indexer to run immediately.
        """
        client = await self._get_client()
        try:
            await client.run_indexer(self._indexer_name)
            logger.info(f"Indexer '{self._indexer_name}' started successfully")
        except HttpResponseError as e:
            logger.error(f"Failed to run indexer: {e}")
            raise
    
    async def get_indexer_status(self) -> dict:
        """
        Get the current status of the indexer.
        
        :return: Dictionary containing indexer status information
        """
        client = await self._get_client()
        try:
            status = await client.get_indexer_status(self._indexer_name)
            return {
                'name': status.name,
                'status': status.status,
                'last_result': {
                    'status': status.last_result.status if status.last_result else None,
                    'error_message': status.last_result.error_message if status.last_result else None,
                    'start_time': status.last_result.start_time if status.last_result else None,
                    'end_time': status.last_result.end_time if status.last_result else None,
                } if status.last_result else None
            }
        except HttpResponseError as e:
            logger.error(f"Failed to get indexer status: {e}")
            raise
    
    async def delete_indexer(self) -> None:
        """Delete the indexer."""
        client = await self._get_client()
        try:
            await client.delete_indexer(self._indexer_name)
            logger.info(f"Indexer '{self._indexer_name}' deleted successfully")
        except HttpResponseError as e:
            logger.error(f"Failed to delete indexer: {e}")
            raise
    
    async def delete_data_source(self) -> None:
        """Delete the data source connection."""
        client = await self._get_client()
        try:
            await client.delete_data_source_connection(self._data_source_name)
            logger.info(f"Data source '{self._data_source_name}' deleted successfully")
        except HttpResponseError as e:
            logger.error(f"Failed to delete data source: {e}")
            raise
    
    async def setup_storage_indexing(self, schedule_interval_minutes: int = 120) -> dict:
        """
        Complete setup of storage indexing (creates data source and indexer).
        
        :param schedule_interval_minutes: How often the indexer should run
        :return: Dictionary with setup results
        """
        try:
            # Create data source
            data_source = await self.create_or_update_data_source()
            
            # Create indexer
            indexer = await self.create_or_update_indexer(schedule_interval_minutes)
            
            # Run indexer immediately
            await self.run_indexer()
            
            return {
                'success': True,
                'data_source_name': data_source.name,
                'indexer_name': indexer.name,
                'message': 'Storage indexing setup completed successfully'
            }
        except Exception as e:
            logger.error(f"Failed to setup storage indexing: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to setup storage indexing'
            }
    
    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None
