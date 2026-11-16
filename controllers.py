"""CONTROLLER: recebe requisições, aciona o Model e escolhe a View."""
import os
from flask import Blueprint, current_app as app, render_template, request, redirect, url_for, session, flash, abort
import models

bp = Blueprint("main", __name__)
db = lambda: app.config["DATABASE"]

def _carrinho(): return session.setdefault("carrinho", {})

def _detalhe_carrinho():
    itens, total = [], 0.0
    for pid, qtd in _carrinho().items():
        p = models.obter_produto(db(), int(pid))
        if p:
            sub = p["preco"] * qtd; total += sub
            itens.append({"p": p, "qtd": qtd, "sub": sub})
    return itens, total

@bp.route("/")
def catalogo():
    return render_template("catalogo.html", produtos=models.listar_produtos(db()))

@bp.route("/carrinho")
def carrinho():
    itens, total = _detalhe_carrinho()
    return render_template("carrinho.html", itens=itens, total=total)

@bp.route("/carrinho/adicionar/<int:pid>", methods=["POST"])
def adicionar(pid):
    if not models.obter_produto(db(), pid): abort(404)
    try: qtd = max(1, min(int(request.form.get("qtd", 1)), 50))
    except ValueError: qtd = 1
    c = _carrinho(); c[str(pid)] = min(c.get(str(pid), 0) + qtd, 50)
    session.modified = True
    flash("Cupcake adicionado ao carrinho!", "ok")
    return redirect(url_for("main.catalogo"))

@bp.route("/carrinho/remover/<int:pid>", methods=["POST"])
def remover(pid):
    _carrinho().pop(str(pid), None); session.modified = True
    return redirect(url_for("main.carrinho"))

@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    itens, total = _detalhe_carrinho()
    if not itens:
        flash("Seu carrinho está vazio.", "erro"); return redirect(url_for("main.catalogo"))
    if request.method == "POST":
        f = request.form
        try:
            oid = models.criar_pedido(db(), f.get("nome"), f.get("email"), f.get("telefone"),
                                      f.get("endereco"), f.get("pagamento"), {k: v for k, v in _carrinho().items()})
            session.pop("carrinho", None)
            flash(f"Pedido #{oid} realizado com sucesso!", "ok")
            return redirect(url_for("main.acompanhar", oid=oid, email=f.get("email").strip().lower()))
        except models.ValidationError as e:
            flash(str(e), "erro")
    return render_template("checkout.html", itens=itens, total=total, formas=models.FORMAS, f=request.form)

@bp.route("/pedido", methods=["GET", "POST"])
def acompanhar():
    src = request.values
    oid, email = src.get("oid", type=int), src.get("email")
    pedido = itens = None
    if oid and email:
        pedido, itens = models.consultar_pedido(db(), oid, email)
        if not pedido: flash("Pedido não encontrado. Confira o número e o e-mail.", "erro")
    return render_template("pedido.html", pedido=pedido, itens=itens, oid=oid or "", email=email or "")

@bp.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and "senha" in request.form:
        if request.form["senha"] == app.config["ADMIN_PASSWORD"]: session["admin"] = True
        else: flash("Senha incorreta.", "erro")
    if not session.get("admin"): return render_template("admin_login.html")
    return render_template("admin.html", pedidos=models.listar_pedidos(db()), status=models.STATUS)

@bp.route("/admin/status/<int:oid>", methods=["POST"])
def admin_status(oid):
    if not session.get("admin"): abort(403)
    try: models.atualizar_status(db(), oid, request.form.get("status"))
    except models.ValidationError as e: flash(str(e), "erro")
    return redirect(url_for("main.admin"))

@bp.app_errorhandler(404)
def nao_encontrado(e): return render_template("erro.html", msg="Página não encontrada."), 404
@bp.app_errorhandler(403)
def proibido(e): return render_template("erro.html", msg="Acesso negado."), 403
