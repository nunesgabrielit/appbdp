🚀 BDP Reservation System

Full-stack reservation system built with FastAPI, PostgreSQL, and React, featuring automated backend bootstrap, database validation, and a modern frontend dashboard.


⚙️ Features
Reservation management system (create, validate, and manage bookings)
RESTful API built with FastAPI
PostgreSQL integration with async support
Automated backend bootstrap (environment validation + schema setup)
Frontend dashboard built with React + Vite
API consumption via frontend interface
Unit and integration tests with PostgreSQL
Environment-based configuration via .env
🧠 Tech Stack
Backend
Python
FastAPI
SQLAlchemy / asyncpg
PostgreSQL
Frontend
React
Vite
Testing
Pytest
🏗️ Project Structure
app/                    # Backend source code (FastAPI, business logic, DB access)
database/
  └── 01_init_schema.sql  # Initial PostgreSQL schema
start_bdp.py           # Backend bootstrap script
start.ps1 / start.cmd  # Windows startup scripts
web/                   # Frontend (React + Vite)
tests/                 # Unit and integration tests
⚡ Getting Started
🔧 Requirements
Python 3.11+
PostgreSQL running and accessible
Node.js 18+ (for frontend)
🔐 Environment Setup

Create a .env file in the project root:

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bdp_app

Frontend (optional) — inside /web:

VITE_API_URL=http://127.0.0.1:8000
▶️ Running the Backend
Option 1 — One command (Windows)
.\start.cmd

This script will:

create/use local virtual environment
install dependencies
validate DATABASE_URL
ensure database/schema (if permitted)
start the server at:
http://127.0.0.1:8000

Logs:

bdp_startup.log
Option 2 — Manual
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\python.exe .\start_bdp.py
🌐 Running the Frontend
cd web
npm install
npm run dev -- --host 127.0.0.1

Access:

http://127.0.0.1:5173/

To stop:

Ctrl + C
🧪 Tests
Unit tests
python -m pytest -q
Integration tests (PostgreSQL)

Set test database:

$env:DATABASE_URL_TEST="postgresql+asyncpg://user:password@localhost:5432/bdp_test"

Run:

python -m pytest -q
⚠️ Common Issues
DATABASE_URL not set

Ensure .env exists and is correctly configured.

PostgreSQL connection failure
Check if PostgreSQL is running
Verify host, port, user, and password
Ensure the database exists or user has permission to create it
Port 5173 already in use

Run frontend on another port:

npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
👨‍💻 My Role

In this project, I was responsible for:

Designing and implementing the backend using FastAPI
Integrating PostgreSQL with async support
Creating an automated backend bootstrap process
Developing the frontend dashboard with React
Implementing unit and integration tests
Structuring the project for scalability and maintainability
📌 Notes

This project was built as part of my transition into software engineering, focusing on backend development with Python and modern full-stack architecture.

📫 Contact

Feel free to connect with me on LinkedIn.
