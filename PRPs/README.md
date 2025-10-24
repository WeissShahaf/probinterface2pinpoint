# PRP (Project Requirements & Planning) System

## Overview

The PRP system provides a structured approach to feature implementation using AI agents. By creating comprehensive, context-rich PRPs, we enable **one-pass implementation success** with minimal iterations.

**PRP** = Detailed implementation plan with all necessary context for an AI agent to implement a feature autonomously.

## Directory Structure

```
PRPs/
  ├── README.md                        # This file
  ├── templates/
  │   └── prp_base.md                  # Base template for new PRPs
  ├── {feature-name}.md                # Generated PRPs
  └── completed/
      └── {feature-name}.md            # Completed PRPs (archive)

features/
  ├── example-feature.md               # Example feature specification
  ├── pinpoint-multifile-format.md     # Real feature spec
  └── {new-feature}.md                 # Add new feature specs here
```

## Workflow

### 1. Create Feature Specification

Create a feature file in `features/` directory describing WHAT needs to be built:

```bash
# Copy example template
cp features/example-feature.md features/my-new-feature.md

# Edit with your requirements
# - Problem statement
# - Requirements
# - Examples
# - Similar implementations
# - Success criteria
```

**Key sections:**
- **Problem Statement**: What problem does this solve?
- **Requirements**: Functional and non-functional requirements
- **Examples**: Input/output examples, use cases
- **Similar Implementations**: Internal code patterns and external references
- **Success Metrics**: How to measure success

### 2. Generate PRP

Use the `/generate-prp` command to create a comprehensive PRP from the feature file:

```bash
# In Claude Code CLI
/generate-prp features/my-new-feature.md
```

This command will:
1. **Research**: Search codebase for similar patterns
2. **Explore**: Identify relevant files and conventions
3. **Analyze**: Review external documentation and examples
4. **Plan**: Create detailed implementation blueprint
5. **Generate**: Output complete PRP in `PRPs/my-new-feature.md`

The AI agent will:
- Search for similar features in the codebase
- Identify existing patterns to follow
- Research external libraries and documentation
- Create pseudocode and implementation plan
- Define validation gates (executable tests)
- Score confidence level (1-10)

### 3. Review and Refine

Review the generated PRP:

```bash
# Check the PRP
cat PRPs/my-new-feature.md

# Look for:
# - Confidence score (aim for 7+)
# - Clear implementation path
# - Executable validation gates
# - Sufficient context
```

If confidence score is low (<7):
- Add more context to feature file
- Clarify requirements
- Add more examples
- Regenerate PRP

### 4. Implement Feature

Pass the PRP to an AI agent for implementation:

```bash
# Option 1: Use Claude Code Task agent
# The agent reads the PRP and implements autonomously

# Option 2: Manual implementation
# Follow the PRP step-by-step
```

### 5. Validate

Execute validation gates from PRP:

```bash
# Syntax/Style
ruff check --fix .
mypy src/

# Unit Tests
pytest tests/test_feature.py -v

# Integration Tests
pytest tests/ -v

# End-to-end
python src/cli.py [command] [expected-output]
```

### 6. Archive

Move completed PRP to archive:

```bash
# After successful implementation
mv PRPs/my-feature.md PRPs/completed/
```

## PRP Template Structure

Each PRP follows this structure:

### 1. Overview
- Feature description
- Success criteria
- Related files

### 2. Research Findings
- **Codebase Patterns**: Similar implementations to reference
- **External Resources**: Documentation, examples, best practices
- **Known Gotchas**: Common pitfalls and how to avoid them

### 3. Implementation Blueprint
- **Architecture Overview**: How feature fits into system
- **Pseudocode**: Step-by-step approach
- **Data Structures**: Input/output formats
- **Error Handling**: Strategy for errors

### 4. Implementation Tasks
- Ordered checklist of tasks
- Broken down into: Setup → Core → Integration → Testing → Documentation

### 5. Validation Gates
- **Pre-Implementation**: Environment checks
- **During Implementation**: Syntax, style, smoke tests
- **Post-Implementation**: Full test suite, quality checks
- **Success Metrics**: Measurable outcomes

### 6. Context for AI Agent
- Critical information for autonomous implementation
- Integration points
- Usage examples
- Test patterns

### 7. Quality Checklist
- Verification that PRP is complete
- Confidence score with rationale

## Best Practices

### Writing Feature Specifications

✅ **DO:**
- Provide clear problem statement
- Include concrete examples (input/output)
- Reference similar implementations (internal and external)
- Specify success criteria
- List constraints and risks

❌ **DON'T:**
- Be vague about requirements
- Skip examples
- Ignore existing patterns
- Forget edge cases

### Writing PRPs

✅ **DO:**
- Include executable validation gates
- Reference specific files with line numbers
- Provide URLs to documentation (specific sections)
- Include pseudocode for complex logic
- Score confidence honestly
- Pass all necessary context to AI agent

❌ **DON'T:**
- Assume AI agent has context beyond what's in PRP
- Skip research phase
- Make validation gates non-executable
- Omit error handling strategy

### Validation Gates

Validation gates MUST be executable commands:

```bash
# ✅ GOOD - Specific, executable
pytest tests/test_feature.py::test_basic_case -v
ruff check src/formatters/ --fix
mypy src/formatters/pinpoint.py

# ❌ BAD - Vague, non-executable
"Run tests"
"Check code quality"
"Verify output"
```

## Confidence Scoring

Rate PRPs on a scale of 1-10:

- **9-10**: Exceptional - All context, clear path, minimal risk
- **7-8**: Good - Sufficient context, clear path, some unknowns
- **5-6**: Moderate - Missing some context, may need iteration
- **3-4**: Poor - Significant gaps, high risk of failure
- **1-2**: Inadequate - Insufficient context, likely to fail

**Target**: Aim for 7+ before implementation.

**If score < 7**: Refine feature spec, add more research, regenerate PRP.

## Example Usage

### Example: Implementing Pinpoint Multi-File Format

1. **Feature Specification** (already exists):
   ```bash
   cat features/pinpoint-multifile-format.md
   # Shows: Problem, requirements, examples, references
   ```

2. **Generate PRP**:
   ```bash
   /generate-prp features/pinpoint-multifile-format.md
   # AI researches codebase, external docs, generates PRP
   ```

3. **Review PRP**:
   ```bash
   cat PRPs/pinpoint-multifile-format.md
   # Check confidence score, implementation plan
   ```

4. **Implement**:
   ```bash
   # Pass to AI agent or implement manually following PRP
   ```

5. **Validate**:
   ```bash
   # Execute validation gates from PRP
   pytest tests/test_pinpoint_formatter.py -v
   ruff check . && mypy src/
   python src/cli.py convert -i test.json -o output/
   ```

## FAQ

**Q: When should I create a feature spec vs just implement?**
A: Create feature specs for:
- Complex features requiring planning
- Features affecting multiple files
- Features needing research
- Features you want AI to implement autonomously

**Q: How detailed should feature specs be?**
A: Detailed enough to answer:
- What problem are we solving?
- What should the output look like?
- Are there similar implementations to reference?
- How will we know it's successful?

**Q: What if the AI agent fails to implement?**
A:
1. Check confidence score (if <7, refine PRP)
2. Add more context to feature spec
3. Add more examples
4. Regenerate PRP and retry

**Q: Can I modify a generated PRP?**
A: Yes! PRPs are starting points. Refine them based on:
- New research findings
- Implementation learnings
- Changed requirements

**Q: Should I archive failed PRPs?**
A: Yes, to `PRPs/archive/failed/` with notes on why it failed and what to improve.

## References

- `/generate-prp` command: `.claude/commands/generate-prp.md`
- Feature template: `features/example-feature.md`
- PRP template: `PRPs/templates/prp_base.md`
- Project architecture: `CLAUDE.md`

## Contributing

When adding new features:
1. Create feature spec in `features/`
2. Generate PRP using `/generate-prp`
3. Review and refine
4. Implement following PRP
5. Archive completed PRP
6. Update this README if workflow changes

---

**Goal**: Enable one-pass implementation success through comprehensive PRPs with all necessary context for AI agents.
