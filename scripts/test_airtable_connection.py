#!/usr/bin/env python3
"""
Script to test Airtable connection and explore data structure.
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.utils.airtable_client import AirtableClient


def main():
    """Test Airtable connection and show data structure."""
    print("=== Airtable Connection Test ===\n")
    
    try:
        # Initialize client
        print("1. Initializing Airtable client...")
        client = AirtableClient()
        print("   ✓ Client initialized")
        
        # List tables
        print("\n2. Discovering tables...")
        tables = client.list_tables()
        
        if not tables:
            print("   ⚠️  No tables found. This could mean:")
            print("   - Incorrect API key or base ID")
            print("   - Tables have different names than expected")
            print("   - Base is empty")
            return
        
        print(f"   ✓ Found {len(tables)} tables: {', '.join(tables)}")
        
        # Analyze each table
        print("\n3. Analyzing table structures...")
        for table_name in tables:
            print(f"\n--- Table: {table_name} ---")
            
            schema = client.get_table_schema(table_name)
            
            if schema.get('error'):
                print(f"❌ Error: {schema['error']}")
                continue
            
            print(f"Fields: {schema.get('fields', [])}")
            print(f"Record count: {schema.get('record_count', 0)}")
            
            # Show sample record
            if schema.get('sample'):
                print("Sample record:")
                sample_fields = schema['sample'].get('fields', {})
                for field, value in sample_fields.items():
                    # Truncate long values
                    display_value = str(value)
                    if len(display_value) > 50:
                        display_value = display_value[:47] + "..."
                    print(f"  {field}: {display_value}")
        
        # Test getting all records from first table
        if tables:
            first_table = tables[0]
            print(f"\n4. Testing record retrieval from '{first_table}'...")
            
            records = client.get_all_records(first_table)
            print(f"   ✓ Retrieved {len(records)} records")
            
            if records:
                print("   Sample record structure:")
                sample = records[0]
                print(f"   ID: {sample.get('id')}")
                print(f"   Created: {sample.get('createdTime')}")
                print(f"   Fields: {list(sample.get('fields', {}).keys())}")
        
        print("\n✅ Airtable connection test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your AIRTABLE_API_KEY in .env file")
        print("2. Check your AIRTABLE_BASE_ID in .env file")
        print("3. Ensure you have read access to the Airtable base")
        print("4. Verify the base contains tables with the expected names")


if __name__ == "__main__":
    main()