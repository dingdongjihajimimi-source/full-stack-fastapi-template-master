# Build and Run Commands

## Backend

### Local Development

**Option 1: Using `uv` (Recommended if installed)**
```bash
cd backend
uv run fastapi dev app/main.py
```

**Option 2: Using existing virtual environment**
```bash
# Activate the virtual environment first
source backend/venv/bin/activate
cd backend
fastapi dev app/main.py
```
*Or run directly:*
```bash
./backend/venv/bin/python -m fastapi dev backend/app/main.py
```

### Build/Run with Docker
```bash
docker compose build backend
docker compose up -d backend
```

## Frontend

### Local Development (using `npm`)
```bash
cd frontend
npm install
npm run dev
```

### Build for Production
```bash
cd frontend
npm run build
```

### Build/Run with Docker
```bash
docker compose build frontend
docker compose up -d frontend
```

## Entire Stack
To build and run everything at once:
```bash
docker compose up -d --build
```
To watch for changes (development mode):
```bash
docker compose watch
```
