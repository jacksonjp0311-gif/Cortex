"""Execute one explicit live Cortex v9.6 empirical commissioning circulation."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from pathlib import Path

from cortex.adapter_provenance import (
    EVIDENCE_LIVE,
    register_adapter_provenance,
    resolve_adapter_provenance,
)
from cortex.adapters.ollama_local import DEFAULT_ENDPOINT, OllamaLocalAdapter
from cortex.empirical_commissioning import commission_empirical_circulation
from cortex.store import Store
from cortex.will import register_will_principal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one host-registered loopback Ollama circulation and print a "
            "sanitized, independently reconstructed v9.6 seal."
        )
    )
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--model-family", required=True)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--max-output-tokens", type=int, default=160)
    parser.add_argument(
        "--task-instruction",
        default=(
            "Return the exact token CORTEX_EMPIRICAL_960 in public_output.text. "
            "Do not request tools or permissions."
        ),
    )
    parser.add_argument("--expected-text", default="CORTEX_EMPIRICAL_960")
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Required acknowledgement that a real local inference call will execute.",
    )
    return parser


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    args = _parser().parse_args()
    if not args.execute_live:
        print(
            json.dumps(
                {
                    "status": "EMPIRICAL_TRIAL_NOT_EXECUTED",
                    "reason": "--execute-live acknowledgement required",
                    "host_mutate_authorized": False,
                    "execution_authorized": False,
                },
                indent=2,
            )
        )
        return 2

    store = Store(args.home.resolve() / "cortex.db")
    try:
        if store.repo(str(args.repo)) is None:
            raise ValueError(f"Unknown repository: {args.repo}")
        adapter = OllamaLocalAdapter(
            model_id=str(args.model),
            model_version=str(args.model_version),
            endpoint=str(args.endpoint),
            timeout_seconds=float(args.timeout_seconds),
            max_output_tokens=int(args.max_output_tokens),
            temperature=0.0,
            keep_alive="0s",
        )
        registration = resolve_adapter_provenance(store, str(args.repo), adapter)
        if str(registration.get("evidence_class") or "") != EVIDENCE_LIVE:
            principal_id = f"v960-commission-{int(time.time())}-{secrets.token_hex(4)}"
            principal_secret = secrets.token_urlsafe(48)
            register_will_principal(
                store,
                str(args.repo),
                principal_id,
                "Cortex v9.6 empirical commissioning operator",
                secret=principal_secret,
            )
            registration = register_adapter_provenance(
                store,
                str(args.repo),
                adapter,
                boundary_kind="local_inference_server",
                principal_id=principal_id,
                principal_secret=principal_secret,
                endpoint_descriptor={
                    "transport": "loopback_http",
                    "service": "ollama",
                    "path": "/api/generate",
                    "model": str(args.model),
                },
                model_family=str(args.model_family),
                capability_class="instruction_text_generation",
            )
            # The plaintext principal secret is intentionally discarded here.
            # The canonical ledgers contain only its cryptographic binding.
            principal_secret = ""
        commissioned = commission_empirical_circulation(
            store,
            str(args.repo),
            adapter=adapter,
            task_instruction=str(args.task_instruction),
            expected_text=str(args.expected_text),
            configuration={
                "temperature": 0.0,
                "max_output_tokens": int(args.max_output_tokens),
                "external_consequence": "public_text_observation_only",
            },
        )
        result = commissioned["result"]
        output = {
            "seal": commissioned["seal"],
            "adapter_registration": {
                "registration_id": registration.get("registration_id"),
                "registration_hash": registration.get("registration_hash"),
                "evidence_class": registration.get("evidence_class"),
                "boundary_kind": registration.get("boundary_kind"),
                "provider_attestation": registration.get("provider_attestation"),
            },
            "public_output": dict(
                (result.get("invocation_result") or {}).get("public_output") or {}
            ),
            "token_usage": dict(
                (result.get("invocation_result") or {}).get("token_usage") or {}
            ),
            "credentials_or_secrets_persisted": False,
            "empirical_transfer_established": False,
            "next_gate": "matched fresh-model A-E transfer trial",
        }
        print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if commissioned["seal"].get("status") == "EMPIRICAL_CIRCULATION_VERIFIED" else 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "EMPIRICAL_CIRCULATION_HELD",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "credentials_or_secrets_persisted": False,
                    "host_mutate_authorized": False,
                    "execution_authorized": False,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
