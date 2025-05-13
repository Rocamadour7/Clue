# Clue: Subscription Management API

## Overview

Clue is a RESTful API designed to manage user subscriptions. It provides endpoints for user registration, authentication, subscription plan management, and subscription lifecycle management (subscribe, upgrade, cancel).  It's built using Flask, Flask-SQLAlchemy, and JWT for authentication.

## Features

* **User Authentication:**
    * Registration
    * Login
    * Refresh tokens for secure and persistent sessions
* **Subscription Management:**
    * Retrieve subscription plans
    * Subscribe users to plans
    * Upgrade subscriptions (with proration)
    * Cancel subscriptions
* **Database:** Uses SQLAlchemy for database interactions (SQLite by default, configurable to MySQL)
* **Token-Based Authentication:** JWT (JSON Web Tokens) for secure authentication
* **Containerized:** Includes a Dockerfile for easy setup and deployment

## Technical Details

* **Framework:** Flask
* **Database ORM:** Flask-SQLAlchemy
* **Authentication:** JWT
* **Database:** SQLite (default), MySQL (configurable)
* **Containerization:** Docker

## Setup

### Prerequisites

* Docker

### Docker Setup

1.  **Build the Docker image:**

    ```bash
    docker build -t my-flask-app .
    ```

2.  **Run the Docker container:**

    ```bash
    docker run -p 5000:5000 my-flask-app
    ```

## API Endpoints

### User API

* `POST /register`: Register a new user.
    * Request body: `{ "username": "string", "password": "string", "email": "string" }`
* `POST /login`: Authenticate a user and return tokens.
    * Request body: `{ "username": "string", "password": "string" }`
    * Response: `{ "access_token": "string", "refresh_token": "string", "message": "string" }`
* `POST /refresh`: Refresh an access token.
    * Request body: `{ "refresh_token": "string" }`
    * Response: `{ "access_token": "string", "refresh_token": "string" }`

### Subscription API

* `GET /plans`: Get all subscription plans.
* `POST /subscribe/<plan_id>`: Subscribe the user to a plan. Requires a valid access token.
* `POST /upgrade/<subscription_id>/<new_plan_id>`: Upgrade a user's subscription. Requires a valid access token.
* `POST /cancel/<subscription_id>`: Cancel a user's subscription. Requires a valid access token.
* `GET /subscriptions/active`: Get the active subscriptions for the current user. Requires a valid access token.
* `GET /users/<user_id>/subscriptions`: Get all subscriptions for a specific user. Requires a valid access token.

## Authentication

The API uses JWT for authentication. Most routes are protected and require a valid access token in the `Authorization` header:


Authorization: Bearer <access_token>
