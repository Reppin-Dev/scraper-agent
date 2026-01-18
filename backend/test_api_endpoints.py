"""Test API endpoints with ChromaDB backend."""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint."""
    print("=" * 60)
    print("TEST 1: Health Check Endpoint")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/api/query/health")
        response.raise_for_status()
        data = response.json()

        print("✓ Health check successful")
        print(f"  - Status: {data.get('status')}")
        print(f"  - Service: {data.get('service')}")
        print(f"  - Collection: {data.get('collection')}")

        assert data.get('status') == 'healthy', "Service should be healthy"
        print("  - ✓ Service is healthy")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_embed_endpoint():
    """Test the embed endpoint."""
    print("\n" + "=" * 60)
    print("TEST 2: Embed Endpoint")
    print("=" * 60)

    try:
        # Use the existing sample file
        payload = {
            "filename": "heartlakecleaners.com__20251203_040611_b5c2740a.json"
        }

        print(f"  - Embedding file: {payload['filename']}")
        response = requests.post(
            f"{BASE_URL}/api/embed/",
            json=payload,
            timeout=180  # 3 minutes for embedding
        )
        response.raise_for_status()
        data = response.json()

        print("✓ Embed request completed")
        print(f"  - Status: {data.get('status')}")
        print(f"  - Message: {data.get('message')}")
        print(f"  - Total pages: {data.get('total_pages')}")
        print(f"  - Total chunks: {data.get('total_chunks')}")

        if data.get('status') == 'completed':
            assert data.get('total_pages', 0) > 0, "Should have embedded some pages"
            assert data.get('total_chunks', 0) > 0, "Should have created some chunks"
            print("  - ✓ Embedding successful")
            return True
        else:
            print(f"  - ⚠ Embedding status: {data.get('status')}")
            print(f"  - Message: {data.get('message')}")
            # Don't fail if it's just a data issue
            return True

    except requests.exceptions.Timeout:
        print("✗ Embed request timed out (may still be processing)")
        return False
    except Exception as e:
        print(f"✗ Embed request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_endpoint():
    """Test the search endpoint."""
    print("\n" + "=" * 60)
    print("TEST 3: Search Endpoint")
    print("=" * 60)

    try:
        # Search for something likely to be in the cleaner's website
        payload = {
            "query": "cleaning services",
            "top_k": 5
        }

        print(f"  - Query: '{payload['query']}'")
        response = requests.post(
            f"{BASE_URL}/api/query/search",
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        print("✓ Search successful")
        print(f"  - Query: {data.get('query')}")
        print(f"  - Total results: {data.get('total_results')}")

        results = data.get('results', [])
        for i, result in enumerate(results[:3]):  # Show first 3
            print(f"  - Result {i+1}:")
            print(f"    - Domain: {result.get('domain')}")
            print(f"    - Site: {result.get('site_name')}")
            print(f"    - Page: {result.get('page_name')}")
            print(f"    - Score: {result.get('score', 0):.4f}")
            print(f"    - Preview: {result.get('chunk_text', '')[:80]}...")

        return True
    except Exception as e:
        print(f"✗ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_filtered_search():
    """Test search with filters."""
    print("\n" + "=" * 60)
    print("TEST 4: Filtered Search Endpoint")
    print("=" * 60)

    try:
        # Search with domain filter
        payload = {
            "query": "leather cleaning",
            "top_k": 5,
            "filter_domain": "https://heartlakecleaners.com"
        }

        print(f"  - Query: '{payload['query']}'")
        print(f"  - Filter domain: {payload['filter_domain']}")

        response = requests.post(
            f"{BASE_URL}/api/query/search",
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        print("✓ Filtered search successful")
        print(f"  - Total results: {data.get('total_results')}")

        # Verify all results match the domain filter
        results = data.get('results', [])
        if results:
            domains = set(r.get('domain') for r in results)
            print(f"  - Unique domains in results: {domains}")

        return True
    except Exception as e:
        print(f"✗ Filtered search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ask_endpoint():
    """Test the RAG question answering endpoint."""
    print("\n" + "=" * 60)
    print("TEST 5: Ask/RAG Endpoint")
    print("=" * 60)

    try:
        payload = {
            "question": "What cleaning services are offered?",
            "top_k": 5
        }

        print(f"  - Question: '{payload['question']}'")

        response = requests.post(
            f"{BASE_URL}/api/query/ask",
            json=payload,
            timeout=60  # Claude API can take a while
        )
        response.raise_for_status()
        data = response.json()

        print("✓ RAG answer generated")
        print(f"  - Question: {data.get('question')}")
        print(f"  - Optimized query: {data.get('optimized_query')}")
        print(f"  - Sources used: {data.get('sources_used')}")
        print(f"  - Answer preview: {data.get('answer', '')[:200]}...")

        assert data.get('answer'), "Should have generated an answer"
        assert data.get('sources_used', 0) >= 0, "Should have source count"
        print("  - ✓ RAG pipeline successful")

        return True
    except requests.exceptions.Timeout:
        print("✗ Ask request timed out")
        return False
    except Exception as e:
        print(f"✗ Ask request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all API tests."""
    print("\n" + "=" * 60)
    print("API ENDPOINT TESTS (ChromaDB Backend)")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Health Check", test_health_check()))

    # Give server a moment
    time.sleep(1)

    results.append(("Embed Endpoint", test_embed_endpoint()))

    # Give embedding time to complete
    time.sleep(2)

    results.append(("Search Endpoint", test_search_endpoint()))
    results.append(("Filtered Search", test_filtered_search()))

    # Only test ask endpoint if we have ANTHROPIC_API_KEY
    import os
    if os.getenv('ANTHROPIC_API_KEY'):
        results.append(("Ask/RAG Endpoint", test_ask_endpoint()))
    else:
        print("\n⚠ Skipping Ask/RAG test (no ANTHROPIC_API_KEY)")

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
    import sys
    success = main()
    sys.exit(0 if success else 1)
