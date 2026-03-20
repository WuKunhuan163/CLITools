# ProcMEM: Procedural Memory for LLM Agents

**Paper**: ProcMEM: Learning Reusable Procedural Memory from Experience via Non-Parametric PPO for LLM Agents
**Authors**: Qirui Mi, Zhijian Ma, Mengyue Yang, Haoxuan Li, Yisen Wang, Haifeng Zhang, Jun Wang
**Venue**: ICML 2026
**Code**: https://github.com/Miracle1207/ProcMEM

## Core Idea

LLM agents typically rely on **episodic memory** — storing past interactions as "history books" to consult. Even with retrieved examples, the agent must re-derive solutions in its limited context window. ProcMEM introduces **procedural memory**: executable Skills that directly map situations to action sequences, bypassing re-derivation.

The analogy: episodic memory is like reading a recipe book every time you cook. Procedural memory is like knowing how to cook without looking — the skill is automatic.

## Skill Structure

A Skill is a tuple `<activation, execution, termination>`:

| Component | What it does | Representation |
|-----------|-------------|----------------|
| **Activation Condition** (I_omega) | When to invoke this skill | Natural language description of observable patterns |
| **Execution Procedure** (pi_omega) | Sequence of actions to perform | Ordered natural language steps |
| **Termination Condition** (beta_omega) | When to stop and return control | Natural language state predicate |

Example Skill from the paper:
```
Name: StrategicPlanning
Activation: When the task begins and no prior information or feedback is available.
Execution: 1. Establish initial hypothesis space. 2. Generate diverse exploratory action.
Termination: After first exploratory action is executed and feedback is observed.
```

## Skill-MDP

ProcMEM formalizes decision-making as a **Skill-augmented Markov Decision Process**:

```
M_Omega = (S, A, Omega, P, R, gamma)
```

- `S`: Semantic state space (natural language)
- `A`: Primitive action space
- `Omega`: Pool of available Skills (= procedural memory)
- The agent selects a Skill via `mu(omega | s_t, Omega)`, then executes primitive actions conditioned on the Skill

## Non-Parametric PPO

Skills are optimized **without updating LLM weights**:

1. **Semantic Gradients**: After collecting trajectories, extract what went wrong/right per-step (hindsight attribution). Use these as "gradients" to generate improved Skill candidates.

2. **PPO Gate**: Trust-region verification — only accept new Skills that improve performance within a bounded divergence from the original. Prevents catastrophic degradation.

3. **Score-based Maintenance**: Skills accumulate scores based on success/failure. Low-scoring skills are pruned to keep memory compact.

## Key Results

| Metric | ProcMEM | Best Baseline |
|--------|---------|---------------|
| Reuse Rate | 82% | 45% (episodic) |
| Memory Size | 12 skills | 500+ episodes |
| Cross-Task Transfer | Yes (skills generalize) | Limited |
| Cross-Agent Transfer | Yes (skills are portable) | No |

## Relevance to Our System

Our three-layer reflex arc system is an adaptation of ProcMEM's ideas:

| ProcMEM Concept | Our Implementation | Location |
|-----------------|-------------------|----------|
| Skill with activation/execution/termination | Blueprint procedural_skills | `openclaw-20260316/blueprint.json` |
| Skill pool (Omega) | Combination of blueprint + lessons + graph | `logic/brain/utils/procedural.py` |
| Activation matching | Regex patterns + keyword overlap | `match_skills()`, `match_lessons()` |
| Non-Parametric optimization | Lesson→Skill→Infrastructure pipeline | `AGENT_REFLECTION.md` Knowledge Creation |
| Score-based maintenance | Lesson severity + trigger frequency | `trigger_patterns` in lessons.jsonl |
| Cross-agent transfer | Blueprint portability + brain export | `BRAIN session export` |

### Key Differences

1. **We use static + dynamic skills**: ProcMEM learns all skills from experience. We pre-seed blueprint skills (static) AND learn from experience (dynamic lesson triggers).

2. **Graph-RAG layer**: ProcMEM's activation is purely similarity-based. Our graph adds multi-hop causal reasoning: action → system → file → documentation.

3. **Human-in-the-loop**: ProcMEM is fully autonomous. Our system maintains `USERINPUT` for human feedback, and `promotion_rules` require human review for skill→infrastructure transitions.

4. **Session-based vs. continuous**: ProcMEM runs continuously. Our system operates in discrete IDE sessions with brain persistence across them.

## Implications for Future Development

1. **Semantic Gradient extraction**: When an agent fails, extract what specifically went wrong and use it to refine the activation conditions of matching skills. Currently we record this as a lesson; future: auto-refine the blueprint skill's patterns.

2. **PPO Gate for lesson→skill promotion**: Before promoting a lesson to a skill (3+ occurrences), verify that the new skill doesn't degrade performance on other tasks. Currently this is human-reviewed; could be automated.

3. **Skill visualization**: ProcMEM visualizes skill evolution over time. Our brain Settings UI could show how skills accumulate and which are most frequently activated.
