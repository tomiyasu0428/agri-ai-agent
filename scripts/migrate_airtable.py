#!/usr/bin/env python3
"""
Script to migrate data from Airtable to MongoDB.
"""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.core.database import MongoDBClient
from agri_ai.utils.airtable_client import AirtableClient, AirtableToMongoMigrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main migration function."""
    print("=== Airtable to MongoDB Migration Tool ===\n")
    
    try:
        # Initialize clients
        print("1. Initializing Airtable client...")
        airtable_client = AirtableClient()
        
        print("2. Initializing MongoDB client...")
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        
        # Test connections
        print("3. Testing connections...")
        
        # Test Airtable connection
        tables = airtable_client.list_tables()
        if tables:
            print(f"   ✓ Airtable connected. Found tables: {', '.join(tables)}")
        else:
            print("   ⚠️  No Airtable tables found. Please check your API key and base ID.")
            return
        
        # Test MongoDB connection
        health = await mongo_client.health_check()
        if health:
            print("   ✓ MongoDB connected successfully.")
        else:
            print("   ❌ MongoDB connection failed.")
            return
        
        # Show table schemas
        print("\n4. Analyzing Airtable table structures...")
        for table_name in tables:
            schema = airtable_client.get_table_schema(table_name)
            print(f"   Table: {table_name}")
            print(f"   Fields: {schema.get('fields', [])}")
            print(f"   Record count: {schema.get('record_count', 0)}")
            if schema.get('error'):
                print(f"   Error: {schema['error']}")
            print()
        
        # Confirm migration
        response = input("Do you want to proceed with the migration? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
        
        # Initialize migrator
        print("\n5. Starting migration...")
        migrator = AirtableToMongoMigrator(airtable_client, mongo_client)
        
        # Run migration
        result = await migrator.migrate_all_tables()
        
        # Display results
        print("\n=== Migration Results ===")
        print(f"Migration started: {result['migration_started']}")
        print(f"Migration completed: {result.get('migration_completed', 'N/A')}")
        print(f"Tables migrated: {result['tables_migrated']}")
        print(f"Total records migrated: {result['total_records']}")
        
        if result['table_results']:
            print("\nTable-by-table results:")
            for table_result in result['table_results']:
                status = "✓" if table_result['success'] else "❌"
                print(f"  {status} {table_result['table_name']} -> {table_result['mongo_collection']}: {table_result['records_migrated']} records")
        
        if result['errors']:
            print(f"\nErrors encountered:")
            for error in result['errors']:
                print(f"  - {error}")
        
        # Save migration report
        report_file = f"migration_report_{result['migration_started'].replace(':', '-')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()
        print("\nMigration script completed.")


if __name__ == "__main__":
    asyncio.run(main())