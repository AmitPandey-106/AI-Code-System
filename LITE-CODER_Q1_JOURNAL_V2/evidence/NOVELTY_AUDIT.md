# NOVELTY AUDIT

## 1. Architectural Novelty
- **Claimed:** "novel experience-based repair memory framework designed specifically for lightweight code LLMs"
- **Status:** Acceptable. The specific coupling of a 1.5B edge model with a localized CPU-bound FAISS+MiniLM index strictly gated by execution verification represents a specific, novel architectural arrangement.
- **Overreach check:** Did not claim to be the "first" to use RAG or the "only" memory system.

## 2. Methodological Novelty
- **Claimed:** Verification-gated memory admission to prevent contamination.
- **Status:** Requires literature review confirmation. Gating memory via unit tests is established in agentic SE (e.g., AutoGPT, Reflexion), but using sandboxed AST/contract validation specifically for edge-APR memory indices is a solid incremental methodological novelty.

## 3. Experimental Contribution
- **Claimed:** Isolating semantic memory retrieval from parameter adaptation (LoRA).
- **Status:** Strong. Directly comparing in-context RAG experience against LoRA weight updates on the exact same base model provides high-value empirical knowledge to the SE community.

## 4. Warnings and Revisions
- The manuscript must ensure it heavily cites Reflexion, Reprompting, and existing RAG-for-code works in the `03_background_related_work.tex` section to defend the "designed specifically for lightweight" novelty bound.
