"""Test ChromaDB persistence across service restarts."""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from src.services.vector_service_chroma import VectorServiceChroma

def test_persistence():
    """Test that data persists across service restarts."""
    print("=" * 60)
    print("CHROMADB PERSISTENCE TEST")
    print("=" * 60)

    # Step 1: Create first instance and insert data
    print("\nStep 1: Creating first instance and inserting test data...")
    service1 = VectorServiceChroma()
    service1.load_model()
    service1.create_collection()

    test_chunks = [
        {"text": "Persistence test chunk 1: ChromaDB should save this data."},
        {"text": "Persistence test chunk 2: Data should survive service restarts."},
        {"text": "Persistence test chunk 3: This is a test of the persistence layer."}
    ]

    service1.insert_chunks(
        domain="persistence.test",
        site_name="Persistence Test Site",
        page_name="test_page",
        page_url="https://persistence.test/page",
        chunks=test_chunks
    )

    print("✓ Test data inserted")
    print(f"  - Domain: persistence.test")
    print(f"  - Chunks inserted: {len(test_chunks)}")

    # Search to verify data is there
    results1 = service1.search("persistence", top_k=10)
    print(f"✓ Initial search found {len(results1)} results")

    # Step 2: Close the first instance
    print("\nStep 2: Closing first instance...")
    service1.close()
    print("✓ First instance closed")

    # Step 3: Create new instance (simulating restart)
    print("\nStep 3: Creating new instance (simulating restart)...")
    service2 = VectorServiceChroma()
    service2.load_model()
    service2.create_collection()
    print("✓ New instance created")

    # Step 4: Search for the same data
    print("\nStep 4: Searching for previously inserted data...")
    results2 = service2.search("persistence", top_k=10, filter_domain="persistence.test")

    print(f"✓ Persistence search found {len(results2)} results")

    if len(results2) > 0:
        print("\n✓ DATA PERSISTED SUCCESSFULLY!")
        print(f"  - Found {len(results2)} chunks after restart")
        for i, result in enumerate(results2):
            print(f"  - Chunk {i+1}: {result['chunk_text'][:60]}...")

        # Cleanup - delete test data
        print("\nCleaning up test data...")
        service2.delete_by_domain("persistence.test")
        print("✓ Test data deleted")

        # Verify deletion
        results3 = service2.search("persistence", top_k=10, filter_domain="persistence.test")
        if len(results3) == 0:
            print("✓ Cleanup verified (no results found)")
        else:
            print(f"⚠ Cleanup verification: {len(results3)} results still found")

        service2.close()
        return True
    else:
        print("\n✗ DATA DID NOT PERSIST!")
        print("  - No results found after restart")
        service2.close()
        return False

def main():
    """Run persistence test."""
    try:
        success = test_persistence()

        print("\n" + "=" * 60)
        if success:
            print("PERSISTENCE TEST: ✓ PASSED")
        else:
            print("PERSISTENCE TEST: ✗ FAILED")
        print("=" * 60)

        return success
    except Exception as e:
        print(f"\n✗ Persistence test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
