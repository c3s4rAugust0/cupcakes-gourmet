import os
from flask import Flask
import models, controllers

def create_app(db_path=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY", "dev-troque-em-producao"),
                      DATABASE=db_path or os.path.join(models.BASE, "cupcakes.db"),
                      ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "admin123"))
    models.init_db(app.config["DATABASE"])
    app.register_blueprint(controllers.bp)
    app.jinja_env.filters["brl"] = lambda v: "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    cores = {"Red Velvet": "#c0392b", "Brigadeiro Gourmet": "#5d3a1a", "Limão Siciliano": "#f1c40f",
             "Ninho com Nutella": "#8e5b3a", "Cenoura com Chocolate": "#e67e22"}
    app.jinja_env.filters["cor"] = lambda nome: cores.get(nome, "#d6336c")
    return app

if __name__ == "__main__":
    create_app().run(debug=True)
