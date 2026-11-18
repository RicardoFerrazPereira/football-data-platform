
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
from pathlib import Path

# Adiciona a raiz do projeto ao caminho de importação.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.extract import collect_lineups as collector


MATCH_ID = 99999999


class FakeResponse:
    status = 404


class FakePage:
    def __init__(self):
        self.calls = 0

    def goto(self, url, **kwargs):
        self.calls += 1
        return FakeResponse()


def run_test():
    with tempfile.TemporaryDirectory() as temp_dir:

        test_path = Path(temp_dir)

        page = FakePage()

        with patch.object(collector, "SAVE_PATH", test_path):

            # ---------------------------------------------------------
            # CENÁRIO A: não existe JSON anterior.
            # ---------------------------------------------------------

            result = collector.process_match(
                page,
                MATCH_ID,
            )

            expected_file = test_path / f"{MATCH_ID}.json"

            assert result == "not_found", (
                f"Resultado inesperado: {result}"
            )

            assert not expected_file.exists(), (
                "Um JSON foi criado indevidamente após HTTP 404."
            )

            assert page.calls == 1, (
                "HTTP 404 não deveria provocar nova tentativa."
            )

            print("CENÁRIO A: APROVADO")
            print("Resultado: not_found")
            print("Arquivo criado: não")
            print("Requisições realizadas: 1")

            # ---------------------------------------------------------
            # CENÁRIO B: existe um JSON anterior.
            # ---------------------------------------------------------

            previous_data = {
                "confirmed": False,
                "home": {
                    "players": [],
                    "substitutes": [],
                },
                "away": {
                    "players": [],
                    "substitutes": [],
                },
            }

            expected_file.write_text(
                json.dumps(
                    previous_data,
                    ensure_ascii=False,
                    indent=4,
                ),
                encoding="utf-8",
            )

            original_content = expected_file.read_bytes()

            result = collector.process_match(
                page,
                MATCH_ID,
            )

            current_content = expected_file.read_bytes()

            assert result == "not_found", (
                f"Resultado inesperado: {result}"
            )

            assert current_content == original_content, (
                "O JSON anterior foi alterado após HTTP 404."
            )

            assert page.calls == 2, (
                "Cada consulta deveria realizar somente uma requisição."
            )

            print("\nCENÁRIO B: APROVADO")
            print("Resultado: not_found")
            print("Arquivo anterior preservado: sim")
            print("Requisições acumuladas: 2")

    print("\nTODOS OS TESTES FORAM APROVADOS.")


if __name__ == "__main__":
    run_test()
