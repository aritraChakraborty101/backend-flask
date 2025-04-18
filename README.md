# Flask Backend for CSE471 Project

This is a Flask-based backend for the CSE471 project. It provides APIs for user management, note sharing, course management, and more.

## Prerequisites

Ensure you have the following installed on your system:
- Python 3.9 or higher
- pip (Python package manager)
- Virtual environment tool (`venv` or `virtualenv`)
- SQLite (pre-installed on most systems)
- Git (optional, for cloning the repository)

## Setup Instructions

Follow these steps to set up and run the project on your local machine.

### 1. Clone the Repository
```bash
git clone <repository-url>
cd CSE471-project/backend-flask
```

### 2. Create a Virtual Environment
#### On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

#### On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root and add the following variables:
```
PROPELAUTH_AUTH_URL=<your-propel-auth-url>
PROPELAUTH_API_KEY=<your-propel-auth-api-key>
GOOGLE_DRIVE_CREDENTIALS_PATH=./gothic-doodad-456615-d8-5e334deccd14.json
CLOUDINARY_CLOUD_NAME=<your-cloudinary-cloud-name>
CLOUDINARY_API_KEY=<your-cloudinary-api-key>
CLOUDINARY_API_SECRET=<your-cloudinary-api-secret>
```

### 5. Initialize the Database
Run the following commands to set up the database:
```bash
flask db upgrade
```

### 6. Run the Application
Start the Flask development server:
```bash
python app.py
```

The server will run on `http://127.0.0.1:3001`.

## Testing the APIs
You can use tools like [Postman](https://www.postman.com/) or [cURL](https://curl.se/) to test the APIs. The base URL for all endpoints is `http://127.0.0.1:3001`.

## Notes
- Ensure your `.env` file is not committed to version control for security reasons.
- If you encounter issues with dependencies, ensure your `pip` is up to date:
  ```bash
  pip install --upgrade pip
  ```

## Troubleshooting
- **Database Errors**: If you encounter database-related errors, delete the `users.db` file and re-run `flask db upgrade`.
- **Missing Dependencies**: Ensure all required Python packages are installed using `pip install -r requirements.txt`.

## License
This project is licensed under the MIT License.
