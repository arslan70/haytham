"""State divergence measurement for concept fidelity (ADR-022 Part 7e).

Measures semantic overlap between the original idea and outputs at different
pipeline stages using embedding similarity. Based on findings from Kim et al.
(2025) showing "only 34% overlap after 10 interactions" in agent world states.

Target: With the anchor pattern, Stage 10's semantic similarity to the original
idea should exceed 60% (vs. the research baseline of 34% without anchoring).
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SimilarityMeasurement:
    """Similarity measurement between original idea and a stage output."""

    stage: str
    similarity_score: float  # 0.0 to 1.0
    method: str  # e.g., "cosine", "bertscore", "jaccard"
    key_terms_preserved: list[str]
    key_terms_lost: list[str]


@dataclass
class DivergenceReport:
    """Full divergence report across pipeline stages."""

    original_idea: str
    anchor_present: bool
    measurements: list[SimilarityMeasurement]

    @property
    def final_similarity(self) -> float:
        """Get similarity score at the final stage."""
        if not self.measurements:
            return 0.0
        return self.measurements[-1].similarity_score

    @property
    def average_similarity(self) -> float:
        """Calculate average similarity across all stages."""
        if not self.measurements:
            return 0.0
        return sum(m.similarity_score for m in self.measurements) / len(self.measurements)

    @property
    def divergence_trend(self) -> str:
        """Classify the divergence trend."""
        if len(self.measurements) < 2:
            return "insufficient_data"

        first = self.measurements[0].similarity_score
        last = self.measurements[-1].similarity_score

        if last >= first * 0.9:
            return "stable"  # Less than 10% drop
        elif last >= first * 0.7:
            return "moderate_drift"  # 10-30% drop
        else:
            return "severe_drift"  # More than 30% drop

    @property
    def meets_target(self) -> bool:
        """Check if final similarity meets the 60% target."""
        return self.final_similarity >= 0.6

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "original_idea_hash": hashlib.md5(self.original_idea.encode()).hexdigest()[:8],
            "anchor_present": self.anchor_present,
            "final_similarity": self.final_similarity,
            "average_similarity": self.average_similarity,
            "divergence_trend": self.divergence_trend,
            "meets_target": self.meets_target,
            "target": 0.6,
            "baseline": 0.34,  # Research baseline without anchoring
            "measurements": [
                {
                    "stage": m.stage,
                    "similarity": m.similarity_score,
                    "method": m.method,
                    "terms_preserved": len(m.key_terms_preserved),
                    "terms_lost": len(m.key_terms_lost),
                }
                for m in self.measurements
            ],
        }


# =============================================================================
# Keyword-Based Similarity (Lightweight, No ML Dependencies)
# =============================================================================


def extract_key_terms(text: str, min_length: int = 4) -> set[str]:
    """Extract key terms from text for comparison.

    A simple keyword extraction that captures:
    - Multi-word phrases (noun phrases)
    - Important single words
    - Technical terms

    Args:
        text: Text to extract terms from
        min_length: Minimum word length to consider

    Returns:
        Set of key terms (lowercased)
    """
    import re

    # Normalize text
    text = text.lower()

    # Extract quoted phrases
    quoted = set(re.findall(r'"([^"]+)"', text))
    quoted.update(re.findall(r"'([^']+)'", text))

    # Extract words
    words = set(re.findall(r"\b[a-z][a-z-]+[a-z]\b", text))

    # Filter by length and remove common stop words
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "have",
        "will",
        "can",
        "are",
        "was",
        "were",
        "been",
        "being",
        "has",
        "had",
        "does",
        "did",
        "should",
        "would",
        "could",
        "their",
        "there",
        "these",
        "those",
        "they",
        "them",
        "what",
        "when",
        "where",
        "which",
        "while",
        "about",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
    }

    filtered_words = {w for w in words if len(w) >= min_length and w not in stop_words}

    return quoted | filtered_words


def calculate_jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    """Calculate Jaccard similarity between two sets.

    Args:
        set1: First set of terms
        set2: Second set of terms

    Returns:
        Jaccard similarity (0.0 to 1.0)
    """
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0


def measure_keyword_similarity(
    original: str,
    output: str,
    stage: str,
) -> SimilarityMeasurement:
    """Measure similarity using keyword overlap.

    This is a lightweight method that doesn't require ML models.
    For more accurate semantic similarity, use embedding-based methods.

    Args:
        original: Original idea text
        output: Stage output text
        stage: Stage name

    Returns:
        SimilarityMeasurement with jaccard similarity
    """
    original_terms = extract_key_terms(original)
    output_terms = extract_key_terms(output)

    similarity = calculate_jaccard_similarity(original_terms, output_terms)

    preserved = list(original_terms & output_terms)
    lost = list(original_terms - output_terms)

    return SimilarityMeasurement(
        stage=stage,
        similarity_score=similarity,
        method="jaccard_keywords",
        key_terms_preserved=preserved[:20],  # Limit to top 20
        key_terms_lost=lost[:20],
    )


# =============================================================================
# Embedding-Based Similarity (Requires sentence-transformers)
# =============================================================================


def measure_embedding_similarity(
    original: str,
    output: str,
    stage: str,
    model_name: str = "all-MiniLM-L6-v2",
) -> SimilarityMeasurement:
    """Measure similarity using sentence embeddings.

    Requires sentence-transformers library. Falls back to keyword
    similarity if not available.

    Args:
        original: Original idea text
        output: Stage output text
        stage: Stage name
        model_name: Sentence transformer model to use

    Returns:
        SimilarityMeasurement with cosine similarity
    """
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        logger.warning("sentence-transformers not installed, falling back to keyword similarity")
        return measure_keyword_similarity(original, output, stage)

    try:
        model = SentenceTransformer(model_name)

        # Encode texts
        original_embedding = model.encode(original, convert_to_tensor=True)
        output_embedding = model.encode(output[:5000], convert_to_tensor=True)  # Limit length

        # Calculate cosine similarity
        similarity = float(util.cos_sim(original_embedding, output_embedding)[0][0])

        # Also calculate keyword overlap for term tracking
        original_terms = extract_key_terms(original)
        output_terms = extract_key_terms(output)

        return SimilarityMeasurement(
            stage=stage,
            similarity_score=similarity,
            method=f"cosine_embedding_{model_name}",
            key_terms_preserved=list(original_terms & output_terms)[:20],
            key_terms_lost=list(original_terms - output_terms)[:20],
        )
    except Exception as e:
        logger.warning(f"Embedding similarity failed: {e}, falling back to keywords")
        return measure_keyword_similarity(original, output, stage)


# =============================================================================
# BERTScore-Based Contradiction Detection (ADR-022 Part 2c reference)
# =============================================================================


def detect_contradiction_bertscore(text1: str, text2: str, threshold: float = 0.3) -> bool:
    """Detect semantic contradiction using BERTScore.

    Based on Kim et al. (2025) finding that BERTScore < 0.3 correlates
    with contradiction/failure (2.3% contradictory tokens in successes
    vs. 8.1% in failures).

    Args:
        text1: First text
        text2: Second text
        threshold: BERTScore below this indicates contradiction

    Returns:
        True if texts appear contradictory
    """
    try:
        from bert_score import score
    except ImportError:
        logger.warning("bert-score not installed, cannot detect contradictions")
        return False

    try:
        # Calculate BERTScore
        P, R, F1 = score([text1], [text2], lang="en", verbose=False)
        bertscore = float(F1[0])

        return bertscore < threshold
    except Exception as e:
        logger.warning(f"BERTScore calculation failed: {e}")
        return False


# =============================================================================
# Full Pipeline Divergence Measurement
# =============================================================================


def measure_pipeline_divergence(
    original_idea: str,
    stage_outputs: dict[str, str],
    anchor_present: bool = False,
    use_embeddings: bool = False,
) -> DivergenceReport:
    """Measure semantic divergence across the full pipeline.

    Args:
        original_idea: The original startup idea
        stage_outputs: Dict mapping stage slug to output content
        anchor_present: Whether concept anchor was used
        use_embeddings: Whether to use embedding-based similarity (slower but more accurate)

    Returns:
        DivergenceReport with measurements for each stage
    """
    # Define stages to measure (key checkpoint stages)
    checkpoint_stages = [
        "idea-analysis",
        "validation-summary",
        "mvp-scope",
        "capability-model",
        "story-generation",
    ]

    measurements = []

    for stage in checkpoint_stages:
        output = stage_outputs.get(stage, "")
        if not output:
            continue

        if use_embeddings:
            measurement = measure_embedding_similarity(original_idea, output, stage)
        else:
            measurement = measure_keyword_similarity(original_idea, output, stage)

        measurements.append(measurement)

    return DivergenceReport(
        original_idea=original_idea,
        anchor_present=anchor_present,
        measurements=measurements,
    )


def compare_divergence_reports(
    with_anchor: DivergenceReport,
    without_anchor: DivergenceReport,
) -> dict[str, Any]:
    """Compare divergence reports with and without anchor pattern.

    Args:
        with_anchor: Report from pipeline with concept anchor
        without_anchor: Report from pipeline without anchor

    Returns:
        Comparison metrics
    """
    return {
        "with_anchor": {
            "final_similarity": with_anchor.final_similarity,
            "average_similarity": with_anchor.average_similarity,
            "trend": with_anchor.divergence_trend,
            "meets_target": with_anchor.meets_target,
        },
        "without_anchor": {
            "final_similarity": without_anchor.final_similarity,
            "average_similarity": without_anchor.average_similarity,
            "trend": without_anchor.divergence_trend,
        },
        "improvement": {
            "final_similarity_delta": with_anchor.final_similarity
            - without_anchor.final_similarity,
            "average_similarity_delta": with_anchor.average_similarity
            - without_anchor.average_similarity,
        },
        "research_context": {
            "baseline_overlap": 0.34,  # Kim et al. 2025: 34% after 10 interactions
            "target_overlap": 0.60,  # ADR-022 target
            "context_saturation_threshold": 0.39,  # Kim et al. 2025: c* = 0.39
        },
    }
