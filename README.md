# KnowMap: Knowledge Graph Explorer

KnowMap is an intelligent research exploration tool that extracts, visualizes, and analyzes knowledge graphs from academic papers or datasets.
It also supports semantic search, feedback collection, and an admin dashboard — all containerized with Docker.

# Features    

 Dataset Uploads — Upload CSV, JSON, or TXT files

 Semantic Search — Search papers or concepts using Sentence Transformers

 Knowledge Graph Extraction — Uses REBEL & spaCy for entity–relation extraction

 Admin Dashboard — View system statistics, feedback, and user activity

 Feedback System — Collect user feedback and compute average ratings

 Docker Support — Run both backend (Flask) and frontend (Streamlit) easily

 # Project Structure           
 
 knowmap/                                                                                                                                  
├── app.py                                                                                                                                                  
├── app_ui.py                                                                                                                                            
├── Dockerfile.api                                                                                                                            
├── Dockerfile.ui                                                                                                                                     
├── docker-compose.yml                                                             
├── requirements.txt                                                            
├── ui_requirements.txt                                                                                         
├── knowledge_base.db                                                           
├── feedback.csv                                                                                 
└── uploads/                                                                                                      


# Tech Stack                                                                                                    


| Component        | Technology                          |
| ---------------- | ----------------------------------- |
| Backend API      | Flask, SQLite, pandas               |
| Frontend UI      | Streamlit                           |
| NLP Models       | spaCy, REBEL, Sentence Transformers |
| Containerization | Docker, docker-compose              |
| Visualization    | PyVis, NetworkX                     |
| Authentication   | JWT-based                           |




# Setup Instructions       

Option 1 — Run with Docker                                                                           
docker-compose up --build                                                                         

Then open:

Frontend (Streamlit): http://localhost:8501

Backend (Flask API): http://localhost:5010

Option 2 — Run Locally (without Docker)

Create a virtual environment                                                   
python -m venv venv                                                                
venv\Scripts\activate  # (Windows)                                              

Install dependencies                                                                    
pip install -r requirements.txt                                                    
pip install -r ui_requirements.txt                                                      

Run backend                                                                    
python app.py                                                              

Run frontend                                                                      
streamlit run app_ui.py                                                                            

# Admin Login
Default admin credentials:

Username: admin                                     
Password: admin123        

Admins can:                                                
View system stats                                      
Manage users                                        
View and analyze feedback                                               

# Feedback System

Users can:                                                                         
Rate their experience (1–5 stars)                                               
Submit comments or suggestions                                                                            

All feedback is stored in feedback.csv and aggregated in the Admin Dashboard.                                      
                                                                   

# License

This project is licensed under the MIT License
