# Health Agents Collective - Implementation Tasks

## High Priority Tasks

### 1. Project Structure Setup
- [ ] Create `src/agents/` directory structure
- [ ] Set up Python package structure with `__init__.py` files
- [ ] Update `pyproject.toml` with required dependencies for A2A and MCP

### 2. Core Agent Implementation
- [ ] **Orchestration Agent**: Central coordinator for workflow management
  - Receive patient information and tasks
  - Delegate sub-tasks to specialized agents
  - Manage workflow sequencing and information flow
  - Handle agent communication via A2A protocol

- [ ] **Diagnosis Agent**: Symptom analysis and preliminary diagnosis
  - Analyze patient symptoms and medical history
  - Formulate questions for additional data when needed
  - Return preliminary diagnosis recommendations

- [ ] **FHIR Agent**: Gateway to FHIR server
  - Implement secure API for patient data operations
  - Handle read operations (medical history, allergies)
  - Handle write operations (diagnoses, test results)
  - Ensure proper FHIR R4 resource formatting

### 3. Communication & Integration
- [ ] **A2A Protocol Implementation**: Agent-to-Agent communication
  - Set up Google's A2A protocol for inter-agent communication
  - Implement message routing and handling
  - Ensure secure and reliable agent interactions

- [ ] **MCP Tools Development**: FHIR R4 API integration
  - Create MCP tools for FHIR server interaction
  - Implement proper authentication and error handling
  - Support all required FHIR resource types

## Medium Priority Tasks

### 4. Specialized Agent Implementation
- [ ] **Insurance Agent**: Insurance verification and prior-authorization
  - Perform prior-authorization checks for tests and procedures
  - Verify patient coverage and benefits
  - Handle insurance API integrations

- [ ] **Order Generating Agent**: Medical order creation
  - Generate orders for procedures, tests, prescriptions
  - Use standardized formats based on diagnosis and insurance approval
  - Ensure proper FHIR resource creation

- [ ] **Referral Agent**: Specialist referral management
  - Identify appropriate specialists based on diagnosis
  - Generate referral requests
  - Track referral status and follow-up

### 5. Data Management & Workflow
- [ ] **Data Provenance & Auditing**: Observation resource implementation
  - Persist all agent-generated data as FHIR Observation resources
  - Include agent identity and content in each observation
  - Maintain references to source data for audit trails

- [ ] **Standard Workflow Implementation**: End-to-end patient processing
  - Implement the complete patient workflow example
  - Test agent coordination and task delegation
  - Validate data flow and persistence

## Low Priority Tasks

### 6. Quality Assurance & Operations
- [ ] **Testing Framework**: Unit and integration tests
  - Set up pytest with appropriate test structure
  - Write unit tests for each agent
  - Create integration tests for workflows

- [ ] **Configuration Management**: Centralized configuration
  - Create configuration system for agent settings
  - Manage environment-specific configurations
  - Handle sensitive data securely

- [ ] **Logging & Monitoring**: Operational visibility
  - Implement comprehensive logging for all agent actions
  - Set up monitoring for system health and performance
  - Create alerting for critical issues

## Implementation Order

1. **Phase 1**: Project structure and core agents (Orchestration, Diagnosis, FHIR)
2. **Phase 2**: Communication protocols (A2A, MCP tools)
3. **Phase 3**: Specialized agents (Insurance, Order, Referral)
4. **Phase 4**: Data provenance and workflow implementation
5. **Phase 5**: Testing, configuration, and monitoring

## Dependencies

- Python 3.13+
- uv for package management
- Google A2A protocol libraries
- MCP (Model Context Protocol) tools
- FHIR R4 server access
- Requests library for HTTP operations

## Notes

- All patient data must be persisted to FHIR server as Observation resources
- FHIR Agent is the sole gateway to the FHIR server
- Each agent must maintain audit trails of actions performed
- System must be flexible for adding new agents and capabilities