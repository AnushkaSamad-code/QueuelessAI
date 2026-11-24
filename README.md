# QueueLess AI

**Intelligent Appointment, Queue & Service Optimization Platform**

QueueLess AI is a full-stack appointment and queue-management system for simulated diagnostic laboratory workflows. Version 1.0 manages three parallel service counters, generates alphanumeric tokens in the `Q101`-`Q999` range, and applies data-structure and search algorithms to distribute customers and move them through laboratory stages.

The system separates customer-facing booking and token status functions from counter operations and administrative oversight. It maintains durable queue state in SQLite and exposes a deterministic FastAPI backend to a responsive React interface.

## Key Capabilities

- Appointment booking with service selection and time-slot validation
- Sequential token assignment from `Q101` through `Q999`
- Custom queue, heap, and routing-data structures
- Breadth-first search, uniform-cost search, and $A^*$ laboratory routing
- Fair counter assignment with waiting-time aging
- Staff-controlled stage transitions across registration, testing, and report stages
- Real-time token status and estimated waiting information
- Administrator dashboards for throughput, utilization, wait time, and queue length
- Persistent queue state and controlled recovery after backend restarts
- Responsive, keyboard-accessible web interface conforming to WCAG AA targets

## System Architecture

The React and Vite frontend communicates with FastAPI over JSON HTTP endpoints. The API layer validates requests, applies role permissions, and coordinates appointment, queue, routing, and analytics services. The data structure layer provides heap, queue, and graph operations used by assignment and routing logic. The AI layer implements admissible $A^*$ routing and alternative search strategies. SQLite is the persistent store for Version 1.0.

```text
React UI -> FastAPI routes -> application services -> custom data structures / AI algorithms
                                         |
                                      SQLite
```

## Technology Stack

| Component | Technology |
|---|---|
| Application language | Python 3.11+ |
| Backend framework | FastAPI |
| Database | SQLite |
| Frontend library | React |
| Frontend build tool | Vite |
| Styling | Tailwind CSS |

## Team Division

| Member | Registration Number | Finalized Role and Division |
|---|---|---|
| Anushka Samad | CSC-25F-083 | AI Lead; Artificial Intelligence (50%), Data Structures (50%); UI/UX decisions and overall project coordination |
| Ubaid Raza | CSC-25F-013 | DS & Search Lead; Artificial Intelligence (50%), Data Structures (50%); backend development |
| Laiba Khan | CSC-25F-024 | Project Content & Sample Data Collection (small task); no coding, backend, or AI algorithm ownership |
| Danyal Hassan | CSC-25F-032 | Testing & Project Support (supporting); screenshots, testing checklist, assigned-feature testing, feedback, and GitHub contribution maintenance |

### Detailed Ownership

- **Anushka Samad:** AI ownership covers problem formulation, state-space representation, initial state/goal state/actions, graph creation, dictionary creation, BFS, graph visualization, and AI documentation. Data Structures ownership covers array implementation, array operations, and array integration with QueueLess. Anushka also makes UI/UX decisions and coordinates the project overall.
- **Ubaid Raza:** AI ownership covers Uniform Cost Search (UCS), $A^*$, path-cost calculation, heuristic function, and search-algorithm integration. Data Structures ownership covers linked lists, priority queues, BSTs, insertion/deletion/search/traversal operations, and data-structures integration. Ubaid also owns backend development.
- **Laiba Khan:** Laiba prepares a list of 5-10 diagnostic laboratory services, collects estimated service durations, and suggests three service-counter names. This is a small content and sample-data task with no coding, backend, or AI-algorithm responsibility.
- **Danyal Hassan:** Danyal collects application screenshots, prepares a basic testing checklist, tests assigned features, reports feedback, and maintains GitHub contributions for completed work.

### Git and Co-Authoring Workflow

Each member records only work actually completed under their own GitHub contribution. When Anushka or Ubaid materially assists with documentation or testing, the contributor creating the commit records that assistance with the required trailer:

```text
Co-authored-by: <assisting contributor name> <verified GitHub noreply address>
```

Commit history must not claim work that was not performed. Co-author trailers are used for actual assistance, including documentation or testing support.

## Directory Map

```text
queueless-ai/
├── README.md
├── backend/
│   ├── ai/
│   ├── api/
│   ├── data/
│   ├── ds/
│   └── tests/
├── frontend/
└── docs/
    ├── 01_Project_Proposal.md
    ├── 02_SRS_Requirements.md
    ├── 03_System_Design.md
    ├── 04_AI_Algorithms.md
    ├── 05_Data_Structures.md
    ├── 06_API_Specification.md
    ├── 07_Database_Schema.md
    ├── 08_Test_Plan.md
    ├── 09_UI_UX_Specification.md
    ├── 10_User_Manual.md
    ├── 11_Deployment_Guide.md
    └── 12_Project_Report.md
```

## Local Setup

### Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- npm

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install fastapi uvicorn aiosqlite
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

The API documentation is available at `http://127.0.0.1:8000/docs`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server normally serves the interface at `http://127.0.0.1:5173`.

### Database

Version 1.0 uses SQLite in `backend/data/queueless.db`. Schema initialization must create tables, constraints, and indexes before the API accepts requests. Backups should copy the database file while the service is stopped.

## Documentation Index

1. [Project Proposal](docs/01_Project_Proposal.md)
2. [Software Requirements Specification](docs/02_SRS_Requirements.md)
3. [System Design](docs/03_System_Design.md)
4. [AI Algorithms](docs/04_AI_Algorithms.md)
5. [Data Structures](docs/05_Data_Structures.md)
6. [API Specification](docs/06_API_Specification.md)
7. [Database Schema](docs/07_Database_Schema.md)
8. [Test Plan](docs/08_Test_Plan.md)
9. [UI/UX Specification](docs/09_UI_UX_Specification.md)
10. [User Manual](docs/10_User_Manual.md)
11. [Deployment Guide](docs/11_Deployment_Guide.md)
12. [Project Report](docs/12_Project_Report.md)
