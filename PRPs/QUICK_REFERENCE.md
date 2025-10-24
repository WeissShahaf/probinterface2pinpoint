# PRP Quick Reference

## Cheat Sheet

### Create Feature Spec
```bash
# 1. Copy template
cp features/example-feature.md features/my-feature.md

# 2. Fill in:
# - Problem statement
# - Requirements
# - Examples
# - Similar implementations
# - Success criteria
```

### Generate PRP
```bash
# In Claude Code
/generate-prp features/my-feature.md

# Output: PRPs/my-feature.md
```

### Review PRP
```bash
# Check confidence score (aim for 7+)
# - 9-10: Exceptional
# - 7-8: Good (ready to implement)
# - 5-6: Needs more context
# - <5: Insufficient, refine feature spec

# Look for:
# - Clear implementation tasks
# - Executable validation gates
# - References to codebase patterns
# - External documentation links
```

### Implement
```bash
# Follow PRP tasks in order:
# 1. Setup
# 2. Core implementation
# 3. Integration
# 4. Testing
# 5. Documentation
```

### Validate
```bash
# Execute validation gates from PRP:

# Syntax/Style
ruff check --fix .
mypy src/

# Tests
pytest tests/test_feature.py -v

# Integration
pytest tests/ -v

# End-to-end
python src/cli.py [command]
```

### Archive
```bash
# Successful implementation
mv PRPs/my-feature.md PRPs/completed/

# Failed implementation (with notes)
mv PRPs/my-feature.md PRPs/archive/failed/
# Add notes about why it failed
```

## Common Commands

### Research
```bash
# Find similar patterns
grep -r "pattern" src/

# Find similar tests
ls tests/test_*.py

# Check existing implementations
cat src/module/file.py
```

### Validation
```bash
# Quick syntax check
ruff check src/

# Type checking
mypy src/

# Run specific test
pytest tests/test_file.py::test_function -v

# Run all tests
pytest tests/ -v

# Check imports
python -c "from module import Feature; print('OK')"
```

### Git
```bash
# Commit feature spec
git add features/my-feature.md
git commit -m "Add feature spec for my-feature"

# Commit PRP
git add PRPs/my-feature.md
git commit -m "Add PRP for my-feature"

# Commit implementation
git add .
git commit -m "Implement my-feature

- Implemented X
- Added tests
- Updated docs

Closes #123"
```

## Feature Spec Template (Minimal)

```markdown
# Feature: Name

## Problem
What problem are we solving?

## Solution
High-level approach.

## Requirements
- [ ] REQ1: Description
- [ ] REQ2: Description

## Examples
Input:
```python
input_data = {...}
```

Output:
```python
output_data = {...}
```

## Similar Implementations
- `src/file.py` - Pattern to follow
- https://docs.example.com/api - External reference

## Success Criteria
- Metric 1
- Metric 2
```

## PRP Sections (Reference)

1. **Overview**: What, success criteria, files
2. **Research**: Codebase patterns, external resources, gotchas
3. **Blueprint**: Architecture, pseudocode, data structures
4. **Tasks**: Ordered checklist
5. **Validation**: Executable commands
6. **Context**: Critical info for AI agent
7. **Quality**: Checklist and confidence score

## Validation Gate Examples

### Good (Executable)
```bash
# Specific command with exact args
pytest tests/test_converter.py::test_format -v
ruff check src/formatters/ --fix
mypy src/formatters/pinpoint.py
python src/cli.py convert -i test.json -o output/
```

### Bad (Not Executable)
```bash
# Vague, non-specific
"Run tests"
"Check code"
"Verify output"
```

## Confidence Score Guide

| Score | Quality | Action |
|-------|---------|--------|
| 9-10 | Exceptional | Implement immediately |
| 7-8 | Good | Ready to implement |
| 5-6 | Moderate | Add more context, regenerate |
| 3-4 | Poor | Significant gaps, refine feature |
| 1-2 | Inadequate | Start over, add much more detail |

**Target**: 7+ before implementation

## Common Issues

### Low Confidence Score
- **Cause**: Missing context, unclear requirements
- **Fix**: Add more examples, research similar patterns, clarify requirements

### Implementation Fails
- **Cause**: PRP missing critical details
- **Fix**: Review failure points, add to feature spec, regenerate PRP

### Tests Fail
- **Cause**: Requirements unclear, edge cases missed
- **Fix**: Add edge cases to feature spec, update test strategy

### Integration Issues
- **Cause**: Integration points not documented
- **Fix**: Map all integration points, document in PRP

## Tips

- **Start with feature spec**: Don't skip this step
- **Research first**: Find similar patterns before planning
- **Be specific**: Vague requirements = failed implementation
- **Include examples**: Show input/output clearly
- **Make it executable**: All validation gates must be runnable
- **Score honestly**: Low scores catch problems early
- **Iterate**: Refine PRPs based on learnings

## Resources

- Full README: `PRPs/README.md`
- Feature template: `features/example-feature.md`
- PRP template: `PRPs/templates/prp_base.md`
- Project docs: `CLAUDE.md`
- Command: `.claude/commands/generate-prp.md`
