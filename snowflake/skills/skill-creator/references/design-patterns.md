# Design Patterns, Testing, and Troubleshooting

Reference guide for advanced skill design. Load this file when planning skill architecture, testing triggering behavior, or diagnosing issues.

## Table of Contents
1. [Five Design Patterns](#five-design-patterns)
2. [Testing Approach](#testing-approach)
3. [Iteration Signals](#iteration-signals)
4. [Troubleshooting Guide](#troubleshooting-guide)
5. [Pre-Upload Checklist](#pre-upload-checklist)
6. [YAML Frontmatter Reference](#yaml-frontmatter-reference)

---

## Five Design Patterns

### Pattern 1: Sequential Workflow Orchestration

Multi-step processes executed in a specific order with explicit dependencies.

**When to use:** Tasks that must happen in sequence, where each step depends on the previous (e.g., data pipeline, deployment workflow, document generation).

**Key elements:**
- Number the steps explicitly
- State dependencies between steps ("After step 2 completes...")
- Add validation gates between critical phases
- Include rollback instructions for failure scenarios

**Example structure:**
```
1. Validate inputs → 2. Fetch data → 3. Transform → 4. Write output → 5. Verify
```

---

### Pattern 2: Multi-MCP Coordination

Workflows that span multiple services and tool connectors.

**When to use:** Tasks requiring data from multiple sources (e.g., Figma + GitHub + Linear, or Google Drive + Slack + Calendar).

**Key elements:**
- Clear phase separation (fetch → process → write)
- Explicit data-passing between MCPs ("Pass the result from Figma to Linear as...")
- Centralized error handling ("If any MCP call fails, report which service and what was attempted")
- Verify connectivity at start of workflow

---

### Pattern 3: Iterative Refinement

Output quality improves through repeated cycles.

**When to use:** Creative or generative tasks where quality emerges through iteration (e.g., design, writing, code review).

**Key elements:**
- Initial draft phase
- Explicit quality check criteria
- Refinement loop with specific stop criteria ("Stop when no substantial changes in 2 consecutive iterations")
- Finalization step

---

### Pattern 4: Context-Aware Tool Selection

Same outcome achieved via different tools based on context.

**When to use:** When the best approach depends on file size, type, user's environment, or collaboration needs.

**Key elements:**
- Decision tree at the start ("If file > 10MB use X, otherwise use Y")
- Fallback options for each tool
- Context detection instructions ("Check if MCP is available before assuming it is")

---

### Pattern 5: Domain-Specific Intelligence

Specialized knowledge applied beyond tool access alone.

**When to use:** Tasks where compliance, regulations, or deep domain expertise govern the process (e.g., security audits, legal document review, financial analysis).

**Key elements:**
- Domain knowledge in references/ files
- Pre-action compliance checks
- Expertise-driven decision points
- Comprehensive audit trail output

---

## Testing Approach

Test skills across three levels before distribution:

### Level 1: Triggering Tests

Verify the skill loads at appropriate times and does NOT load for unrelated queries.

**Test cases to write:**
- 5 paraphrased versions of the expected trigger query
- 5 queries where the skill should NOT trigger
- Edge cases (ambiguous queries)

**If skill doesn't trigger:** Revise description — add more specific trigger phrases users would actually type.

**If skill triggers too often:** Add negative trigger guidance to description ("Do NOT use for general X questions").

### Level 2: Functional Tests

Validate the skill produces correct outputs consistently.

**Check:**
- Correct outputs for typical inputs
- Successful MCP/API calls (if applicable)
- Proper error handling when inputs are missing or malformed
- Resource references load when needed

### Level 3: Performance Comparison

Prove improvement vs. baseline (no skill).

**Metrics to compare:**
- Number of tool calls to complete the task
- Number of messages required
- API failure rate (for MCP skills)
- User corrections needed

**Recommended process:** Iterate on a single challenging task until Claude succeeds consistently, then extract the successful approach into the skill.

---

## Iteration Signals

### Undertriggering (skill doesn't load when needed)
- **Symptom:** User has to explicitly say "use the X skill" every time
- **Fix:** Add more trigger phrases to description; include synonyms and alternate phrasings the user might naturally say

### Overtriggering (skill loads for irrelevant queries)
- **Symptom:** Skill activates on general questions it shouldn't handle
- **Fix:** Add negative triggers to description ("Do NOT use for..."); increase specificity of trigger conditions

### Execution Issues (inconsistent results)
- **Symptom:** Skill sometimes works, sometimes fails or produces wrong output
- **Fix:**
  - Add explicit error handling steps
  - Reduce freedom (move from high to medium/low freedom pattern)
  - Move repeated code to scripts/
  - Add validation checkpoints

### Context Overload (SKILL.md too long)
- **Symptom:** Skill is slow to load; Claude seems to miss instructions
- **Fix:** Move detailed content to references/ files; keep SKILL.md under 500 lines / 5,000 words

---

## Troubleshooting Guide

### Upload Failures

| Error | Fix |
|-------|-----|
| "Could not find SKILL.md" | File must be exactly `SKILL.md` (case-sensitive, no variations) |
| "Invalid frontmatter" | Check YAML formatting; ensure opening and closing `---` delimiters exist |
| "Invalid skill name" | Remove spaces and capitals; use kebab-case only (e.g., `my-skill`) |
| "Description too long" | Max 1,024 characters in description field |
| Frontmatter includes XML angle brackets | Remove all `<` and `>` from frontmatter; they are forbidden |

### Triggering Issues

| Symptom | Fix |
|---------|-----|
| Skill never loads | Revise description; add specific phrases users would actually say |
| Triggers too often | Add negative triggers; increase specificity |
| Users need explicit activation | Description lacks clarity about purpose and scope |

### MCP Connection Problems

1. Verify MCP server is connected in settings
2. Confirm API keys are valid and permissions are correct
3. Test MCP independently without the skill
4. Verify tool names match MCP documentation exactly (case-sensitive)

### Instruction Compliance Issues

- Reduce verbosity; use bullet points and numbered lists instead of paragraphs
- Place critical instructions at the top with `## Critical` headers
- Use explicit validation steps (script-based) rather than relying on Claude's judgment for fragile operations
- Add encouragement: "Quality is more important than speed"

---

## Pre-Upload Checklist

Before uploading a skill, verify all of the following:

**Planning**
- [ ] Identified 2–3 concrete use cases with trigger conditions and expected results
- [ ] Tools identified (built-in Claude tools or specific MCP servers)

**File Structure**
- [ ] Folder name is kebab-case (e.g., `my-skill`, not `MySkill` or `my skill`)
- [ ] Main file is exactly `SKILL.md` (case-sensitive)
- [ ] No extraneous files (README.md, INSTALLATION_GUIDE.md, CHANGELOG.md, etc.)

**Frontmatter**
- [ ] YAML block starts and ends with `---`
- [ ] `name` field present and in kebab-case
- [ ] `description` field present and complete
- [ ] Description includes BOTH what the skill does AND specific trigger phrases
- [ ] No XML angle brackets (`<`, `>`) in frontmatter
- [ ] Skill name does not contain "claude" or "anthropic"

**Instructions**
- [ ] Written in imperative/infinitive form
- [ ] Clear, actionable steps (not vague)
- [ ] Error handling included
- [ ] References to bundled resources clearly documented with when to load them
- [ ] SKILL.md is under 500 lines / 5,000 words

**Testing**
- [ ] Triggers on 5 paraphrased versions of the target query
- [ ] Does NOT trigger on 5 unrelated queries
- [ ] Functional tests pass for typical inputs
- [ ] Scripts tested by actually running them (not just reviewed)

---

## YAML Frontmatter Reference

### Required Fields

```yaml
---
name: skill-name-in-kebab-case
description: What it does and when to use it. Include specific trigger phrases.
---
```

### Full Reference (all optional fields)

```yaml
---
name: skill-name-in-kebab-case
description: >
  What it does and when to use it. Include specific trigger phrases users would
  actually say. Max 1,024 characters. No XML angle brackets.
license: MIT
allowed-tools: "Bash(python:*) Bash(npm:*) WebFetch"
metadata:
  author: Your Name or Org
  version: 1.0.0
  mcp-server: server-name
  category: productivity
  tags: [automation, workflow]
  documentation: https://example.com/docs
  support: support@example.com
---
```

### Field Notes

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Kebab-case; matches folder name; no "claude" or "anthropic" |
| `description` | Yes | Primary trigger mechanism; max 1,024 chars; no XML brackets |
| `license` | No | Use for open-source distribution (e.g., MIT, Apache-2.0) |
| `allowed-tools` | No | Restrict which tools the skill may use |
| `metadata` | No | Key-value pairs for author, version, category, tags, etc. |

**Security note:** Frontmatter is loaded into Claude's system prompt. Never include instructions, sensitive data, or XML angle brackets here.
