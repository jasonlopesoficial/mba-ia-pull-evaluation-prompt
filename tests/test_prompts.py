"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt():
    data = load_prompts(PROMPT_FILE)
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE.name}"
    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def system_prompt(prompt):
    return prompt.get("system_prompt") or ""


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt, system_prompt):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt
        assert system_prompt.strip(), "system_prompt está vazio"

    def test_prompt_has_role_definition(self, system_prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert re.search(r"Você é (um|uma)\s+\w+", system_prompt), "Persona não definida"
        assert "Product Manager" in system_prompt

    def test_prompt_mentions_format(self, system_prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        text = system_prompt.lower()
        assert "como um" in text and "eu quero" in text and "para que" in text, \
            "Formato 'Como um..., eu quero..., para que...' não exigido"
        assert "critérios de aceitação" in text
        assert all(k in text for k in ("dado que", "quando", "então")), \
            "Formato Gherkin (Dado que/Quando/Então) não exigido"

    def test_prompt_has_few_shot_examples(self, system_prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        examples = re.findall(r"^#+\s*Exemplo \d", system_prompt, flags=re.MULTILINE)
        assert len(examples) >= 2, f"Mínimo de 2 exemplos, encontrados: {len(examples)}"
        assert system_prompt.count("Relato:") >= len(examples), "Exemplo sem entrada"
        assert system_prompt.count("Resposta:") >= len(examples), "Exemplo sem saída"

    def test_prompt_no_todos(self, prompt):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        for field in ("system_prompt", "user_prompt", "description"):
            assert "TODO" not in (prompt.get(field) or ""), f"TODO encontrado em {field}"

    def test_minimum_techniques(self, prompt):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert isinstance(techniques, list)
        assert len(techniques) >= 2, f"Mínimo de 2 técnicas, encontradas: {len(techniques)}"
        assert "few_shot_learning" in techniques, "Few-shot Learning é obrigatório"

    def test_prompt_structure_is_valid(self, prompt):
        """Valida a estrutura com a função auxiliar do projeto."""
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, errors

    def test_bug_report_only_in_user_prompt(self, prompt, system_prompt):
        """A variável {bug_report} deve estar no user prompt, e não duplicada no system."""
        assert "{bug_report}" in prompt.get("user_prompt", "")
        assert "{bug_report}" not in system_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
