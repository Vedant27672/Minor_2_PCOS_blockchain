# Blockchain-based File Storage System

## Overview
A decentralized file storage system that leverages blockchain technology to provide secure, immutable file storage with access control.

This project also includes a synthetic data generation and analysis module using CTGAN to generate synthetic datasets from uploaded files, with detailed statistical and visual comparisons between original and synthetic data. The synthetic datasets and analysis plots are saved in uniquely timestamped subdirectories inside the `app/static/Uploads` folder, organized by username and filename for easy management and retrieval.

## Key Features
- Secure user authentication
- File upload/download with blockchain verification
- View block contents functionality
- Master admin access
- MongoDB backend storage
- Synthetic data generation using CTGAN
- Statistical and visual analysis of synthetic vs original data
- Synthetic datasets and analysis plots saved in timestamped user-specific folders within `app/static/Uploads`

## System Architecture

### Backend Components
- **Flask**: Web application framework
- **MongoDB**: User data storage
- **Blockchain Node**: Transaction processing
- **Bcrypt**: Password hashing
- **LoginManager**: Session management
- **CTGAN**: Synthetic data generation and modeling
- **Pandas, NumPy, Scikit-learn**: Data processing and analysis
- **Matplotlib, Seaborn**: Visualization

### Frontend Components
- Bootstrap-based responsive UI
- Jinja2 templating
- Dynamic content rendering
- Form validation
- Analysis results visualization with carousel and tables

## File Structure

```
project/
├── app/
│   ├── __init__.py           # App initialization
│   ├── views.py              # Route handlers
│   ├── gan.py                # Synthetic data generation and analysis
│   ├── templates/            # HTML templates
│   │   ├── base.html         # Base template
│   │   ├── index.html        # Main interface
│   │   ├── login.html        # Login page
│   │   ├── signup.html       # Registration
│   │   ├── view_block.html   # Block viewer
│   │   └── analysis_results.html  # Synthetic data analysis results
│   └── static/               # Static assets
├── config.py                 # Configuration
├── block_accessor.py         # CLI access tool
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Configure environment variables in `.env`:
```
SECRET_KEY=your_secret_key
MONGO_URI=mongodb://localhost:27017
```
4. Start MongoDB service
5. Run the application:
```bash
python run_app.py
```

## Usage

### User Features
- Register new account
- Login/logout
- Upload files
- Download owned files
- View block details
- Generate synthetic datasets from uploaded files
- View detailed statistical and visual analysis comparing original and synthetic data
- Synthetic datasets and analysis plots are saved in uniquely timestamped subdirectories inside `app/static/Uploads`, organized by username and filename

### Admin Features
- Access all files
- View all transactions
- Master login endpoint

## Security Features
- Password hashing
- Secure session cookies
- CSRF protection
- File ownership verification
- Environment-based configuration

## Blockchain Integration
- Stores file metadata in blockchain
- Each upload creates a transaction
- Immutable record of all uploads
- REST API communication with node

## API Endpoints
- `/submit` - File upload
- `/submit/<filename>` - File download
- `/view_block/<index>/<filename>` - Block viewer
- `/login`, `/logout` - Authentication
- `/signup` - Registration
- `/generate_synthetic` - Generate synthetic dataset and analysis

## Dependencies
See `requirements.txt` for complete list of Python packages.

## License
[MIT License](LICENSE)
