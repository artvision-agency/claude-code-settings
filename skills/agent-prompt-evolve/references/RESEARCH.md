# Agent Self-Improvement Research (2026-03-07)

## Key Papers & Solutions

| Solution | What It Does | Relevance |
|----------|-------------|-----------|
| **Voyager** (NVIDIA, 2023) | Ever-growing skill library, skills indexed by embeddings | Pattern: compose complex from simple |
| **SAGE** (Dec 2025) | Skill Augmented GRPO, -59% tokens, +8.9% accuracy | Pattern: sequential skill chains |
| **SEAgent** | Curriculum learning for skill discovery, 11.3% -> 34.5% | Pattern: auto-discover capabilities |
| **4-Gate Governance** (Feb 2026 survey) | G1:static, G2:LLM, G3:sandbox, G4:permissions | Pattern: multi-source validation |
| **skills.sh** (Vercel) | npm for agent skills, 30+ agents | Infrastructure: already exists |
| **NIST AI Agent Standards** (Feb 2026) | Federal security standard for agents | Compliance: coming soon |

## Critical Finding: Phase Transition in Skill Libraries

Research shows unbounded skill accumulation DEGRADES performance past a critical size.
- Selection accuracy drops sharply
- Context window pollution
- Conflicting instructions

**Solution:** Aggressive curation. 20-30 well-crafted > 200 mediocre.

## 26% of Community Skills Have Vulnerabilities

Executable scripts are 2.12x more vulnerable than instruction-only.
Multi-source validation is NOT optional.

## Sources

- arxiv.org/html/2602.12430v3 — comprehensive survey
- voyager.minedojo.org — foundational research
- arxiv.org/abs/2512.17102 — SAGE
- github.com/anthropics/skills — official standard
- skills.sh — package manager
- yoheinakajima.com — practitioner perspective
