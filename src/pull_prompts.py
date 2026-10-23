"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import os
import sys
from pathlib import Path
import yaml
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()


def _str_presenter(dumper, data):
    """Grava textos multilinha no estilo bloco (|), mais legível para prompts."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, _str_presenter)

SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
PROMPT_KEY = "bug_to_user_story_v1"
OUTPUT_PATH = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v1.yml"


def extract_messages(prompt) -> dict:
    """
    Extrai o template de cada mensagem do ChatPromptTemplate.

    Returns:
        Dicionário com as chaves system_prompt e user_prompt
    """
    extracted = {"system_prompt": "", "user_prompt": ""}

    for message in prompt.messages:
        template = getattr(getattr(message, "prompt", None), "template", "")
        role = message.__class__.__name__.lower()

        if "system" in role:
            extracted["system_prompt"] = template
        elif "human" in role or "user" in role:
            extracted["user_prompt"] = template

    return extracted


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt semente e salva em prompts/bug_to_user_story_v1.yml.

    Returns:
        True se sucesso, False caso contrário
    """
    client = Client()

    print(f"Puxando prompt: {SOURCE_PROMPT}")
    try:
        prompt = client.pull_prompt(SOURCE_PROMPT, dangerously_pull_public_prompt=True)
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt: {e}")
        return False

    messages = extract_messages(prompt)
    if not messages["system_prompt"]:
        print("❌ Nenhuma mensagem de sistema encontrada no prompt")
        return False

    data = {
        PROMPT_KEY: {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": messages["system_prompt"],
            "user_prompt": messages["user_prompt"],
            "version": "v1",
            "source": SOURCE_PROMPT,
            "input_variables": list(prompt.input_variables),
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }

    if not save_yaml(data, str(OUTPUT_PATH)):
        return False

    print(f"   ✓ Variáveis de entrada: {', '.join(prompt.input_variables)}")
    print(f"   ✓ Prompt salvo em: {OUTPUT_PATH}")
    return True


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    if not pull_prompts_from_langsmith():
        return 1

    print("\n✅ Pull concluído com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
