"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROMPT_NAME = "bug_to_user_story_v2"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / f"{PROMPT_NAME}.yml"
REQUIRED_VARIABLE = "bug_report"


def build_prompt_template(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate separando system e user prompt."""
    return ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    username = os.getenv("USERNAME_LANGSMITH_HUB")
    full_name = f"{username}/{prompt_name}"

    prompt = build_prompt_template(prompt_data)
    techniques = prompt_data.get("techniques_applied", [])

    # As técnicas também viram tags, para facilitar a busca no Hub
    tags = list(dict.fromkeys(
        prompt_data.get("tags", [])
        + [prompt_data.get("version", "")]
        + [f"technique:{t}" for t in techniques]
    ))
    tags = [t for t in tags if t]

    description = prompt_data.get("description", "")
    if techniques:
        description = f"{description} | Técnicas: {', '.join(techniques)}"

    print(f"Fazendo push: {full_name}")
    try:
        url = Client().push_prompt(
            full_name,
            object=prompt,
            is_public=True,
            description=description,
            readme=prompt_data.get("readme"),
            tags=tags,
        )
    except Exception as e:
        print(f"❌ Erro ao fazer push do prompt: {e}")
        if "handle" in str(e).lower() or "403" in str(e):
            print("   Verifique se USERNAME_LANGSMITH_HUB é o seu handle público do Hub.")
        return False

    print(f"   ✓ Tags: {', '.join(tags)}")
    print(f"   ✓ Publicado em: {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    _, errors = validate_prompt_structure(prompt_data)

    user_prompt = (prompt_data.get("user_prompt") or "").strip()
    if not user_prompt:
        errors.append("user_prompt está vazio")
    elif f"{{{REQUIRED_VARIABLE}}}" not in user_prompt:
        errors.append(f"user_prompt deve conter a variável {{{REQUIRED_VARIABLE}}}")

    # Evita repetir o problema da v1 ({bug_report} duplicado no system e no user)
    if f"{{{REQUIRED_VARIABLE}}}" in prompt_data.get("system_prompt", ""):
        errors.append(f"{{{REQUIRED_VARIABLE}}} deve aparecer apenas no user_prompt")

    if not errors:
        try:
            variables = build_prompt_template(prompt_data).input_variables
            if variables != [REQUIRED_VARIABLE]:
                errors.append(
                    f"Variáveis inesperadas no template: {variables} "
                    f"(esperado apenas ['{REQUIRED_VARIABLE}']; escape chaves literais com {{{{ }}}})"
                )
        except Exception as e:
            errors.append(f"Template inválido: {e}")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_PATH))
    if not data or PROMPT_NAME not in data:
        print(f"❌ Prompt '{PROMPT_NAME}' não encontrado em {PROMPT_PATH}")
        return 1

    prompt_data = data[PROMPT_NAME]

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("   ✓ Prompt validado")

    if not push_prompt_to_langsmith(PROMPT_NAME, prompt_data):
        return 1

    print("\n✅ Push concluído com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
