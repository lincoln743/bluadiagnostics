"""
Testes unitários das tools (Dia 7).

Cobre:
- consultar_historico_paciente: 7 testes
- verificar_interacoes_medicamentosas: 8 testes
- agendar_teleconsulta: 7 testes
- consultar_wearables: 5 testes
- Registry (dispatch_tool, get_tool_specs_for_agent): 5 testes

Todos determinísticos, sem chamadas a LLM. Suite total < 1s.
"""
from __future__ import annotations

import pytest

from src.tools import (
    ALL_TOOLS,
    TOOLS_POR_AGENTE,
    dispatch_tool,
    get_tool_specs_for_agent,
    listar_tools_disponiveis,
)
from src.tools.agendar_teleconsulta import (
    ESPECIALIDADES_VALIDAS,
    URGENCIAS_VALIDAS,
    agendar_teleconsulta,
)
from src.tools.consultar_historico import consultar_historico_paciente
from src.tools.consultar_wearables import consultar_wearables
from src.tools.verificar_interacoes import verificar_interacoes_medicamentosas


# ============================================================
# consultar_historico_paciente
# ============================================================

class TestConsultarHistorico:
    def test_maria_retorna_perfil_completo(self, maria_id, historico_maria_esperado):
        r = consultar_historico_paciente(maria_id)
        assert r["status"] == "success"
        assert r["paciente_id"] == maria_id
        assert r["data"]["nome_apelido"] == historico_maria_esperado["nome"]
        assert r["data"]["idade"] == historico_maria_esperado["idade"]
        assert r["data"]["sexo"] == historico_maria_esperado["sexo"]

    def test_maria_tem_hipertensao_e_losartana(self, maria_id):
        r = consultar_historico_paciente(maria_id)
        assert any("Hipertensão" in c for c in r["data"]["condicoes_cronicas"])
        meds = [m["nome"] for m in r["data"]["medicamentos_em_uso"]]
        assert "Losartana" in meds

    def test_maria_tem_alergia_dipirona(self, maria_id):
        r = consultar_historico_paciente(maria_id)
        alergias = " ".join(r["data"]["alergias"])
        assert "Dipirona" in alergias

    def test_joao_diabetico_tipo_2(self, joao_id):
        r = consultar_historico_paciente(joao_id)
        assert r["status"] == "success"
        cond = " ".join(r["data"]["condicoes_cronicas"])
        assert "Diabetes" in cond

    def test_ana_gestante_22_semanas(self, ana_id):
        r = consultar_historico_paciente(ana_id)
        assert r["status"] == "success"
        assert r["data"].get("gestacao", {}).get("idade_gestacional_semanas") == 22

    def test_id_inexistente_retorna_not_found(self, paciente_inexistente_id):
        r = consultar_historico_paciente(paciente_inexistente_id)
        assert r["status"] == "not_found"

    def test_id_formato_invalido(self):
        r = consultar_historico_paciente("XYZ-123")
        assert r["status"] == "invalid_id"

    def test_id_vazio(self):
        r = consultar_historico_paciente("")
        assert r["status"] == "invalid_id"

    def test_id_so_numeros_normalizado(self):
        """'04821' deve ser normalizado para 'BNF-04821'."""
        r = consultar_historico_paciente("04821")
        assert r["status"] == "success"
        assert r["paciente_id"] == "BNF-04821"

    def test_filtro_campos_especificos(self, maria_id):
        r = consultar_historico_paciente(maria_id, campos=["alergias"])
        assert r["status"] == "success"
        assert "alergias" in r["data"]
        # Não deve retornar exames_recentes se não pediu
        assert "exames_recentes" not in r["data"]


# ============================================================
# verificar_interacoes_medicamentosas
# ============================================================

class TestVerificarInteracoes:
    def test_losartana_ibuprofeno_detecta_interacao(self):
        r = verificar_interacoes_medicamentosas(["losartana", "ibuprofeno"])
        assert r["status"] == "success"
        assert r["total_interacoes"] >= 1
        assert any("ibuprofeno" in i["par"].lower() for i in r["interacoes_encontradas"])

    def test_atorvastatina_claritromicina_severidade_grave(self):
        r = verificar_interacoes_medicamentosas(["atorvastatina", "claritromicina"])
        assert r["total_interacoes"] == 1
        assert r["interacoes_encontradas"][0]["severidade"] == "grave"

    def test_paracetamol_losartana_sem_interacao(self):
        """Caso negativo: combinação segura."""
        r = verificar_interacoes_medicamentosas(["paracetamol", "losartana"])
        assert r["status"] == "success"
        assert r["total_interacoes"] == 0

    def test_dipirona_em_maria_alergia_detectada(self, maria_id):
        r = verificar_interacoes_medicamentosas(
            ["dipirona"],
            paciente_id=maria_id,
        )
        assert r["status"] == "success"
        assert len(r["contraindicacoes_alergia"]) >= 1
        assert r["contraindicacoes_alergia"][0]["severidade"] == "critica"

    def test_alerta_hitl_quando_nao_aprovado(self):
        r = verificar_interacoes_medicamentosas(
            ["paracetamol"],
            aprovado_por_medico=False,
        )
        assert "alerta_hitl" in r

    def test_sem_alerta_hitl_quando_aprovado(self):
        r = verificar_interacoes_medicamentosas(
            ["paracetamol"],
            aprovado_por_medico=True,
        )
        assert "alerta_hitl" not in r

    def test_lista_vazia_retorna_invalid_input(self):
        r = verificar_interacoes_medicamentosas([])
        assert r["status"] == "invalid_input"

    def test_normaliza_case(self):
        """'LOSARTANA' e 'losartana' devem ser equivalentes."""
        r1 = verificar_interacoes_medicamentosas(["LOSARTANA", "IBUPROFENO"])
        r2 = verificar_interacoes_medicamentosas(["losartana", "ibuprofeno"])
        assert r1["total_interacoes"] == r2["total_interacoes"]

    def test_sertralina_tramadol_sindrome_serotoninergica(self):
        r = verificar_interacoes_medicamentosas(["sertralina", "tramadol"])
        assert r["total_interacoes"] == 1
        mec = r["interacoes_encontradas"][0]["mecanismo"].lower()
        assert "serotonin" in mec


# ============================================================
# agendar_teleconsulta
# ============================================================

class TestAgendarTeleconsulta:
    def test_agendamento_basico_sucesso(self, maria_id):
        r = agendar_teleconsulta(
            paciente_id=maria_id,
            especialidade="cardiologia",
            urgencia="rotina",
            motivo_resumido="Avaliação de controle pressórico",
        )
        assert r["status"] == "success"
        assert r["agendamento_id"].startswith("CP-")
        assert r["especialidade"] == "cardiologia"
        assert "link_video" in r

    def test_agendamento_gera_id_unico(self, maria_id):
        """Dois agendamentos seguidos devem ter IDs diferentes."""
        r1 = agendar_teleconsulta(maria_id, "clinica_medica", "rotina", "teste 1")
        r2 = agendar_teleconsulta(maria_id, "clinica_medica", "rotina", "teste 2")
        assert r1["agendamento_id"] != r2["agendamento_id"]

    def test_especialidade_invalida_rejeitada(self, maria_id):
        r = agendar_teleconsulta(
            paciente_id=maria_id,
            especialidade="neurocirurgia",  # não está nas 8 cobertas
            urgencia="rotina",
            motivo_resumido="teste",
        )
        assert r["status"] == "invalid_input"
        assert "neurocirurgia" in r["mensagem"].lower()

    def test_urgencia_invalida_rejeitada(self, maria_id):
        r = agendar_teleconsulta(
            paciente_id=maria_id,
            especialidade="cardiologia",
            urgencia="agora_mesmo",  # inválida
            motivo_resumido="teste",
        )
        assert r["status"] == "invalid_input"

    def test_motivo_vazio_rejeitado(self, maria_id):
        r = agendar_teleconsulta(maria_id, "cardiologia", "rotina", "")
        assert r["status"] == "invalid_input"

    def test_paciente_vazio_rejeitado(self):
        r = agendar_teleconsulta("", "cardiologia", "rotina", "teste")
        assert r["status"] == "invalid_input"

    def test_instrucoes_preparatorias_incluem_cardiologia(self, maria_id):
        r = agendar_teleconsulta(maria_id, "cardiologia", "rotina", "teste")
        instrucoes = " ".join(r["instrucoes_preparatorias"]).lower()
        # Cardio tem instrução específica sobre aferidor
        assert "pressão" in instrucoes or "afer" in instrucoes

    def test_todas_8_especialidades_funcionam(self, maria_id):
        for esp in ESPECIALIDADES_VALIDAS:
            r = agendar_teleconsulta(maria_id, esp, "rotina", "teste")
            assert r["status"] == "success", f"falhou para {esp}"

    def test_todas_3_urgencias_funcionam(self, maria_id):
        for urg in URGENCIAS_VALIDAS:
            r = agendar_teleconsulta(maria_id, "clinica_medica", urg, "teste")
            assert r["status"] == "success", f"falhou para urgência {urg}"


# ============================================================
# consultar_wearables (BÔNUS)
# ============================================================

class TestConsultarWearables:
    def test_maria_tem_apple_watch(self, maria_id):
        r = consultar_wearables(maria_id)
        assert r["status"] == "success"
        assert "Apple Watch" in r["dispositivo"]

    def test_maria_perfil_hipertensao_correlato(self, maria_id):
        """Wearable da Maria reflete o quadro clínico (sono ruim, HRV baixo)."""
        r = consultar_wearables(maria_id)
        assert r["status"] == "success"
        metricas = r["metricas"]
        assert metricas["sono"]["media_horas_7d"] < 7  # baixo
        assert metricas["hrv_ms"]["media_7d"] < 35  # baixo

    def test_paciente_sem_wearable(self, paciente_inexistente_id):
        r = consultar_wearables(paciente_inexistente_id)
        assert r["status"] == "sem_dispositivo"

    def test_periodo_dias_limitado(self, maria_id):
        """periodo_dias > 30 deve ser clipado para 30."""
        r = consultar_wearables(maria_id, periodo_dias=999)
        assert r["periodo_dias"] == 30

    def test_filtro_metricas(self, maria_id):
        r = consultar_wearables(maria_id, metricas=["sono"])
        assert "sono" in r["metricas"]
        # Não deve incluir frequencia_cardiaca se não pedido
        assert "frequencia_cardiaca" not in r["metricas"]


# ============================================================
# Registry
# ============================================================

class TestRegistry:
    def test_5_tools_registradas(self):
        tools = listar_tools_disponiveis()
        assert len(tools) == 5

    def test_triagem_tem_4_tools_acessiveis(self):
        specs = get_tool_specs_for_agent("triagem")
        assert len(specs) == 4

    def test_prescricao_tem_4_tools_acessiveis(self):
        specs = get_tool_specs_for_agent("prescricao")
        assert len(specs) == 4

    def test_escalada_nao_tem_tools(self):
        specs = get_tool_specs_for_agent("escalada")
        assert len(specs) == 0

    def test_dispatch_tool_desconhecida_retorna_erro(self):
        r = dispatch_tool("ferramenta_que_nao_existe", {})
        assert r["status"] == "error"
        assert "desconhecida" in r["mensagem"].lower()

    def test_dispatch_aceita_args_como_string_json(self, maria_id):
        """Groq retorna args como string JSON — dispatch deve parsear."""
        import json
        args_str = json.dumps({"paciente_id": maria_id})
        r = dispatch_tool("consultar_historico_paciente", args_str)
        assert r["status"] == "success"

    def test_dispatch_args_json_invalido(self):
        r = dispatch_tool("consultar_historico_paciente", "not valid json{")
        assert r["status"] == "error"

    def test_specs_formato_anthropic(self):
        """Specs devem ter 'name', 'description', 'input_schema'."""
        for spec, _func in ALL_TOOLS.values():
            assert "name" in spec
            assert "description" in spec
            assert "input_schema" in spec
            # Schema deve ter type=object
            assert spec["input_schema"]["type"] == "object"
