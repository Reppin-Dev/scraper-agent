"""Test ChromaDB vector service migration."""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from src.services.vector_service_chroma import vector_service

def test_initialization():
    """Test vector service initialization."""
    print("=" * 60)
    print("TEST 1: Vector Service Initialization")
    print("=" * 60)

    try:
        vector_service._connect()
        print("✓ ChromaDB connection successful")
        print(f"  - DB path: {vector_service.db_path}")
        print(f"  - Connected: {vector_service.connected}")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def test_model_loading():
    """Test BGE-M3 model loading."""
    print("\n" + "=" * 60)
    print("TEST 2: BGE-M3 Model Loading")
    print("=" * 60)

    try:
        vector_service.load_model()
        print("✓ BGE-M3 model loaded successfully")
        print(f"  - Model type: {type(vector_service.model)}")
        return True
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        return False

def test_collection_creation():
    """Test collection creation."""
    print("\n" + "=" * 60)
    print("TEST 3: Collection Creation")
    print("=" * 60)

    try:
        vector_service.create_collection()
        print("✓ Collection created/loaded successfully")
        print(f"  - Collection name: {vector_service.collection_name}")
        print(f"  - Collection object: {type(vector_service.collection)}")
        return True
    except Exception as e:
        print(f"✗ Collection creation failed: {e}")
        return False

def test_embedding():
    """Test text embedding."""
    print("\n" + "=" * 60)
    print("TEST 4: Text Embedding")
    print("=" * 60)

    try:
        test_text = "This is a test sentence for embedding."
        dense_vec, sparse_vec = vector_service.embed_text(test_text)

        print("✓ Text embedding successful")
        print(f"  - Input text: '{test_text}'")
        print(f"  - Dense vector dimension: {len(dense_vec)}")
        print(f"  - Dense vector type: {type(dense_vec)}")
        print(f"  - Sparse vector (should be empty dict): {sparse_vec}")
        print(f"  - Sample values: {dense_vec[:5]}")

        # Verify it's 1024 dimensions (BGE-M3)
        assert len(dense_vec) == 1024, f"Expected 1024 dimensions, got {len(dense_vec)}"
        print("  - ✓ Dimension validation passed (1024)")

        return True
    except Exception as e:
        print(f"✗ Embedding failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chunking():
    """Test markdown chunking."""
    print("\n" + "=" * 60)
    print("TEST 5: Markdown Chunking")
    print("=" * 60)

    try:
        test_markdown = """# Test Page

## Introduction
This is a test page with some content.

## Section 1
Here is some content in section 1.
It has multiple lines.

### Subsection 1.1
More detailed information here.

## Section 2
Different content in section 2.
"""

        chunks = vector_service.chunk_markdown(test_markdown, "test_page")

        print("✓ Markdown chunking successful")
        print(f"  - Input length: {len(test_markdown)} chars")
        print(f"  - Number of chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks):
            print(f"  - Chunk {i+1}:")
            print(f"    - Text length: {len(chunk['text'])} chars")
            print(f"    - Heading: {chunk.get('heading', 'N/A')}")
            print(f"    - Page name: {chunk.get('page_name', 'N/A')}")

        return True
    except Exception as e:
        print(f"✗ Chunking failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_insert_and_search():
    """Test inserting chunks and searching."""
    print("\n" + "=" * 60)
    print("TEST 6: Insert & Search")
    print("=" * 60)

    try:
        # Prepare test data
        test_domain = "example.com"
        test_site_name = "Example Site"
        test_page_name = "home"
        test_page_url = "https://example.com/home"

        test_chunks = [
            {"text": "Welcome to Example Gym. We offer yoga, pilates, and CrossFit classes."},
            {"text": "Our facility has state-of-the-art equipment and experienced trainers."},
            {"text": "Join us today for a free trial session. Contact us at info@example.com."}
        ]

        # Track progress
        progress_steps = []
        def progress_callback(current, total):
            progress_steps.append((current, total))
            print(f"  - Progress: {current}/{total}")

        print("\nInserting chunks...")
        vector_service.insert_chunks(
            domain=test_domain,
            site_name=test_site_name,
            page_name=test_page_name,
            page_url=test_page_url,
            chunks=test_chunks,
            progress_callback=progress_callback
        )

        print("✓ Chunks inserted successfully")
        print(f"  - Progress callbacks: {len(progress_steps)}")
        print(f"  - Final progress: {progress_steps[-1] if progress_steps else 'N/A'}")

        # Test search
        print("\nSearching for 'yoga classes'...")
        search_results = vector_service.search(
            query="yoga classes",
            top_k=3
        )

        print("✓ Search successful")
        print(f"  - Results found: {len(search_results)}")
        for i, result in enumerate(search_results):
            print(f"  - Result {i+1}:")
            print(f"    - Chunk ID: {result['chunk_id']}")
            print(f"    - Domain: {result['domain']}")
            print(f"    - Site name: {result['site_name']}")
            print(f"    - Score: {result['score']:.4f}")
            print(f"    - Text preview: {result['chunk_text'][:80]}...")

        return True
    except Exception as e:
        print(f"✗ Insert/Search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_filtered_search():
    """Test search with domain/site filters."""
    print("\n" + "=" * 60)
    print("TEST 7: Filtered Search")
    print("=" * 60)

    try:
        # Search with domain filter
        print("\nSearching with domain filter (example.com)...")
        results = vector_service.search(
            query="equipment trainers",
            top_k=5,
            filter_domain="example.com"
        )

        print("✓ Domain-filtered search successful")
        print(f"  - Results: {len(results)}")

        # Search with site filter
        print("\nSearching with site filter (Example Site)...")
        results = vector_service.search(
            query="contact information",
            top_k=5,
            filter_site="Example Site"
        )

        print("✓ Site-filtered search successful")
        print(f"  - Results: {len(results)}")

        # Search with both filters
        print("\nSearching with both filters...")
        results = vector_service.search(
            query="gym classes",
            top_k=5,
            filter_domain="example.com",
            filter_site="Example Site"
        )

        print("✓ Combined-filter search successful")
        print(f"  - Results: {len(results)}")

        return True
    except Exception as e:
        print(f"✗ Filtered search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_delete_by_domain():
    """Test deleting by domain."""
    print("\n" + "=" * 60)
    print("TEST 8: Delete by Domain")
    print("=" * 60)

    try:
        # First verify data exists
        results_before = vector_service.search("gym", top_k=10, filter_domain="example.com")
        print(f"  - Results before delete: {len(results_before)}")

        # Delete
        print("\nDeleting domain 'example.com'...")
        vector_service.delete_by_domain("example.com")

        print("✓ Delete successful")

        # Verify deletion
        results_after = vector_service.search("gym", top_k=10, filter_domain="example.com")
        print(f"  - Results after delete: {len(results_after)}")

        assert len(results_after) == 0, "Domain data should be deleted"
        print("  - ✓ Deletion verified (no results found)")

        return True
    except Exception as e:
        print(f"✗ Delete failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CHROMADB VECTOR SERVICE MIGRATION TESTS")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Initialization", test_initialization()))
    results.append(("Model Loading", test_model_loading()))
    results.append(("Collection Creation", test_collection_creation()))
    results.append(("Text Embedding", test_embedding()))
    results.append(("Markdown Chunking", test_chunking()))
    results.append(("Insert & Search", test_insert_and_search()))
    results.append(("Filtered Search", test_filtered_search()))
    results.append(("Delete by Domain", test_delete_by_domain()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
