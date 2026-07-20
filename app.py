import os
import requests
import jwt
from flask import Flask, render_template, redirect, request, url_for, session, flash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-key-pour-les-sessions")

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://auth.maximefodjo.com/auth")
REALM = os.getenv("KEYCLOAK_REALM", "company-realm")
CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "gatekeeper-app")
REDIRECT_URI = "http://localhost:5001/callback"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    authorization_endpoint = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/auth"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email"
    }
    url = requests.Request("GET", authorization_endpoint, params=params).prepare().url
    return redirect(url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Erreur : Aucun code fourni.", 400
        
    token_endpoint = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID
    }
    
    try:
        response = requests.post(token_endpoint, data=data, timeout=10)
        if response.status_code != 200:
            return f"Erreur échange : {response.text}", response.status_code
            
        token_data = response.json()
        id_token = token_data.get("id_token")
        
        # Décoder le JWT sans vérification stricte de signature pour la démo locale
        # (Dans une prod, on validerait la signature avec les clés publiques Jwks de Keycloak)
        decoded_token = jwt.decode(id_token, options={"verify_signature": False})
        
        # On extrait le nom de l utilisateur (Keycloak stocke ça dans "name" ou "preferred_username")
        session["user_name"] = decoded_token.get("name", decoded_token.get("preferred_username", "Utilisateur SecOps"))
        
        return redirect(url_for("dashboard"))
        
    except Exception as e:
        return f"Erreur : {str(e)}", 500

@app.route("/dashboard")
def dashboard():
    # Protection de la route : Si pas de session, retour à l accueil
    if "user_name" not in session:
        return redirect(url_for("index"))
    return render_template("dashboard.html", user_name=session["user_name"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
