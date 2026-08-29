# Custom Agents Registry

This project uses specialized AI agents to handle different development tasks. Each agent is an expert in their domain with strict boundaries and tool restrictions to ensure clean architecture and separation of concerns.

## Available Agents

### 🏗️ Solution Architect
**File**: `.github/agents/architect.agent.md`  
**Invoke**: `@architect`

**Purpose**: High-level system design, architecture planning, and technical documentation.

**Responsibilities**:
- System architecture design with Mermaid diagrams
- Feature breakdown and implementation planning
- API contract definitions (RESTful/GraphQL)
- Data model design and ERD creation
- Folder structure planning
- RFC generation for technical decisions

**When to Use**:
- Planning new features or systems
- Designing API contracts
- Creating data models
- Structuring project organization
- Making strategic technical decisions
- Generating technical RFCs

**Tools**: read, search, edit, web

**Example Prompts**:
```
@architect Design a real-time notification system with email, SMS, and in-app channels
@architect Create an API contract for multi-tenant booking management
@architect Design the data model for a subscription billing system
@architect Plan the folder structure for a payment processing microservice
```

---

### 🐍 FastAPI Backend Developer
**File**: `.github/agents/fastapi-backend.agent.md`  
**Invoke**: `@fastapi-backend`

**Purpose**: Backend implementation following strict clean architecture principles.

**Responsibilities**:
- Pydantic models (request/response schemas)
- Service layer (ALL business logic)
- Repository layer (database access only)
- Test cases for critical features
- Swagger/OpenAPI documentation

**Architecture Enforcement**:
```
Routers → Services → Repositories → Database
    ↓
Pydantic Models
```

- **Routers**: HTTP handling ONLY (no business logic)
- **Services**: ALL business logic (MUST be separate)
- **Repositories**: Database operations ONLY (no business logic)
- **Models**: Pydantic schemas for validation

**Boundaries**:
- ✅ Works in `backend/` directory only
- ❌ Never touches `frontend/` or `terraform/`
- ❌ Never puts business logic in routers or repositories
- ✅ Always creates service and repository layers

**When to Use**:
- Implementing backend API endpoints
- Creating data models and validation
- Writing business logic
- Building database repositories
- Writing backend tests
- Updating API documentation

**Tools**: read, search, edit, execute

**Example Prompts**:
```
@fastapi-backend Implement a booking cancellation endpoint with refund logic
@fastapi-backend Create a quote management API with status workflow
@fastapi-backend Add filtering and pagination to the /operators endpoint
@fastapi-backend Implement email verification flow with OTP validation
```

---

### 🎨 Vue Frontend Developer
**File**: `.github/agents/vue-frontend.agent.md`  
**Invoke**: `@vue-frontend`

**Purpose**: Frontend implementation using Vue 3, Tailwind CSS, and modern web standards.

**Responsibilities**:
- Vue 3 components (Composition API with `<script setup>`)
- Pinia state management
- Vue Router configuration
- API integration via stores
- Tailwind CSS styling (production-ready, responsive)
- Form handling (native for simple, VeeValidate for complex)

**Tech Stack**:
- Vue 3 Composition API
- Pinia for state management
- Tailwind CSS for styling
- JSDoc for type hints
- Axios for API calls

**Architecture**:
```
Views (pages) → Components → Pinia Stores → API Service
```

**Boundaries**:
- ✅ Works in `frontend/` directory only
- ❌ Never touches `backend/` or `terraform/`
- ❌ No custom CSS unless Tailwind is insufficient
- ❌ No direct API calls in components (use stores)
- ✅ All API calls go through Pinia stores

**When to Use**:
- Building UI components
- Implementing frontend features
- Managing application state
- Creating routes and views
- Integrating with backend APIs
- Styling interfaces

**Tools**: read, search, edit, web

**Example Prompts**:
```
@vue-frontend Create a booking history page with filters and pagination
@vue-frontend Build a responsive user profile editor with avatar upload
@vue-frontend Implement a multi-step quote request form with validation
@vue-frontend Create a notification center with real-time updates
@vue-frontend Build a mobile-friendly tour search interface
```

---

### 🔍 Code Reviewer
**File**: `.github/agents/code-reviewer.agent.md`  
**Invoke**: `@code-reviewer`

**Purpose**: Automated code review with architecture enforcement and security scanning.

**Responsibilities**:
- Architecture boundary enforcement
- Clean architecture validation
- Anti-pattern detection
- Security vulnerability scanning
- Test coverage validation
- Code quality checks

**Review Scope**:
- Auto-scans all modified files (uses `git status`)
- Backend clean architecture compliance
- Frontend architectural patterns
- Security issues (exposed secrets, injection risks)
- Test coverage for critical features

**Review Mode**: **Advisory** (recommends changes, never blocks)

**What It Checks**:

**Backend**:
- ❌ Business logic in routers → ✅ Must be in services
- ❌ Database queries in routers → ✅ Must be in repositories
- ❌ Business logic in repositories → ✅ Must be in services
- ✅ Proper layer separation (routers → services → repositories)

**Frontend**:
- ❌ Direct API calls in components → ✅ Must use Pinia stores
- ❌ Backend imports in frontend → ✅ Must be separate
- ❌ Inline styles/custom CSS → ✅ Use Tailwind utilities
- ✅ Loading/error states for async operations

**Security**:
- 🔒 Exposed secrets (API keys, passwords, tokens)
- 🔒 SQL/NoSQL injection vulnerabilities
- 🔒 XSS risks in templates
- 🔒 Missing authentication checks
- 🔒 Insecure file uploads

**Test Coverage**:
- 🧪 New endpoints have tests
- 🧪 Critical business logic is tested
- 🧪 Edge cases and error paths covered

**When to Use**:
- Reviewing pull requests
- Validating code changes
- Checking architecture compliance
- Scanning for security issues
- Auditing code quality
- Ensuring separation of concerns

**Tools**: read, search, execute

**Example Prompts**:
```
@code-reviewer Review all my changes
@code-reviewer Check the booking feature for architecture compliance
@code-reviewer Scan backend/routers/payments.py for security issues
@code-reviewer Review the authentication implementation
@code-reviewer Validate test coverage for the quote management feature
```

---

## Agent Selection Guide

Use this flowchart to choose the right agent:

```
Need to design or plan something?
    └─> @architect (design, don't implement)

Need to implement backend code?
    └─> @fastapi-backend (Python, FastAPI, clean architecture)

Need to implement frontend code?
    └─> @vue-frontend (Vue 3, Tailwind, Pinia)

Need to review code or check quality?
    └─> @code-reviewer (architecture, security, tests)
```

## Architecture Principles

All agents enforce these principles:

### Clean Architecture (Backend)
```
HTTP Layer (Routers)
    ↓ calls
Business Logic (Services)
    ↓ calls
Data Access (Repositories)
    ↓ queries
Database (MongoDB)
```

**Never mix concerns across layers.**

### Component Architecture (Frontend)
```
Views (pages)
    ↓ compose
Components (reusable UI)
    ↓ use
Pinia Stores (state + API calls)
    ↓ call
API Service (Axios)
```

**Never make API calls directly in components.**

### Boundary Enforcement
- Backend agents never touch frontend code
- Frontend agents never touch backend code
- No agent modifies terraform/infrastructure
- Each agent has minimal tools for their role

## Testing Strategy

- **Backend**: Tests for endpoints, services, repositories (critical features)
- **Frontend**: Tests for critical user flows, complex logic, stores
- **Review**: Code reviewer validates test coverage exists

## Documentation Standards

- **API Docs**: Swagger/OpenAPI with comprehensive examples
- **Architecture**: Mermaid diagrams for system design and ERDs
- **Code**: JSDoc (frontend) and type hints (backend)
- **RFCs**: Markdown documents for major technical decisions

## Security Guidelines

All agents follow security best practices:
- Never commit secrets (use environment variables)
- Validate all user input
- Use parameterized queries (no injection)
- Require authentication on sensitive endpoints
- Implement proper error handling
- Log security events

## Development Workflow

### Automatic Orchestration (Recommended for Full-Stack Features)

Simply describe what you want, and the default agent will automatically orchestrate across specialized agents:

```
"Implement a booking cancellation feature with refund logic, 
including the API endpoint and UI button"
```

**Behind the scenes**:
1. **Design** → `@architect` creates technical design
2. **Backend** → `@fastapi-backend` implements API endpoints
3. **Frontend** → `@vue-frontend` builds UI components
4. **Review** → `@code-reviewer` validates implementation
5. **Iterate** → Repeat as needed

### Manual Agent Invocation (For Targeted Work)

Invoke specific agents when you want precise control:

```bash
# Design first, review before implementing
@architect Design a payment processing system

# Backend only
@fastapi-backend Implement the booking cancellation endpoint

# Frontend only  
@vue-frontend Create a booking cancellation button with confirmation modal

# Review only
@code-reviewer Review my booking cancellation implementation
```

### When to Use Each Approach

| Use Case | Approach | Example |
|----------|----------|---------|
| New full-stack feature | **Automatic** | "Add user profile editing" |
| Complex feature needing design review | **Manual** | `@architect` → review → implement |
| Backend-only change | **Manual** | `@fastapi-backend` |
| Frontend-only change | **Manual** | `@vue-frontend` |
| Architecture review | **Manual** | `@code-reviewer` |
| Bug fix in specific layer | **Manual** | Target specific agent |

## Agent Updates

To modify an agent:
1. Edit the corresponding `.agent.md` file in `.github/agents/`
2. Update this registry if responsibilities change
3. Test the agent with sample prompts
4. Update related documentation

## Additional Resources

### Project Documentation
- [Comprehensive Project Status Report](../docs/project/PROJECT_STATUS_2026_08.md) - Full project overview, metrics, and roadmap
- [Current Phase Status](../docs/project/CURRENT_STATUS.md) - Task-by-task progress tracking
- [Admin Dashboard Guide](../docs/admin/DASHBOARD_GUIDE.md) - Admin feature documentation
- [Setup Instructions](../docs/guides/SETUP.md) - Development environment setup
- [Testing Guide](../docs/guides/TESTING_GUIDE.md) - Testing procedures

### External Documentation
- [Agent Customization Guide](https://code.visualstudio.com/docs/copilot/customization/custom-agents)
- [Clean Architecture Principles](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Vue 3 Style Guide](https://vuejs.org/style-guide/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

---

**Last Updated**: August 7, 2026  
**Agents Version**: 1.0.0  
**Total Agents**: 4  
**Next Review**: Post Phase 2 completion or September 2026
