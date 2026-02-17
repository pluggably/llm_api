# Agent Development Workflow

## Overview
This document defines the standard workflow for system and software development following the V-model in an agile manner. All AI agents working on this project must follow these rules and procedures.

## Operating Rules (Global)

### Change Control (Post-Approval)
- Once Phase 4 approval is granted, requirements and designs are treated as *baselined*.
- Any change request must be handled as a mini V-cycle:
  1. Identify which artifacts are actually impacted (not all changes affect all levels)
  2. Update only the impacted requirements, architecture, designs, and interface contracts
  3. Update impacted test specifications and test stubs
  4. Re-run the Phase 4 review for the impacted scope only
- No implementation work for changed scope begins until re-approval is granted.
- **Scope-appropriate updates**: If a change only affects implementation details, do not force updates to stakeholder or system requirements that remain valid.

### Definition of Ready (DoR) / Definition of Done (DoD)
- Each phase deliverable must include a short checklist stating it is Ready/Done.
- Use objective criteria (IDs present, traceability filled, diagrams render, tests linked).

### Interface Contracts (In Addition to Diagrams)
- Every interface shown in architecture diagrams must have a contract artifact or a stub:
  - HTTP APIs: OpenAPI (preferred) or a Markdown contract specifying endpoints, schemas, errors
  - Events/Messaging: AsyncAPI or a Markdown contract specifying topics, payload schemas
  - Data models: JSON Schema (preferred) or a Markdown schema table
- Contracts must specify: authentication/authorization, request/response shapes, error modes, timeouts/retries, idempotency (if applicable), and versioning.

### Non-Functional Requirements (NFR) Coverage
- Explicitly capture NFRs for: security/privacy, reliability (timeouts/retries), observability (logs/metrics/traces), performance budgets/limits, usability, and maintainability.

### Decision Log (ADRs)
- Create short Architecture Decision Records for any major decision (tech choice, persistence, messaging pattern, authentication strategy, interface versioning).
- Location: `docs/adr/` (one Markdown file per ADR).

### Risks & Threats (Lightweight)
- For each project or major feature, list top risks (delivery/tech/ops) and mitigations.
- For systems handling external input or secrets, include a lightweight threat assessment (e.g., STRIDE bullets) and mitigations.

### Bug Fix Process
When a user reports a bug or issue, follow this process:

1. **Triage & Root Cause Analysis**
   - Investigate the issue to understand the root cause
   - Document findings: what is broken, why, and what components are affected
   - Classify the fix scope:
     - **Trivial**: Typo, config error, single-line fix with no design impact → May proceed directly with user acknowledgment
     - **Localized**: Bug in implementation that doesn't change interfaces or design → Propose fix, get approval, implement
     - **Architectural**: Requires changes to interfaces, data models, or design → Full change management (see below)

2. **Change Proposal (for Localized and Architectural fixes)**
   - Document the proposed change:
     - **Problem**: What is broken and the root cause
     - **Proposed Solution**: High-level description of the fix
     - **Impact Assessment**: Which components, interfaces, or designs are affected
     - **Alternatives Considered**: Other approaches and why they were rejected (if applicable)
   - Present to user for review before any implementation

3. **Approval Gate**
   - **STOP and WAIT** for explicit user approval before implementing
   - User may request changes or ask clarifying questions
   - Only proceed after `APPROVED` is received

4. **Implementation & Verification**
   - Update affected documentation (interfaces, designs, tests) as needed
   - Implement the fix
   - Run relevant tests
   - Present summary for Phase 6.5 Pre-Push Review

### Incremental Change Guidance
- **Not all changes require updating all documentation levels.**
- If stakeholder requirements are stable, do not force updates to them.
- If system requirements are stable, do not force updates to them.
- Update only the artifacts that are actually impacted:
  - Interface change → Update interface contracts and affected designs
  - Implementation bug → May only need code fix and test updates
  - New capability → May require new software requirements and design, but not necessarily new stakeholder/system requirements
- Always maintain traceability for changed items.

## Workflow Phases

### Phase 1: Requirements Analysis

**Goal of Phase 1**: Convert imperfect/ambiguous user input into clear, testable stakeholder and system requirements.

**Intent-first rule**
- Treat the user’s message as *starting context*, not a spec.
- First infer the underlying objective (“what outcome are we optimizing for?”), then propose a structured set of requirements.
- If the input is ambiguous, ask targeted clarifying questions *and* provide a best-effort draft using clearly labeled assumptions.

#### 1.1 Stakeholder Requirements
- **Input**: User's natural language description of needs
- **Output**: `docs/requirements/stakeholder_requirements.md`
- **Content**: Convert user input into clear stakeholder requirements with:
  - Business objectives
  - User needs
  - High-level functional requirements
  - Non-functional requirements (performance, security, usability, etc.)
  - Constraints and assumptions

**Elicitation & completeness checklist (required in the doc)**
- **Problem statement**: What problem is being solved and why now?
- **Stakeholders/personas**: Who uses/operates it, and who is impacted?
- **Success criteria**: What measurable outcomes define success (e.g., time saved, error rate, latency, cost)?
- **In-scope / out-of-scope**: Explicit non-goals to prevent scope creep.
- **Constraints**: Budget, timeline, tech, compliance, deployment environment.
- **Key workflows**: 3–5 primary user journeys.
- **Edge cases**: High-risk/likely failure scenarios.
- **Open questions**: A section listing unanswered questions.

**Quality bar**
- Stakeholder requirements should be outcome-oriented, unambiguous, and testable where possible (SMART-ish).
- When requirements are uncertain, capture multiple viable options and trade-offs, and mark decisions needed.

#### 1.2 System Requirements
- **Input**: Stakeholder requirements
- **Output**: `docs/requirements/system_requirements.md`
- **Content**: Decompose stakeholder requirements into:
  - Detailed functional requirements (numbered/traceable)
  - System-level non-functional requirements
  - External interface requirements
  - Data requirements
  - System constraints

**Decomposition guidance**
- Each system requirement must:
  - have a unique `SYS-REQ-###` ID
  - be testable (trace forward to `TEST-*`)
  - specify success criteria/thresholds where relevant (e.g., latency p95, throughput, RTO/RPO)
  - define error modes for externally visible behaviors
- Include a short **Assumptions** section; assumptions must be validated or turned into requirements before approval.
- Include an **Out of Scope** section aligned to stakeholder non-goals.

#### 1.3 System Architecture
- **Input**: System requirements
- **Output**: `docs/architecture/system_architecture.md`
- **Content**: Define the system-level architecture including:
  - System context diagram (Mermaid)
  - System decomposition into major elements/subsystems
  - System element diagrams (Mermaid)
  - Interface definitions between system elements
  - Data flow diagrams (Mermaid)
  - Technology stack decisions
  - Rationale for architectural decisions

### Phase 2: Software Design

#### 2.1 Software Requirements
- **Input**: System requirements and architecture
- **Output**: `docs/requirements/software_requirements_[software_name].md` (one per software component)
- **Content**: For each software component:
  - User stories following format: "As a [role], I want [capability] so that [benefit]"
  - Acceptance criteria for each user story
  - Story points/complexity estimates
  - Dependencies between stories
  - Traceability matrix to system requirements

#### 2.2 Software Architecture
- **Input**: Software requirements
- **Output**: `docs/architecture/software_architecture_[software_name].md` (one per software component)
- **Content**: For each software component:
  - High-level component diagram (Mermaid)
  - Module/package structure
  - Block diagrams showing software blocks (Mermaid)
  - Interface definitions between blocks (APIs, protocols, data structures)
  - Sequence diagrams for key interactions (Mermaid)
  - Technology and framework choices
  - Design patterns to be used

#### 2.3 Detailed Design
- **Input**: Software architecture
- **Output**: `docs/design/detailed_design_[component_name].md` (one per major component)
- **Content**: For each component:
  - Component responsibilities
  - Class diagrams or module structures (Mermaid)
  - Flowcharts for algorithms and logic (Mermaid)
  - State diagrams where applicable (Mermaid)
  - Data structures and schemas
  - Error handling strategies
  - Pseudo-code for complex logic

### Phase 3: Test Planning

#### 3.1 Test Specifications
- **Input**: All requirements, architecture, and design documents
- **Output**: `docs/testing/test_specifications.md`
- **Content**: Human-readable test specifications covering:
  - **System Test Specifications**: How to verify system requirements
  - **Integration Test Specifications**: How to verify interfaces between components
  - **Unit Test Specifications**: How to verify individual components/functions
  - Test approach and strategy
  - Test environment requirements
  - Test data requirements
  - Traceability to requirements

#### 3.2 Automated Test Cases
- **Input**: Test specifications
- **Output**: `tests/test_[feature].py` (or appropriate test files)
- **Content**: Automated test cases including:
  - Unit tests for all functions/methods
  - Integration tests for component interactions
  - System tests for end-to-end scenarios
  - Test stubs/skeletons for tests that cannot run yet (marked with `@pytest.skip` or similar)
  - Every skipped/stubbed test must include: the reason, what unblocks it, and the expected verification method
  - Test fixtures and mocks as needed
  - Clear test naming following conventions

#### 3.3 Manual Test Procedures
- **Input**: Test specifications
- **Output**: `docs/testing/manual_test_procedures.md`
- **Content**: For anything that cannot be automated:
  - Step-by-step manual test procedures
  - Expected results
  - Test data to use
  - Screenshots or examples where helpful
  - Traceability to requirements

### Phase 4: Review and Approval Gate

#### 4.1 Document Review
Before any code is written, present all documentation for review:
1. Stakeholder requirements
2. System requirements and architecture
3. Software requirements (user stories)
4. Software architecture
5. Detailed design
6. Test specifications
7. Test case outlines

#### 4.2 Approval Process
- Present a summary of all work completed
- Highlight key decisions and trade-offs
- Request explicit approval from the user
- **STOP and WAIT for user approval before proceeding to Phase 5**
- Address any feedback or concerns
- Update documentation based on feedback

**Approval Protocol (Explicit)**
- The user approval must be recorded in the conversation using one of:
  - `APPROVED: <scope>`
  - `CHANGES REQUESTED: <bulleted list>`
- If scope is partial, only approved components may proceed to implementation.

### Phase 5: Implementation

#### 5.1 Code Development
- **Input**: Approved design documents and test specifications
- **Output**: Source code files
- **Process**:
  1. Implement all components according to detailed design
  2. Follow coding standards and best practices
  3. Include inline documentation and docstrings
  4. Implement error handling as specified
  5. Ensure code is modular and testable

#### 5.2 Test Implementation
- **Input**: Test case stubs and test specifications
- **Output**: Fully implemented automated tests
- **Process**:
  1. Complete all test case implementations
  2. Remove skip decorators from tests
  3. Ensure tests are independent and repeatable
  4. Verify test coverage

### Phase 6: Verification and Validation

#### 6.1 Test Execution
- **Process**:
  1. Run all automated unit tests
  2. Run all automated integration tests
  3. Run all automated system tests
  4. Document test results

#### 6.1.5 Code Quality Gate
- **Process**:
  1. Run static type checker (Pylance/Pyright) and resolve all errors
  2. Address warnings that indicate real bugs or type safety issues
  3. Suppressions (# type: ignore) are acceptable only with justification comment
  4. **All Pylance errors must be resolved before proceeding to Phase 6.5**

#### 6.2 Bug Fixing Cycle
- **Process**:
  1. Analyze test failures
  2. Fix bugs in code
  3. Re-run affected tests
  4. Repeat until all automated tests pass
  5. Do NOT modify tests to pass unless they are incorrectly written

#### 6.3 Manual Testing
- **Process**:
  1. Once automated tests pass, provide manual test procedures
  2. User executes manual tests
  3. Address any issues found
  4. Re-test as needed

#### 6.4 User Story Completion
- **Process**:
  1. Once all tests pass for a user story, mark it as complete
  2. Update `docs/requirements/software_requirements_[software_name].md` with status
  3. Update any tracking documents

### Phase 6.5: Pre-Push Review Checkpoint
- **Process**:
  1. Prepare a concise change summary (files touched + key behavior changes)
  2. Provide test results and any skipped tests
  3. Request explicit user approval to push commits
  4. **Do not push to git until approval is granted**

## Documentation Standards

### File Organization
```
docs/
├── requirements/
│   ├── stakeholder_requirements.md
│   ├── system_requirements.md
│   └── software_requirements_[name].md
├── architecture/
│   ├── system_architecture.md
│   └── software_architecture_[name].md
├── design/
│   └── detailed_design_[component].md
└── testing/
    ├── test_specifications.md
    └── manual_test_procedures.md

tests/
├── unit/
├── integration/
└── system/

src/
└── [implementation files]
```

### Mermaid Diagram Standards
- **System Context**: Use C4 context diagrams or simple block diagrams
- **System Architecture**: Use component diagrams
- **Software Architecture**: Use component/package diagrams
- **Interfaces**: Use sequence diagrams or communication diagrams
- **Detailed Design**: Use flowcharts, class diagrams, state diagrams
- All diagrams must be embedded in Markdown using mermaid code blocks

### Release & Operations (Minimum Expectations)
- Define how to run locally, how to configure, and how to run tests (README is acceptable).
- Document runtime configuration (env vars), secrets handling, and logging.
- Prefer reproducible commands for build/test/lint and a clear CI entrypoint if applicable.

### Requirements Traceability
- Each requirement must have a unique ID
- Format: `SH-REQ-###` (Stakeholder), `SYS-REQ-###` (System), `SW-REQ-###` (Software)
- Maintain traceability matrices linking:
  - Stakeholder → System requirements
  - System → Software requirements
  - Requirements → Tests

#### Traceability Matrix (Required)
- Every requirements and testing document must include a **Traceability** section.
- The traceability matrix must be updated **in the same change** whenever requirements, architecture/interfaces, design, or tests are added/removed/renumbered.
- A requirement is not “Done” unless it traces forward to at least one verification item (automated test or manual procedure).

**Recommended Test ID format**: `TEST-UNIT-###`, `TEST-INT-###`, `TEST-SYS-###`, `TEST-MAN-###`

**Matrix template (use one or more tables as needed):**

Stakeholder → System

| Stakeholder Req ID | System Req ID(s) | Notes |
|---|---|---|
| SH-REQ-001 | SYS-REQ-001, SYS-REQ-002 | |

System → Software (per software component)

| System Req ID | Software Component | User Story ID(s) | Notes |
|---|---|---|---|
| SYS-REQ-001 | <name> | US-001, US-002 | |

Requirements → Verification

| Requirement ID | Verification Type | Test/Procedure ID | Location | Notes |
|---|---|---|---|---|
| SYS-REQ-001 | Automated | TEST-SYS-001 | tests/system/test_feature.py | |
| SYS-REQ-002 | Manual | TEST-MAN-001 | docs/testing/manual_test_procedures.md | |

### User Story Format
```markdown
**Story ID**: US-###
**Title**: [Brief title]
**Priority**: High/Medium/Low
**Story Points**: [Estimate]

As a [role]
I want [capability]
So that [benefit]

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Traceability**: SYS-REQ-###, SYS-REQ-###

**Status**: Not Started / In Progress / In Review / Testing / Complete
```

## Agent Responsibilities

### When Starting New Work
1. Review this agents.md file
2. Identify current phase in workflow
3. Ensure all prerequisite phases are complete
4. Follow the workflow sequentially

### When Creating Documentation
1. Follow the file organization structure
2. Use appropriate templates and formats
3. Include all required mermaid diagrams
4. Maintain traceability links
5. Write clearly and concisely for human readers

### When Writing Tests
1. Prioritize automated tests over manual tests
2. Use stubs/skip decorators for tests that can't run yet
3. Write independent, repeatable tests
4. Follow naming conventions: `test_[feature]_[scenario]_[expected_result]`
5. Include both positive and negative test cases

### When Writing Code
1. Only write code after approval gate
2. Implement according to detailed design
3. Write clean, documented, maintainable code
4. Handle errors as specified
5. Make code testable

### When Testing
1. Run all tests systematically
2. Fix bugs, don't modify tests (unless tests are wrong)
3. Cycle between testing and fixing until all pass
4. Document any issues that require manual testing

## Key Principles

### V-Model Adherence
- Left side of V (requirements → design): Complete thoroughly before implementation
- Bottom of V (implementation): Guided by design
- Right side of V (testing → validation): Mirrors left side with appropriate tests for each level

### Agile Integration
- Use user stories for software requirements
- Allow iterative refinement within phases
- Maintain working increments
- Respond to feedback during review gates

### Quality Gates
- **Gate 1**: Complete all documentation before approval gate
- **Gate 2**: Get explicit user approval before coding
- **Gate 3**: All automated tests must pass before completion
- **Gate 4**: Manual tests must pass before user story completion

### Testing Priority
1. Automated unit tests (highest priority)
2. Automated integration tests
3. Automated system tests
4. Manual tests (only when automation is not feasible)

## Status Tracking

### User Story Status Values
- **Not Started**: Requirements defined, not yet designed/implemented
- **In Design**: Architecture and design in progress
- **Ready for Approval**: Documentation complete, awaiting approval
- **Approved**: Ready for implementation
- **In Development**: Code being written
- **In Testing**: Automated tests running
- **Bug Fixing**: Issues found, being resolved
- **Manual Testing**: Awaiting user validation
- **Complete**: All tests pass, accepted by user

### Progress Reporting
- Provide status updates at phase transitions
- Highlight blockers or risks
- Report test results clearly
- Update user story statuses promptly

---

**Version**: 1.0  
**Last Updated**: January 23, 2026  
**Status**: Active
