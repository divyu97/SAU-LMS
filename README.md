# South Asian University - Library Management System (LMS)

Software Engineering Prototyping Project.

## Project Structure
- `app.py`: Main Flask application entry point and routes.
- `db.sql`: Database schema creation and initial seed data.
- `templates/`: HTML templates for views and dashboards.
- `static/`: CSS styles and static assets.
- `CHANGELOG.md`: Dated history of evolutionary prototypes and additions.
- `requirements.txt`: Python package dependencies.

## Setup Instructions (Local / Second Laptop)
1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd "DBMS Application"
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv env
   # On Windows (PowerShell):
   .\env\Scripts\Activate.ps1
   # On Windows (cmd):
   .\env\Scripts\activate.bat
   # On Linux/macOS:
   source env/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Database Configuration**:
   - Install and start MySQL Server.
   - Run the script `db.sql` in MySQL to initialize `SouthAsianUniversityLMS` database and tables:
     ```bash
     mysql -u root -p < db.sql
     ```
   - Update database credentials in `app.py` if your local MySQL root password differs.

5. **Run the Application**:
   ```bash
   python app.py
   ```
   Open your browser at `http://127.0.0.1:5000`.
