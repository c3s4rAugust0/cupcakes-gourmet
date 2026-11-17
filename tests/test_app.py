
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

