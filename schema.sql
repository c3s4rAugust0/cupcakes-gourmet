-- Projeto físico (SQLite; sintaxe compatível com MySQL/PostgreSQL com pequenos ajustes de tipo)
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS cliente (
  id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
  nome       VARCHAR(100) NOT NULL,
  email      VARCHAR(120) NOT NULL UNIQUE,
  telefone   VARCHAR(20)  NOT NULL,
  criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS produto (
  id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
  nome       VARCHAR(80)  NOT NULL,
  descricao  VARCHAR(255) NOT NULL,
  preco      DECIMAL(8,2) NOT NULL CHECK (preco > 0),
  ativo      INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1))
);
CREATE TABLE IF NOT EXISTS pedido (
  id_pedido       INTEGER PRIMARY KEY AUTOINCREMENT,
  id_cliente      INTEGER NOT NULL REFERENCES cliente(id_cliente),
  endereco_entrega VARCHAR(200) NOT NULL,
  forma_pagamento VARCHAR(10) NOT NULL CHECK (forma_pagamento IN ('PIX','CARTAO','DINHEIRO')),
  status          VARCHAR(12) NOT NULL DEFAULT 'RECEBIDO'
                  CHECK (status IN ('RECEBIDO','PREPARANDO','EM_ENTREGA','ENTREGUE','CANCELADO')),
  total           DECIMAL(10,2) NOT NULL CHECK (total >= 0),
  criado_em       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS item_pedido (
  id_pedido      INTEGER NOT NULL REFERENCES pedido(id_pedido) ON DELETE CASCADE,
  id_produto     INTEGER NOT NULL REFERENCES produto(id_produto),
  quantidade     INTEGER NOT NULL CHECK (quantidade > 0),
  preco_unitario DECIMAL(8,2) NOT NULL,
  PRIMARY KEY (id_pedido, id_produto)
);
CREATE INDEX IF NOT EXISTS idx_pedido_cliente ON pedido(id_cliente);
