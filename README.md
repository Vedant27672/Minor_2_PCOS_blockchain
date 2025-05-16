# Blockchain-based File Storage System

## Overview

A decentralized file storage system leveraging blockchain technology for secure, immutable file storage and robust access control.

This project features:
- Synthetic data generation and analysis using CTGAN.
- Statistical and visual comparisons between original and synthetic datasets.
- Organized storage of synthetic datasets and analysis plots in timestamped, user-specific subdirectories within `app/static/Uploads`.

---

## Features

### User Features
- Secure registration and login/logout
- File upload and download with blockchain verification
- View block details and contents
- Generate synthetic datasets from uploaded files
- Access detailed statistical and visual analysis comparing original and synthetic data

### Admin Features
- Master admin access and login endpoint
- View all files and transactions

### Security
- Password hashing (Bcrypt)
- Secure session cookies and CSRF protection
- File ownership verification
- Environment-based configuration

---

## System Architecture

### Backend
- **Flask**: Web framework
- **MongoDB**: User and file metadata storage
- **Blockchain Node**: Transaction processing and verification
- **CTGAN**: Synthetic data generation
- **Pandas, NumPy, Scikit-learn**: Data processing and analysis
- **Matplotlib, Seaborn**: Data visualization

### Frontend
- Responsive UI (Bootstrap)
- Jinja2 templating
- Dynamic content rendering
- Form validation
- Carousel and tables for analysis results

---

## File Structure

```
project/
├── app/
│   ├── __init__.py
│   ├── views.py
│   ├── gan.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── view_block.html
│   │   └── analysis_results.html
│   └── static/
├── config.py
├── block_accessor.py
├── requirements.txt
└── README.md
```

---

## Installation

1. **Clone the repository**
2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3. **Configure environment variables** in `.env`:
    ```
    SECRET_KEY=your_secret_key
    MONGO_URI=mongodb://localhost:27017
    ```
4. **Start MongoDB service**
5. **Run the application**
    ```bash
    python run_app.py
    ```

---

## API Endpoints

- `POST /submit` — Upload file
- `GET /submit/<filename>` — Download file
- `GET /view_block/<index>/<filename>` — View block details
- `POST /login`, `POST /logout` — Authentication
- `POST /signup` — Registration
- `POST /generate_synthetic` — Generate synthetic dataset and analysis

---

## Blockchain Integration

- Stores file metadata on blockchain
- Each upload creates a new transaction (immutable record)
- REST API communication with blockchain node

---

## Dependencies

See [`requirements.txt`](requirements.txt) for the full list of Python packages.

---

## License

[MIT License](LICENSE)
