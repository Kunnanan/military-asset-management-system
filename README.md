# Military Asset Management System

A full-stack web application for managing military/logistics assets
across multiple bases with inventory tracking, transfers,
assignments, expenditures, RBAC and audit logging.

## Features

- Dashboard with inventory metrics
- Opening and closing balances
- Net movement tracking
- Purchase management
- Inter-base asset transfers
- Asset assignments
- Expenditure tracking
- Role-Based Access Control
- Audit logging
- Date, base and equipment filters
- REST APIs
- Cloud MySQL database

## Tech Stack

### Frontend
- React
- Vite
- CSS/Tailwind

### Backend
- Python
- FastAPI
- SQLAlchemy
- JWT Authentication

### Database
- MySQL
- Railway Cloud

## Architecture

React
↓
FastAPI REST API
↓
SQLAlchemy
↓
MySQL

## User Roles

### Admin
Full system access.

### Base Commander
Access to the assigned base.

### Logistics Officer
Access to purchases and transfers.

## Project Structure

military-asset-management-system/

├── backend/
├── frontend/
├── database/
├── .env.example
├── .gitignore
└── README.md

## Setup

### Backend

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload
