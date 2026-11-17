"""MODEL: acesso a dados e regras de validação."""
import os, re, sqlite3
from decimal import Decimal

BASE = os.path.dirname(os.path.abspath(__file__))
FORMAS = ("PIX", "CARTAO", "DINHEIRO")
STATUS = ("RECEBIDO", "PREPARANDO", "EM_ENTREGA", "ENTREGUE", "CANCELADO")
SEED = [("Red Velvet", "Massa aveludada com cobertura de cream cheese", "9.50"),
        ("Brigadeiro Gourmet", "Chocolate belga com granulado", "8.50"),
        ("Limão Siciliano", "Massa cítrica com chantilly de limão", "8.00"),
        ("Ninho com Nutella", "Recheio cremoso de leite ninho e Nutella", "10.00"),
        ("Cenoura com Chocolate", "Clássico com ganache meio amargo", "7.50")]

class ValidationError(Exception):
    pass

def conn(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c

def init_db(path):
    c = conn(path)
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        c.executescript(f.read())
    if c.execute("SELECT COUNT(*) FROM produto").fetchone()[0] == 0:
        c.executemany("INSERT INTO produto(nome,descricao,preco) VALUES (?,?,?)", SEED)
    c.commit(); c.close()

def listar_produtos(path):
    c = conn(path)
    r = c.execute("SELECT * FROM produto WHERE ativo=1 ORDER BY nome").fetchall()
    c.close(); return r

def obter_produto(path, pid):
    c = conn(path)
    r = c.execute("SELECT * FROM produto WHERE id_produto=? AND ativo=1", (pid,)).fetchone()
    c.close(); return r

def validar_cliente(nome, email, telefone, endereco, pagamento):
    nome, email, endereco = (nome or "").strip(), (email or "").strip().lower(), (endereco or "").strip()
    tel = re.sub(r"\D", "", telefone or "")
    if len(nome) < 3: raise ValidationError("Informe o nome completo.")
    if not re.fullmatch(r"[^\W\d_]+(?:[ '\-][^\W\d_]+)*", nome):
        raise ValidationError("O nome deve conter apenas letras (sem números ou símbolos).")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email): raise ValidationError("E-mail inválido.")
    if len(tel) not in (10, 11): raise ValidationError("Telefone inválido (use DDD + número).")
    if len(endereco) < 10: raise ValidationError("Informe o endereço completo de entrega.")
    if pagamento not in FORMAS: raise ValidationError("Selecione uma forma de pagamento.")
    return nome, email, tel, endereco

def criar_pedido(path, nome, email, telefone, endereco, pagamento, carrinho):
    """carrinho: {id_produto(str): quantidade(int)}. Retorna id do pedido."""
    nome, email, tel, endereco = validar_cliente(nome, email, telefone, endereco, pagamento)
    if not carrinho: raise ValidationError("O carrinho está vazio.")
    c = conn(path)
    try:
        itens, total = [], Decimal("0")
        for pid, qtd in carrinho.items():
            p = c.execute("SELECT * FROM produto WHERE id_produto=? AND ativo=1", (int(pid),)).fetchone()
            if not p or qtd < 1: raise ValidationError("Item inválido no carrinho.")
            itens.append((p["id_produto"], qtd, p["preco"]))
            total += Decimal(str(p["preco"])) * qtd
        row = c.execute("SELECT id_cliente FROM cliente WHERE email=?", (email,)).fetchone()
        if row:
            cid = row["id_cliente"]
            c.execute("UPDATE cliente SET nome=?, telefone=? WHERE id_cliente=?", (nome, tel, cid))
        else:
            cid = c.execute("INSERT INTO cliente(nome,email,telefone) VALUES (?,?,?)", (nome, email, tel)).lastrowid
        oid = c.execute("INSERT INTO pedido(id_cliente,endereco_entrega,forma_pagamento,total) VALUES (?,?,?,?)",
                        (cid, endereco, pagamento, float(total))).lastrowid
        c.executemany("INSERT INTO item_pedido VALUES (?,?,?,?)", [(oid, *i) for i in itens])
        c.commit(); return oid
    except Exception:
        c.rollback(); raise
    finally:
        c.close()

def consultar_pedido(path, oid, email):
    c = conn(path)
    p = c.execute("""SELECT p.*, c.nome, c.email FROM pedido p JOIN cliente c USING(id_cliente)
                     WHERE p.id_pedido=? AND c.email=?""", (oid, (email or "").strip().lower())).fetchone()
    itens = c.execute("""SELECT i.*, pr.nome FROM item_pedido i JOIN produto pr USING(id_produto)
                         WHERE id_pedido=?""", (oid,)).fetchall() if p else []
    c.close(); return p, itens

def listar_pedidos(path):
    c = conn(path)
    r = c.execute("""SELECT p.*, c.nome FROM pedido p JOIN cliente c USING(id_cliente)
                     ORDER BY p.id_pedido DESC""").fetchall()
    c.close(); return r

def atualizar_status(path, oid, status):
    if status not in STATUS: raise ValidationError("Status inválido.")
    c = conn(path)
    n = c.execute("UPDATE pedido SET status=? WHERE id_pedido=?", (status, oid)).rowcount
    c.commit(); c.close()
    if not n: raise ValidationError("Pedido não encontrado.")
