# Sentinel Asset Command

Responsive React dashboard with a Python Flask REST API and MySQL data store.

## Run locally with Railway MySQL

1. Install Python 3.10+ and Node.js 18+.
2. In Railway, open the MySQL service and copy its connection values from **Connect**. Keep the password private. Do not commit `.env`.
3. In the project folder, make your environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

   Fill in `.env` using the Railway connection information:

   ```dotenv
   MYSQL_HOST=your Railway proxy host
   MYSQL_PORT=your Railway proxy port
   MYSQL_USER=root
   MYSQL_PASSWORD=your Railway password
   MYSQL_DATABASE=railway
   PORT=4000
   ```

   Use the public proxy host and port when connecting from your computer. Railway's private hostname/port is for services running inside the Railway network.

4. Install the Python API dependencies and create the tables:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python server\init_db.py
   ```

   The initializer reads `.env`, connects to Railway, and applies `server/schema.sql`. Alternatively, use Railway's `railway connect MySQL` command from a linked Railway project and run the contents of `server/schema.sql` in that session.

5. In a second terminal, install and start the React UI:

   ```powershell
   npm install
   npm run dev
   ```

   Open the Vite URL shown in the terminal (usually `http://localhost:5173`). Start the API in the first terminal with:

   ```powershell
   python server\app.py
   ```

   Check the API/database connection at `http://localhost:4000/api/health`.

## Stack and data design

React and Vite provide the responsive browser UI. Flask exposes REST endpoints in Python, while MySQL/InnoDB stores related bases, users, equipment, purchases, transfers, assignments, expenditures, and audit records. Relational foreign keys help preserve valid base, equipment, and user references. InnoDB transactions ensure a mutation and its audit record commit together. Transfers have separate dispatch and receipt timestamps, so stock appears at the destination after receipt.

The API is in `server/app.py`; the MySQL schema is in `server/schema.sql`. Dashboard and table content in the React UI is currently illustrative sample data and is not yet connected to the API.

## API roles and authentication status

API routes are under `/api`. The starter applies role checks and base scoping: admins can access all bases, base commanders are scoped to their base and can assign assets or record expenditures, and logistics officers can access purchases and transfers. Mutations write an audit record.

For local development, the API reads `X-User-Role`, `X-User-Id`, and `X-Base-Id` headers. These are not secure authentication. Replace them with verified JWT/session identity before deployment, seed valid users/bases/equipment, and enforce stock availability in transactions before operational use. The UI role selector is only a visual preview, not a security boundary.
