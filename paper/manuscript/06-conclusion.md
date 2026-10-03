---
status: final
---

# 6. Conclusion

In this work, we investigated whether a lightweight local NLI cross-encoder (`cross-encoder/nli-deberta-v3-small`) running on consumer laptop CPU hardware can provide effective hallucination verification in healthcare Agentic RAG pipelines. Across both a 400-pair controlled benchmark evaluation (MedHallu) and a 200-pair real-world RAG evaluation with double-blind human ground truth (PubMedQA), the local cross-encoder achieved a zero False Negative Rate ($\text{FNR} = 0.0000$), successfully capturing 100% of hallucinations without letting an unsupported medical assertion pass undetected.

Verifier performance ranking proved stable across both synthetic and real settings (Filter B $\ge$ ROUGE-L), and benchmark-tuned decision thresholds transferred to real RAG with an $F_1$ penalty of only 0.0048. Operating at a median CPU latency of 332 ms and consuming less than 1 GB of memory, local NLI verification offers a viable, cost-free, and privacy-preserving alternative to cloud-based LLM judges.

We conclude that local NLI cross-encoders serve as an ideal, non-leaking front-line defense mechanism for clinical agentic architectures, providing reliable safety tripwires directly on hospital edge devices. Future work will explore multi-hop medical reasoning chains, multi-lingual clinical records, and calibrating dynamic escalation thresholds for hybrid human-in-the-loop workflows.
