import os
import tempfile
import unittest

import models
from app import create_app


class CupcakesModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "test_cupcakes.db")
        models.init_db(self.db)
        self.produtos = models.listar_produtos(self.db)
        self.pid = self.produtos[0]["id_produto"]

    def tearDown(self):
        self.tmp.cleanup()

    def dados_cliente(self):
        return ("Cesar Augusto", "cesar@example.com", "(11) 99999-8888",
                "Rua das Flores, 123 - Centro", "PIX")

    def criar_pedido_teste(self, carrinho=None):
        # Usa o carrinho padrão somente quando nenhum carrinho foi informado.
        # Um dicionário vazio ({}) deve continuar vazio para testar sua rejeição.
        if carrinho is None:
            carrinho = {str(self.pid): 2}

        return models.criar_pedido(
            self.db,
            *self.dados_cliente(),
            carrinho
        )

    def test_01_banco_inicializa_com_produtos(self):
        self.assertGreaterEqual(len(self.produtos), 1)

    def test_02_listar_produtos_retorna_produtos_ativos(self):
        self.assertTrue(all(p["ativo"] == 1 for p in self.produtos))

    def test_03_obter_produto_existente(self):
        self.assertIsNotNone(models.obter_produto(self.db, self.pid))

    def test_04_obter_produto_inexistente(self):
        self.assertIsNone(models.obter_produto(self.db, 999999))

    def test_05_validar_cliente_normaliza_email_e_telefone(self):
        nome, email, telefone, endereco = models.validar_cliente(
            " Cesar Augusto ", " CESAR@EXAMPLE.COM ", "(11) 99999-8888",
            " Rua das Flores, 123 ", "PIX")
        self.assertEqual(nome, "Cesar Augusto")
        self.assertEqual(email, "cesar@example.com")
        self.assertEqual(telefone, "11999998888")
        self.assertEqual(endereco, "Rua das Flores, 123")

    def test_06_rejeitar_nome_muito_curto(self):
        with self.assertRaises(models.ValidationError):
            models.validar_cliente("Jo", "jo@example.com", "11999998888",
                                   "Rua das Flores, 123", "PIX")

    def test_07_rejeitar_email_invalido(self):
        with self.assertRaises(models.ValidationError):
            models.validar_cliente("Joao Silva", "email-invalido", "11999998888",
                                   "Rua das Flores, 123", "PIX")

    def test_08_rejeitar_telefone_invalido(self):
        with self.assertRaises(models.ValidationError):
            models.validar_cliente("Joao Silva", "joao@example.com", "12345",
                                   "Rua das Flores, 123", "PIX")

    def test_09_rejeitar_endereco_curto(self):
        with self.assertRaises(models.ValidationError):
            models.validar_cliente("Joao Silva", "joao@example.com", "11999998888",
                                   "Rua 1", "PIX")

    def test_10_rejeitar_forma_pagamento_invalida(self):
        with self.assertRaises(models.ValidationError):
            models.validar_cliente("Joao Silva", "joao@example.com", "11999998888",
                                   "Rua das Flores, 123", "BOLETO")

    def test_11_rejeitar_carrinho_vazio(self):
        with self.assertRaises(models.ValidationError):
            self.criar_pedido_teste({})

    def test_12_rejeitar_produto_inexistente_no_carrinho(self):
        with self.assertRaises(models.ValidationError):
            self.criar_pedido_teste({"999999": 1})

    def test_13_criar_pedido_calcula_total(self):
        oid = self.criar_pedido_teste({str(self.pid): 2})
        pedido, itens = models.consultar_pedido(self.db, oid, "cesar@example.com")
        self.assertIsNotNone(pedido)
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["quantidade"], 2)
        self.assertAlmostEqual(float(pedido["total"]), float(itens[0]["preco_unitario"]) * 2, places=2)

    def test_14_consultar_pedido_com_email_correto(self):
        oid = self.criar_pedido_teste()
        pedido, _ = models.consultar_pedido(self.db, oid, "CESAR@example.com")
        self.assertIsNotNone(pedido)

    def test_15_nao_consultar_pedido_com_email_incorreto(self):
        oid = self.criar_pedido_teste()
        pedido, itens = models.consultar_pedido(self.db, oid, "outra@example.com")
        self.assertIsNone(pedido)
        self.assertEqual(itens, [])

    def test_16_atualizar_status_valido(self):
        oid = self.criar_pedido_teste()
        models.atualizar_status(self.db, oid, "PREPARANDO")
        pedido, _ = models.consultar_pedido(self.db, oid, "cesar@example.com")
        self.assertEqual(pedido["status"], "PREPARANDO")

    def test_17_rejeitar_status_invalido(self):
        oid = self.criar_pedido_teste()
        with self.assertRaises(models.ValidationError):
            models.atualizar_status(self.db, oid, "STATUS_ERRADO")

    def test_18_rejeitar_atualizacao_de_pedido_inexistente(self):
        with self.assertRaises(models.ValidationError):
            models.atualizar_status(self.db, 999999, "ENTREGUE")


class CupcakesRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "routes.db")
        self.app = create_app(self.db)
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret", ADMIN_PASSWORD="senha-teste")
        self.client = self.app.test_client()
        self.pid = models.listar_produtos(self.db)[0]["id_produto"]

    def tearDown(self):
        self.tmp.cleanup()

    def adicionar_produto(self, qtd=1):
        return self.client.post(f"/carrinho/adicionar/{self.pid}",
                                data={"qtd": str(qtd)}, follow_redirects=True)

    def test_19_catalogo_abre(self):
        resposta = self.client.get("/")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Nossos cupcakes", resposta.data)

    def test_20_adicionar_produto_ao_carrinho(self):
        resposta = self.adicionar_produto(2)
        self.assertEqual(resposta.status_code, 200)
        carrinho = self.client.get("/carrinho")
        self.assertIn(b"2", carrinho.data)

    def test_21_adicionar_produto_inexistente_retorna_404(self):
        resposta = self.client.post("/carrinho/adicionar/999999")
        self.assertEqual(resposta.status_code, 404)

    def test_22_checkout_com_carrinho_vazio_redireciona(self):
        resposta = self.client.get("/checkout")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/", resposta.location)

    def test_23_finalizar_pedido_pelo_checkout(self):
        self.adicionar_produto(2)
        resposta = self.client.post("/checkout", data={
            "nome": "Cesar Augusto", "email": "cesar@example.com",
            "telefone": "11999998888", "endereco": "Rua das Flores, 123 - Centro",
            "pagamento": "PIX"
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/pedido", resposta.location)
        with self.client.session_transaction() as sess:
            self.assertNotIn("carrinho", sess)

    def test_24_painel_admin_exige_login(self):
        resposta = self.client.get("/admin")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Senha", resposta.data)
        self.assertNotIn(b"Pedidos</h1>", resposta.data)

    def test_25_login_admin_com_senha_incorreta_nao_autentica(self):
        self.client.post("/admin", data={"senha": "errada"})
        resposta = self.client.get("/admin")
        self.assertNotIn(b"Pedidos</h1>", resposta.data)

    def test_26_alterar_status_sem_login_retorna_403(self):
        resposta = self.client.post("/admin/status/1", data={"status": "ENTREGUE"})
        self.assertEqual(resposta.status_code, 403)

    def test_27_login_admin_e_atualizar_status(self):
        self.adicionar_produto(1)
        self.client.post("/checkout", data={
            "nome": "Cesar Augusto", "email": "cesar@example.com",
            "telefone": "11999998888", "endereco": "Rua das Flores, 123 - Centro",
            "pagamento": "PIX"
        })
        self.client.post("/admin", data={"senha": "senha-teste"})
        resposta = self.client.post("/admin/status/1", data={"status": "ENTREGUE"})
        self.assertEqual(resposta.status_code, 302)
        pedido, _ = models.consultar_pedido(self.db, 1, "cesar@example.com")
        self.assertEqual(pedido["status"], "ENTREGUE")


if __name__ == "__main__":
    unittest.main()

