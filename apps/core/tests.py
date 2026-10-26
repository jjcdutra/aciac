"""Testes de fumaça: cadastro, login, painel, consulta, solicitação e PIX."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.consultas.validators import is_valid_cpf
from apps.pagamentos.pix import _crc16_emv, gerar_payload_pix
from apps.solicitacoes.models import Servico, Solicitacao

FAKE_CNPJ = {
    "tipo": "cnpj",
    "cnpj": "19131243000197",
    "razao_social": "OPEN KNOWLEDGE BRASIL",
    "situacao": "ATIVA",
}


class FluxoCompletoTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Usuário de apoio para o fluxo de solicitação (aprovado)
        User = get_user_model()
        empresa2 = User.objects.create_user(
            username="empresa2",
            email="e2@teste.com",
            password="S3gur@Senha123",
            role="associado",
        )
        from apps.associados.models import Associado

        Associado.objects.create(
            user=empresa2,
            tipo_documento="CNPJ",
            documento="33444555000166",
            razao_social="Empresa Dois LTDA",
            status=Associado.Status.ATIVO,
        )

    def _criar_pendente(self, username="pendente1"):
        User = get_user_model()
        from apps.associados.models import Associado

        user = User.objects.create_user(
            username=username,
            email=f"{username}@teste.com",
            password="S3gur@Senha123",
            role="associado",
        )
        Associado.objects.create(
            user=user,
            tipo_documento="CPF",
            documento="52998224725",
            razao_social=f"{username} Silva",
            status=Associado.Status.PENDENTE,
        )
        return user

    def test_home_200(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_cadastro_e_login(self):
        resp = self.client.post(
            reverse("associados:cadastro"),
            {
                "username": "empresa1",
                "email": "empresa1@teste.com",
                "documento": "11.222.333/0001-81",
                "razao_social": "Empresa Teste LTDA",
                "telefone": "(11) 99999-0000",
                "password1": "S3gur@Senha123",
                "password2": "S3gur@Senha123",
                "aceite_termos": "on",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

        # Login
        ok = self.client.login(username="empresa1", password="S3gur@Senha123")
        self.assertTrue(ok)

        # Painel acessível
        resp = self.client.get(reverse("associados:painel"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ASS00000")

        # Perfil criado com status pendente
        from apps.associados.models import Associado

        perfil = Associado.objects.get(user__username="empresa1")
        self.assertEqual(perfil.status, "pendente")
        self.assertEqual(perfil.tipo_documento, "CNPJ")

    def test_painel_exige_login(self):
        resp = self.client.get(reverse("associados:painel"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("associados:login"), resp.url)

    def test_consulta_exige_login(self):
        resp = self.client.post(
            reverse("consultas:consulta_ajax"),
            {"documento": "19131243000197"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("associados:login"), resp.url)

        resp = self.client.get(reverse("consultas:consulta"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("associados:login"), resp.url)

    def test_consulta_exige_aprovacao(self):
        self._criar_pendente()
        self.client.login(username="pendente1", password="S3gur@Senha123")

        resp = self.client.get(reverse("consultas:consulta"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("associados:painel"), resp.url)

        resp = self.client.post(
            reverse("consultas:consulta_ajax"),
            {"documento": "19131243000197"},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(resp.json()["ok"])

    def test_solicitacao_exige_aprovacao(self):
        from apps.solicitacoes.models import Solicitacao

        self._criar_pendente()
        self.client.login(username="pendente1", password="S3gur@Senha123")
        resp = self.client.get(reverse("solicitacoes:servicos"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("associados:painel"), resp.url)
        self.assertEqual(Solicitacao.objects.count(), 0)

    @patch("apps.consultas.views.consultar_cnpj", side_effect=lambda cnpj: dict(FAKE_CNPJ))
    def test_consulta_ajax(self, _mock):
        self.client.login(username="empresa2", password="S3gur@Senha123")
        resp = self.client.post(
            reverse("consultas:consulta_ajax"),
            {"documento": "19131243000197"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["tipo"], "cnpj")

    @patch("apps.consultas.views.consultar_cnpj", side_effect=lambda cnpj: dict(FAKE_CNPJ))
    def test_consulta_rate_limit(self, _mock):
        from django.core.cache import cache

        cache.clear()
        self.client.login(username="empresa2", password="S3gur@Senha123")
        with override_settings(CONSULTA={"RATE_LIMIT": 3, "CACHE_HORAS": 24,
                                         "SERPRO_API_TOKEN": "", "SERPRO_API_URL": ""}):
            codes = [
                self.client.post(
                    reverse("consultas:consulta_ajax"),
                    {"documento": "00000000000191"},
                ).status_code
                for _ in range(5)
            ]
        # Cache evita nova chamada à API; rate-limit bloqueia após o limite
        self.assertIn(429, codes)

    @override_settings(
        ASSOCIACAO={
            "NOME": "ASSOCIACAO COMERCIAL TESTE",
            "CIDADE": "SAO PAULO",
            "UF": "SP",
            "TELEFONE": "(11) 3000-0000",
            "EMAIL": "contato@teste.com",
            "PIX_CHAVE": "a1b2c3d4-e5f6-7890-abcd-1234567890ef",
        }
    )
    def test_solicitacao_com_pix(self):
        self.client.login(username="empresa2", password="S3gur@Senha123")
        Servico.seed_defaults()
        servico = Servico.objects.get(slug="certificado-digital")

        resp = self.client.post(
            reverse("solicitacoes:servicos"),
            {"servico": servico.pk, "observacoes": "Teste smoke"},
        )
        self.assertEqual(resp.status_code, 302)

        solicitacao = Solicitacao.objects.first()
        self.assertIsNotNone(solicitacao)
        self.assertTrue(solicitacao.protocolo.startswith("SOL"))
        self.assertEqual(solicitacao.status, Solicitacao.Status.AGUARDANDO_PAGAMENTO)

        # Página de pagamento com payload PIX
        resp = self.client.get(
            reverse("solicitacoes:pagar", args=[solicitacao.protocolo])
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.context["pagamento"].pix_payload
        self.assertTrue(payload.startswith("000201"))
        self.assertIn("br.gov.bcb.pix", payload)
        self.assertIn(f"{float(solicitacao.valor):.2f}", payload)

        # Confirmar pagamento → em análise
        resp = self.client.post(
            reverse("solicitacoes:pagar", args=[solicitacao.protocolo]),
            {"confirmar": "1"},
            follow=True,
        )
        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, Solicitacao.Status.EM_ANALISE)


class PixPayloadTests(TestCase):
    def test_crc16_referencia_bcb(self):
        # Valor de checagem clássico do CRC-16/CCITT-FALSE: "123456789" → 0x29B1
        self.assertEqual(_crc16_emv("123456789"), "29B1")

    def test_payload_com_chave_e_valor(self):
        payload = gerar_payload_pix(
            chave="a1b2c3d4-e5f6-7890-abcd-1234567890ef",
            nome_merchant="ASSOCIACAO COMERCIAL",
            cidade_merchant="SAO PAULO",
            valor=120.00,
            txid="SOL000001",
        )
        self.assertTrue(payload.startswith("000201"))
        self.assertIn("0014br.gov.bcb.pix", payload)
        self.assertIn("5406120.00", payload)
        # CRC final deve bater
        corpo, crc = payload[:-4], payload[-4:]
        self.assertEqual(crc, _crc16_emv(corpo))
        # Estrutura TLV: todos os tamanhos do nível raiz têm exatamente 2 dígitos
        self._validar_tlv_raiz(payload)

    def _validar_tlv_raiz(self, payload: str):
        """Varre o payload no nível raiz e confere Tag(2)+Len(2)."""
        i = 0
        vistos = set()
        while i < len(payload):
            tag = payload[i : i + 2]
            tam = payload[i + 2 : i + 4]
            self.assertTrue(tam.isdigit(), f"Tag {tag}: tamanho inválido '{tam}'")
            n = int(tam)
            valor = payload[i + 4 : i + 4 + n]
            self.assertEqual(len(valor), n, f"Tag {tag}: valor truncado")
            vistos.add(tag)
            i += 4 + n
        for esperado in ("00", "01", "26", "52", "53", "54", "58", "59", "60", "62", "63"):
            self.assertIn(esperado, vistos)

    def test_descricao_longa_nao_quebra_tlv(self):
        """Descrição enorme deve ser truncada para caber no campo 26 (≤99)."""
        payload = gerar_payload_pix(
            chave="a1b2c3d4-e5f6-7890-abcd-1234567890ef",
            nome_merchant="ASSOCIACAO",
            cidade_merchant="SAO PAULO",
            valor=350.00,
            txid="SOL000001",
            descricao="X" * 300,
        )
        self._validar_tlv_raiz(payload)
        # Campo 26 com UUID nunca pode passar de 99 chars
        idx = payload.index("26")
        self.assertLessEqual(int(payload[idx + 2 : idx + 4]), 99)

    def test_payload_sem_chave_levanta_erro(self):
        with self.assertRaises(ValueError):
            gerar_payload_pix(
                chave="",
                nome_merchant="X",
                cidade_merchant="SP",
                valor=10,
            )

    def test_sem_acentos_e_limites(self):
        payload = gerar_payload_pix(
            chave="11144477735",
            nome_merchant="Associação São João Ltda",
            cidade_merchant="São Paulo",
            valor=10.5,
        )
        self.assertNotIn("Ç", payload)
        self.assertIn("ASSOCIACAO SAO", payload)


class ValidadorTests(TestCase):
    def test_cpfs_e_cnpjs(self):
        self.assertTrue(is_valid_cpf("52998224725"))
        self.assertFalse(is_valid_cpf("11111111111"))


class AdminAprovacaoTests(TestCase):
    """Painel do admin: solicitações do 'Associar-se' visíveis para aprovar/negar."""

    def setUp(self):
        from apps.associados.models import Associado

        User = get_user_model()
        User.objects.create_superuser("admin_test", "admin@teste.com", "S3gur@Senha123")
        user = User.objects.create_user(
            "novaempresa", "n@t.com", "S3gur@Senha123", role="associado"
        )
        self.perfil = Associado.objects.create(
            user=user,
            tipo_documento="CNPJ",
            documento="44555666000177",
            razao_social="Nova Empresa LTDA",
        )

    def test_admin_index_destaca_solicitacoes(self):
        self.client.force_login(get_user_model().objects.get(username="admin_test"))
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Solicitações de associação")
        self.assertContains(resp, "Pendentes de aprovação")

    def test_acoes_aprovar_e_negar(self):
        self.client.force_login(get_user_model().objects.get(username="admin_test"))
        resp = self.client.get("/admin/associados/associado/")
        self.assertContains(resp, "Aprovar associados selecionados")
        self.assertContains(resp, "Negar associados selecionados")

        # Listagem filtrada por pendentes (link do módulo do admin)
        resp = self.client.get("/admin/associados/associado/?status__exact=pendente")
        self.assertContains(resp, "Nova Empresa LTDA")

        # Aprovar
        resp = self.client.post(
            "/admin/associados/associado/",
            {"action": "aprovar_associados", "_selected_action": [str(self.perfil.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.status, "ativo")
        self.assertIsNotNone(self.perfil.data_aprovacao)

        # Negar
        resp = self.client.post(
            "/admin/associados/associado/",
            {"action": "negar_associados", "_selected_action": [str(self.perfil.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.status, "negado")
