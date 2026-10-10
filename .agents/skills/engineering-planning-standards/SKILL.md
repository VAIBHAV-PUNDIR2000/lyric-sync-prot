---
name: engineering-planning-standards
description: Use when producing engineering implementation plans, system design descriptions (SDD), requirements traceability matrices (RTM), verification and validation plans (V&V), or safety/assurance cases requiring rigorous systems engineering practices.
---

# Reference Documentation Standards for Engineering Planning Agents

The agent MUST use the following engineering standards, document types, and methodologies as reference frameworks when producing implementation plans. Apply their underlying principles without claiming formal compliance or certification.

## 1. Reference Standards and Methodologies

### A. SAE ARP4754B — Guidelines for Development of Civil Aircraft and Systems
**Purpose:** Requirements-driven systems engineering.

Apply these principles:
- Requirements decomposition and allocation.
- System architecture and subsystem definition.
- Requirements validation and verification.
- Dependency management and change-impact analysis.
- Traceability between requirements, design, implementation, and verification.

### B. RTCA DO-178C — Software Considerations in Airborne Systems and Equipment Certification
**Purpose:** Software development assurance.

Apply these principles:
- Traceable software requirements.
- Structured software design and implementation.
- Verification planning and test evidence.
- Reviewable development artifacts.
- Objective evidence for claims about software correctness.

### C. NASA Systems Engineering Handbook
**Document type:** Systems Engineering Handbook.

**Purpose:** Lifecycle engineering, requirements management, architecture, and verification.

Apply these principles:
- Requirements Verification and Validation Matrix.
- Requirements traceability.
- Interface definition and management.
- Technical risk management.
- Verification and validation planning.

### D. Requirements Traceability Matrix (RTM)
**Document type:** Requirements Traceability Matrix.

Every requirement must have a unique identifier and traceable relationships to:
- Its original source.
- Its rationale and constraints.
- The design decision that addresses it.
- The implementation task or component.
- The verification method.
- Its current status and any unresolved gaps.

### E. System Design Description (SDD)
**Document type:** System Design Description / Software Design Description.

Document:
- System boundaries and responsibilities.
- Architecture and component decomposition.
- Interfaces, APIs, and data contracts.
- Data flows and state transitions.
- Failure handling, security, and operational constraints.
- Design rationale and alternatives considered.

### F. Verification and Validation Plan (V&V Plan)
**Document type:** Verification and Validation Plan.

For every requirement and major design decision, specify:
- What must be verified.
- How it will be verified.
- Required test cases or inspection procedures.
- Expected results and acceptance criteria.
- Evidence required to mark the item as verified.

### G. Assurance Case / Safety Case
**Document type:** Structured Assurance Argument.

Use a Claim–Argument–Evidence structure:
- **Claim:** What is asserted about the design.
- **Argument:** Why the available reasoning supports the claim.
- **Evidence:** Source code, requirements, test results, specifications, or authoritative documentation supporting it.

Do not treat unsupported reasoning as evidence.

## 2. Mandatory Agent Rules

1. Never invent requirements, APIs, files, dependencies, test results, or existing system behavior.
2. Separate CONFIRMED FACTS, ASSUMPTIONS, and UNKNOWN INFORMATION.
3. Attach source references to important claims wherever evidence is available.
4. Link each implementation task to one or more explicit requirements.
5. Link each important design decision to its rationale, alternatives, constraints, and evidence.
6. Identify missing requirements, unresolved dependencies, contradictions, and unverified assumptions.
7. Never claim a requirement is satisfied merely because an implementation task has been proposed.
8. Never claim a test has passed unless actual test evidence is available.
9. Request clarification when missing information materially affects correctness or safety.
10. Generate plans that can be independently reviewed and verified.

## 3. Required Output Documents

For each substantial engineering change, generate the following artifacts as appropriate:

1. **Engineering Plan** — objectives, scope, phases, tasks, and dependencies.
2. **Requirements Specification** — functional and non-functional requirements.
3. **Requirements Traceability Matrix (RTM)** — requirement-to-design-to-implementation-to-test mapping.
4. **System Design Description (SDD)** — architecture, components, interfaces, and data flows.
5. **Design Decision Record (ADR)** — decisions, rationale, alternatives, and consequences.
6. **Verification and Validation Plan (V&V Plan)** — tests, inspections, and acceptance criteria.
7. **Risk and Assumption Register** — uncertainties, impacts, mitigations, and owners.
8. **Assurance Summary** — claims, supporting arguments, evidence, and remaining gaps.

## 4. Completion Gate

Before presenting a plan as ready for implementation, check:
- Every known requirement is represented.
- Every major design decision has a defensible rationale.
- Every task has clear scope and acceptance criteria.
- Dependencies and interfaces are explicit.
- Verification methods are defined.
- Unsupported claims and unresolved assumptions are disclosed.
- The traceability matrix contains no unexplained gaps.

Report the remaining gaps explicitly. Never fabricate evidence to make the plan appear complete.

> [!IMPORTANT]
> These are reference frameworks inspired by aviation and systems engineering practices. Using them does not, by itself, establish formal compliance with ARP4754B, DO-178C, or any certification regime.
