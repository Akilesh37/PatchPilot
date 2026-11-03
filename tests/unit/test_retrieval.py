import pytest
from retrieval.search.retrieval_service import DocumentationRetrievalService, Citation

def test_retrieval_service_indexes_and_searches():
    service = DocumentationRetrievalService()
    assert len(service.chunks) > 0, "Should have indexed chunks from sources"

    # Search for javax.persistence
    citations = service.search("javax.persistence to jakarta.persistence", top_k=2)
    assert len(citations) > 0
    top_hit = citations[0]
    assert "jakarta" in top_hit.snippet.lower() or "persistence" in top_hit.snippet.lower()
    assert top_hit.canonical_url != ""
    assert top_hit.target_version != ""

    # Search for Security filter chain
    security_citations = service.search("WebSecurityConfigurerAdapter SecurityFilterChain", top_k=2)
    assert len(security_citations) > 0
    assert "SecurityFilterChain" in security_citations[0].snippet or "Security" in security_citations[0].doc_title

def test_hybrid_confidence_and_version_filtering():
    service = DocumentationRetrievalService()

    # Search Spring Boot 3 target
    sb3_hits = service.search("Jakarta persistence migration", top_k=3, target_version="3.2.0")
    assert len(sb3_hits) > 0
    for hit in sb3_hits:
        assert 0.0 <= hit.confidence <= 1.0
        assert "3." in hit.target_version or "Jakarta" in hit.target_version or "Security" in hit.target_version
        valid, msg = service.validate_citation(hit)
        assert valid, f"Citation should be valid: {msg}"

    # Search Spring Boot 2 baseline
    sb2_hits = service.search("Spring Boot 2.7 Java 8 baseline", top_k=2, target_version="2.7.18")
    assert len(sb2_hits) > 0
    for hit in sb2_hits:
        assert "2." in hit.target_version

def test_chunk_deduplication():
    service = DocumentationRetrievalService()
    chunk_hashes = [c.content_hash for c in service.chunks]
    # Verify no duplicate chunk hashes exist
    assert len(chunk_hashes) == len(set(chunk_hashes)), "All indexed chunks must be unique"
