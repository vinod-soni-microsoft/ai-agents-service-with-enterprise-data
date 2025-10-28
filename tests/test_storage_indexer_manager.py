# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.
# See LICENSE file in the project root for full license information.

import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from azure.identity.aio import DefaultAzureCredential

from storage_indexer_manager import StorageIndexerManager
from azure.core.exceptions import HttpResponseError


class TestStorageIndexerManager(unittest.IsolatedAsyncioTestCase):
    """Tests for the Storage Indexer Manager."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.search_endpoint = "https://test-search.search.windows.net"
        self.storage_account_name = "teststorage"
        self.storage_container_name = "documents"
        self.index_name = "test-index"
        unittest.TestCase.setUp(self)

    async def test_initialization(self):
        """Test that the manager initializes correctly."""
        manager = StorageIndexerManager(
            search_endpoint=self.search_endpoint,
            credential=AsyncMock(),
            storage_account_name=self.storage_account_name,
            storage_container_name=self.storage_container_name,
            index_name=self.index_name
        )
        
        self.assertEqual(manager._search_endpoint, self.search_endpoint)
        self.assertEqual(manager._storage_account_name, self.storage_account_name)
        self.assertEqual(manager._storage_container_name, self.storage_container_name)
        self.assertEqual(manager._index_name, self.index_name)
        self.assertEqual(manager._data_source_name, 'documents-datasource')
        self.assertEqual(manager._indexer_name, 'documents-indexer')

    async def test_create_data_source_mock(self):
        """Test creating a data source connection."""
        mock_client = AsyncMock()
        mock_client.create_or_update_data_source_connection = AsyncMock()
        
        with patch('storage_indexer_manager.SearchIndexerClient', return_value=mock_client):
            manager = StorageIndexerManager(
                search_endpoint=self.search_endpoint,
                credential=AsyncMock(),
                storage_account_name=self.storage_account_name,
                storage_container_name=self.storage_container_name,
                index_name=self.index_name
            )
            
            await manager.create_or_update_data_source()
            mock_client.create_or_update_data_source_connection.assert_called_once()

    async def test_create_indexer_mock(self):
        """Test creating an indexer."""
        mock_client = AsyncMock()
        mock_client.create_or_update_indexer = AsyncMock()
        
        with patch('storage_indexer_manager.SearchIndexerClient', return_value=mock_client):
            manager = StorageIndexerManager(
                search_endpoint=self.search_endpoint,
                credential=AsyncMock(),
                storage_account_name=self.storage_account_name,
                storage_container_name=self.storage_container_name,
                index_name=self.index_name
            )
            
            await manager.create_or_update_indexer(schedule_interval_minutes=60)
            mock_client.create_or_update_indexer.assert_called_once()

    async def test_run_indexer_mock(self):
        """Test running an indexer manually."""
        mock_client = AsyncMock()
        mock_client.run_indexer = AsyncMock()
        
        with patch('storage_indexer_manager.SearchIndexerClient', return_value=mock_client):
            manager = StorageIndexerManager(
                search_endpoint=self.search_endpoint,
                credential=AsyncMock(),
                storage_account_name=self.storage_account_name,
                storage_container_name=self.storage_container_name,
                index_name=self.index_name
            )
            
            await manager.run_indexer()
            mock_client.run_indexer.assert_called_once_with('documents-indexer')

    async def test_get_indexer_status_mock(self):
        """Test getting indexer status."""
        mock_status = MagicMock()
        mock_status.name = 'documents-indexer'
        mock_status.status = 'running'
        mock_status.last_result = None
        
        mock_client = AsyncMock()
        mock_client.get_indexer_status = AsyncMock(return_value=mock_status)
        
        with patch('storage_indexer_manager.SearchIndexerClient', return_value=mock_client):
            manager = StorageIndexerManager(
                search_endpoint=self.search_endpoint,
                credential=AsyncMock(),
                storage_account_name=self.storage_account_name,
                storage_container_name=self.storage_container_name,
                index_name=self.index_name
            )
            
            status = await manager.get_indexer_status()
            self.assertEqual(status['name'], 'documents-indexer')
            self.assertEqual(status['status'], 'running')
            self.assertIsNone(status['last_result'])

    async def test_setup_storage_indexing_success_mock(self):
        """Test complete setup of storage indexing."""
        mock_data_source = MagicMock()
        mock_data_source.name = 'documents-datasource'
        
        mock_indexer = MagicMock()
        mock_indexer.name = 'documents-indexer'
        
        mock_client = AsyncMock()
        mock_client.create_or_update_data_source_connection = AsyncMock(return_value=mock_data_source)
        mock_client.create_or_update_indexer = AsyncMock(return_value=mock_indexer)
        mock_client.run_indexer = AsyncMock()
        
        with patch('storage_indexer_manager.SearchIndexerClient', return_value=mock_client):
            manager = StorageIndexerManager(
                search_endpoint=self.search_endpoint,
                credential=AsyncMock(),
                storage_account_name=self.storage_account_name,
                storage_container_name=self.storage_container_name,
                index_name=self.index_name
            )
            
            result = await manager.setup_storage_indexing()
            
            self.assertTrue(result['success'])
            self.assertEqual(result['data_source_name'], 'documents-datasource')
            self.assertEqual(result['indexer_name'], 'documents-indexer')
            mock_client.create_or_update_data_source_connection.assert_called_once()
            mock_client.create_or_update_indexer.assert_called_once()
            mock_client.run_indexer.assert_called_once()

    async def test_setup_storage_indexing_failure_mock(self):
        """Test setup failure handling."""
        mock_client = AsyncMock()
        mock_client.create_or_update_data_source_connection = AsyncMock(
            side_effect=HttpResponseError('Failed to create data source')
        )
        
        with patch('storage_indexer_manager.SearchIndexerClient', return_value=mock_client):
            manager = StorageIndexerManager(
                search_endpoint=self.search_endpoint,
                credential=AsyncMock(),
                storage_account_name=self.storage_account_name,
                storage_container_name=self.storage_container_name,
                index_name=self.index_name
            )
            
            result = await manager.setup_storage_indexing()
            
            self.assertFalse(result['success'])
            self.assertIn('error', result)

    async def test_delete_indexer_mock(self):
        """Test deleting an indexer."""
        mock_client = AsyncMock()
        mock_client.delete_indexer = AsyncMock()
        
        with patch('storage_indexer_manager.SearchIndexerClient', return_value=mock_client):
            manager = StorageIndexerManager(
                search_endpoint=self.search_endpoint,
                credential=AsyncMock(),
                storage_account_name=self.storage_account_name,
                storage_container_name=self.storage_container_name,
                index_name=self.index_name
            )
            
            await manager.delete_indexer()
            mock_client.delete_indexer.assert_called_once_with('documents-indexer')

    async def test_delete_data_source_mock(self):
        """Test deleting a data source."""
        mock_client = AsyncMock()
        mock_client.delete_data_source_connection = AsyncMock()
        
        with patch('storage_indexer_manager.SearchIndexerClient', return_value=mock_client):
            manager = StorageIndexerManager(
                search_endpoint=self.search_endpoint,
                credential=AsyncMock(),
                storage_account_name=self.storage_account_name,
                storage_container_name=self.storage_container_name,
                index_name=self.index_name
            )
            
            await manager.delete_data_source()
            mock_client.delete_data_source_connection.assert_called_once_with('documents-datasource')

    async def test_close(self):
        """Test closing the client."""
        mock_client = AsyncMock()
        
        with patch('storage_indexer_manager.SearchIndexerClient', return_value=mock_client):
            manager = StorageIndexerManager(
                search_endpoint=self.search_endpoint,
                credential=AsyncMock(),
                storage_account_name=self.storage_account_name,
                storage_container_name=self.storage_container_name,
                index_name=self.index_name
            )
            
            # Initialize the client first
            await manager._get_client()
            
            # Now close it
            await manager.close()
            self.assertIsNone(manager._client)
            mock_client.close.assert_called_once()

    @unittest.skip("Only for live tests.")
    async def test_e2e(self):
        """End-to-end test with real Azure services (requires environment variables)."""
        search_endpoint = os.environ.get("AZURE_AI_SEARCH_ENDPOINT")
        storage_account_name = os.environ.get("STORAGE_ACCOUNT_NAME")
        index_name = os.environ.get("AZURE_AI_SEARCH_INDEX_NAME", "test-index")
        
        if not search_endpoint or not storage_account_name:
            self.skipTest("Environment variables not set for live test")
        
        async with DefaultAzureCredential() as creds:
            manager = StorageIndexerManager(
                search_endpoint=search_endpoint,
                credential=creds,
                storage_account_name=storage_account_name,
                storage_container_name='documents',
                index_name=index_name
            )
            
            try:
                # Set up storage indexing
                result = await manager.setup_storage_indexing()
                self.assertTrue(result['success'])
                
                # Get indexer status
                status = await manager.get_indexer_status()
                self.assertIsNotNone(status)
                
            finally:
                # Clean up
                try:
                    await manager.delete_indexer()
                    await manager.delete_data_source()
                except:
                    pass
                await manager.close()


if __name__ == "__main__":
    unittest.main()
