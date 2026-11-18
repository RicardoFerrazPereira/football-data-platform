
import tempfile
import unittest
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
    """Simula uma resposta HTTP."""

    def __init__(self, status):
        self.status = status


class FakePageHTTP500:
    """Simula uma resposta HTTP 500."""

    def __init__(self):
        self.requests = 0

    def goto(self, *args, **kwargs):
        self.requests += 1
        return FakeResponse(500)


class FakePageTimeout:
    """Simula timeout durante a navegação."""

    def __init__(self):
        self.requests = 0

    def goto(self, *args, **kwargs):
        self.requests += 1
        raise collector.PlaywrightTimeoutError(
            "Timeout simulado para teste"
        )


class TestLineupsTechnicalErrors(unittest.TestCase):

    def run_scenario(self, page, scenario_name):

        with tempfile.TemporaryDirectory() as temp_dir:

            output_dir = Path(temp_dir)

            with (
                patch.object(
                    collector,
                    "SAVE_PATH",
                    output_dir,
                ),
                patch.object(
                    collector.time,
                    "sleep",
                ) as mocked_sleep,
            ):

                result = collector.process_match(
                    page,
                    MATCH_ID,
                )

                output_file = output_dir / f"{MATCH_ID}.json"

                self.assertEqual(result, "failed")
                self.assertFalse(output_file.exists())

                self.assertEqual(
                    page.requests,
                    collector.MAX_RETRIES,
                )

                self.assertEqual(
                    mocked_sleep.call_count,
                    collector.MAX_RETRIES - 1,
                )

                print(f"\n{scenario_name}: APROVADO")
                print(f"Resultado: {result}")
                print(f"Tentativas: {page.requests}")
                print("Arquivo criado: não")
                print(
                    f"Intervalos de espera: "
                    f"{mocked_sleep.call_count}"
                )

    def test_http_500(self):

        page = FakePageHTTP500()

        self.run_scenario(
            page,
            "CENÁRIO C — HTTP 500",
        )

    def test_navigation_timeout(self):

        page = FakePageTimeout()

        self.run_scenario(
            page,
            "CENÁRIO D — TIMEOUT",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
