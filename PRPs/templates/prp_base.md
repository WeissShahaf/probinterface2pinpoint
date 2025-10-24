# PRP: [Feature Name]

**Status**: Draft | In Progress | Completed
**Created**: YYYY-MM-DD
**Priority**: Low | Medium | High | Critical
**Estimated Complexity**: 1-10

## Overview

### Feature Description
<!-- Brief 2-3 sentence description of what needs to be implemented -->

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

### Related Files
<!-- List files that will be created/modified -->
- `path/to/file1.py` - [Create/Modify] - Purpose
- `path/to/file2.py` - [Create/Modify] - Purpose

---

## Research Findings

### Codebase Patterns
<!-- Document existing patterns found in the codebase to follow -->

**Similar Implementations:**
- `file/path.py:line_number` - Description of pattern
- Key conventions identified:
  - Convention 1
  - Convention 2

**Testing Patterns:**
- Test structure: `tests/test_*.py`
- Test conventions:
  - Convention 1
  - Convention 2

### External Resources
<!-- Include URLs with specific sections that AI agent can reference -->

**Documentation:**
- [Library Name](https://docs.example.com/specific-section) - Section: Feature X
- [API Reference](https://api.example.com/endpoint) - Endpoint details

**Implementation Examples:**
- [GitHub Example](https://github.com/repo/file.py#L10-L50) - Pattern description
- [Blog Post](https://blog.example.com/post) - Key insight

**Best Practices:**
- Practice 1 with rationale
- Practice 2 with rationale

### Known Gotchas
<!-- Library quirks, version issues, common pitfalls -->
- Gotcha 1: Description and how to avoid
- Gotcha 2: Description and how to avoid

---

## Implementation Blueprint

### Architecture Overview
<!-- High-level description of how feature fits into existing architecture -->

```
Component A → Component B → Component C
     ↓              ↓             ↓
  Step 1        Step 2        Step 3
```

### Pseudocode/Approach

```python
# High-level pseudocode showing implementation approach
class FeatureName:
    def __init__(self):
        # Initialize with references to existing patterns
        pass

    def main_method(self):
        # Step 1: Description
        # Reference: existing_file.py:line_number

        # Step 2: Description
        # Reference: pattern from docs_url

        # Step 3: Description
        pass
```

### Data Structures
<!-- Key data structures and their schemas -->

```python
# Input format
input_data = {
    "field1": "type - description",
    "field2": "type - description"
}

# Output format
output_data = {
    "field1": "type - description",
    "field2": "type - description"
}
```

### Error Handling Strategy
<!-- How errors should be handled -->
- Error type 1: Handling approach
- Error type 2: Handling approach
- Logging pattern: Reference to existing logger usage

---

## Implementation Tasks

### Task List (in order of execution)
1. **Setup/Preparation**
   - [ ] Task 1.1 - Description
   - [ ] Task 1.2 - Description

2. **Core Implementation**
   - [ ] Task 2.1 - Description
   - [ ] Task 2.2 - Description
   - [ ] Task 2.3 - Description

3. **Integration**
   - [ ] Task 3.1 - Description
   - [ ] Task 3.2 - Description

4. **Testing**
   - [ ] Task 4.1 - Unit tests
   - [ ] Task 4.2 - Integration tests
   - [ ] Task 4.3 - Validation tests

5. **Documentation**
   - [ ] Task 5.1 - Code documentation
   - [ ] Task 5.2 - Update CLAUDE.md if needed
   - [ ] Task 5.3 - Usage examples

---

## Validation Gates

### Pre-Implementation Checks
```bash
# Verify environment is ready
python --version
pip list | grep -E "package1|package2"
```

### During Implementation
```bash
# Syntax/Style validation (execute after each major change)
ruff check --fix .
mypy src/

# Quick smoke test
python -c "from module import Feature; print('Import OK')"
```

### Post-Implementation Validation
```bash
# Unit tests (must pass 100%)
pytest tests/test_feature.py -v

# Integration tests
pytest tests/ -v -k "integration"

# End-to-end validation
python src/cli.py [command] [args]

# Code quality
ruff check . && mypy src/
```

### Success Metrics
- [ ] All tests passing
- [ ] No type errors
- [ ] Code coverage > X%
- [ ] Performance benchmark met (if applicable)
- [ ] Documentation complete

---

## Context for AI Agent

### Critical Information
<!-- Essential context that AI agent needs to succeed -->

**Coordinate Systems:**
- Input: [Description]
- Output: [Description]
- Transform: Reference to `file.py:line`

**Dependencies:**
- Library1 version X.Y - Used for Z
- Library2 version X.Y - Used for Z

**Integration Points:**
- Integrates with: `module.py:ClassName`
- Called by: `another_module.py:function_name`
- Calls: `dependency.py:function_name`

### Example Usage
```python
# Show how the feature will be used
from module import Feature

feature = Feature(param1, param2)
result = feature.process()
```

### Test Examples
```python
# Show test pattern to follow
def test_feature_basic():
    # Arrange
    input_data = {...}

    # Act
    result = process(input_data)

    # Assert
    assert result["field"] == expected_value
```

---

## Quality Checklist

Before marking PRP as complete, verify:

- [ ] All necessary context included (docs, examples, patterns)
- [ ] Validation gates are executable commands
- [ ] References to existing codebase patterns with file:line
- [ ] Clear implementation path with ordered tasks
- [ ] Error handling documented
- [ ] Data structures clearly defined
- [ ] Integration points identified
- [ ] Test strategy defined
- [ ] Success criteria measurable

---

## Confidence Score

**Score**: X/10

**Rationale**:
- Strengths: What makes this PRP strong
- Risks: What could cause issues
- Mitigations: How risks are addressed

**Estimated Time**: X hours/days

---

## Notes

### Assumptions
- Assumption 1
- Assumption 2

### Open Questions
- Question 1 (if needs user clarification)
- Question 2

### Future Enhancements
- Enhancement 1 (out of scope for this PRP)
- Enhancement 2
