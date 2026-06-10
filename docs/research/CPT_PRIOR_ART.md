# CPT Prior Art

AOIA CPT does not claim to be the first prompt optimizer. Critique prompting, red-team prompting, LLM-as-judge, prompt optimization, structured prompt rewriting, and schema validation are known prior art.

AOIA CPT-A1 is an original deterministic implementation for AOIA's local-first epistemic-control workflow. It changes the rhetorical posture and review structure of a prompt; it does not verify facts, prove truth, perform security review by itself, authorize execution, or promote canonical knowledge. Human verification remains required.

No OpenAI internal code is used. No PromptWizard, SAMMO, DSPy, promptfoo, garak, DeepEval, LangSmith, Instructor, Outlines, Guidance, BAML, Guardrails, JSONformer, lm-format-enforcer, SGLang, or other third-party code is imported or copied into CPT-A1. Public prior art is used as conceptual inspiration only unless licenses are separately reviewed.

Prior-art categories reviewed:
- OpenAI prompt optimization, prompt engineering, structured outputs, graders/evals, red-teaming guidance, and OpenAI Cookbook examples.
- Microsoft PromptWizard and SAMMO.
- Stanford DSPy.
- promptfoo, NVIDIA garak, DeepEval / Confident AI, and LangSmith / LangChain LLM-as-judge workflows.
- Prompt Engineering Guide and adversarial prompting references.
- Open-source prompt optimizer projects such as `linshenkx/prompt-optimizer`.
- Structured-output and validation tools: Pydantic, Instructor, Outlines/dottxt, Guidance, BAML, Guardrails, NeMo Guardrails, JSONformer, lm-format-enforcer, and SGLang.

Implementation rule for CPT-A1: study only, cite honestly, implement original deterministic AOIA code, and keep provider/browser/shell paths out of scope.
