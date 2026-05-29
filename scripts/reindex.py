#!/usr/bin/env python3
"""
Re-indexado completo del vectorstore de un usuario.

Qué hace:
  1. Limpia la colección Chroma del usuario (o todo el vectorstore con --full-reset)
  2. Elimina el sync_state para forzar fetch de TODOS los archivos desde Drive/ClickUp
  3. Ejecuta una ingesta completa y muestra el resumen

Uso:
    uv run python scripts/reindex.py                          # auto-detecta usuario de google_user.json
    uv run python scripts/reindex.py --user-id jhonny_ts4    # usuario específico
    uv run python scripts/reindex.py --full-reset             # borra TODO el vectorstore primero
    uv run python scripts/reindex.py --list-users             # muestra usuarios con datos indexados
"""

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(email: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", email.lower())


def _detect_user_id() -> str | None:
    user_file = PROJECT_ROOT / "credentials" / "google_user.json"
    if not user_file.exists():
        return None
    try:
        data = json.loads(user_file.read_text())
        email = data.get("email", "")
        return _slug(email) if email else None
    except Exception:
        return None


def _list_users() -> list[str]:
    """Retorna los user_ids que tienen sync_state guardado."""
    cred_dir = PROJECT_ROOT / "credentials"
    return [
        p.stem.replace("sync_state_", "")
        for p in cred_dir.glob("sync_state_*.json")
    ]


def _print_separator():
    print("─" * 52)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Re-indexado completo del vectorstore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--user-id", metavar="ID",
                        help="Slug del usuario (ej: jhonny_ts4_mx)")
    parser.add_argument("--full-reset", action="store_true",
                        help="Elimina TODO el directorio .vectorstore antes de re-indexar")
    parser.add_argument("--list-users", action="store_true",
                        help="Lista los usuarios con datos indexados y sale")
    args = parser.parse_args()

    # ── Listar usuarios ──────────────────────────────────────────────────────
    if args.list_users:
        users = _list_users()
        if users:
            print("\nUsuarios con datos indexados:")
            for u in users:
                print(f"  • {u}")
        else:
            print("\nNo hay usuarios con datos indexados todavía.")
        print()
        return

    # ── Resolver user_id ─────────────────────────────────────────────────────
    user_id = args.user_id or _detect_user_id()
    if not user_id:
        print("\n❌  No se encontró user_id.")
        print("    Opciones:")
        print("    • Conecta Google Drive desde la app (crea credentials/google_user.json)")
        print("    • Usa --user-id <slug>  (ej: --user-id jhonny_ts4_mx)")
        print("    • Usa --list-users para ver los existentes")
        sys.exit(1)

    vectorstore_path = PROJECT_ROOT / ".vectorstore"
    sync_file        = PROJECT_ROOT / "credentials" / f"sync_state_{user_id}.json"

    print()
    _print_separator()
    print(f"  Re-indexado completo")
    _print_separator()
    print(f"  usuario     : {user_id}")
    print(f"  vectorstore : {vectorstore_path}")
    print(f"  sync state  : {sync_file.name}")
    _print_separator()
    print()

    # ── Paso 1: Limpiar vectorstore ──────────────────────────────────────────
    if args.full_reset:
        if vectorstore_path.exists():
            print("🗑   Eliminando vectorstore completo (.vectorstore/)...")
            shutil.rmtree(vectorstore_path)
            print("    ✓ Eliminado\n")
        else:
            print("    ℹ  .vectorstore/ no existe, nada que eliminar\n")
    else:
        print("🗑   Limpiando colección del usuario en Chroma...")
        print("    (usa --full-reset para borrar el vectorstore completo)\n")
        try:
            from core.rag.vectorstore import get_vectorstore
            vs = get_vectorstore(user_id)
            vs.reset_collection()
            print(f"    ✓ Colección limpiada\n")
        except Exception as e:
            print(f"    ⚠  No se pudo limpiar la colección: {e}")
            print(f"    → Continuando de todas formas (los chunks se sobreescribirán)\n")

    # ── Paso 2: Borrar sync state ────────────────────────────────────────────
    if sync_file.exists():
        sync_file.unlink()
        print(f"🗑   Sync state eliminado → el próximo fetch traerá TODOS los archivos\n")

    # ── Paso 3: Verificar credenciales ───────────────────────────────────────
    gdrive_token    = PROJECT_ROOT / "credentials" / "gdrive_token.json"
    has_drive       = gdrive_token.exists()

    clickup_token = None
    try:
        from core.auth.clickup_oauth import get_saved_token
        clickup_token = get_saved_token()
    except Exception:
        pass

    print("📡  Fuentes disponibles:")
    print(f"    {'✓' if has_drive    else '✗'}  Google Drive  {'(token encontrado)' if has_drive    else '(sin token — se omitirá)'}")
    print(f"    {'✓' if clickup_token else '✗'}  ClickUp       {'(token encontrado)' if clickup_token else '(sin token — se omitirá)'}")
    print()

    if not has_drive and not clickup_token:
        print("❌  Sin credenciales disponibles. Conecta al menos una fuente desde la app.")
        sys.exit(1)

    # ── Paso 4: Inicializar servicios ────────────────────────────────────────
    from services.integration_service import IntegrationService
    from services.document_service import DocumentService

    integration = IntegrationService(
        google_access_token=("from_file" if has_drive else None),
        clickup_user_id="login",
        clickup_access_token=clickup_token,
    )
    doc_service = DocumentService(integration, user_id)

    # ── Paso 5: Ingesta completa ─────────────────────────────────────────────
    print("📥  Iniciando ingesta completa...")
    print("    Esto puede tardar varios minutos según el volumen de documentos.\n")

    start = time.time()
    try:
        result = doc_service.ingest()
    except Exception as e:
        print(f"\n❌  Error durante la ingesta: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    elapsed = time.time() - start

    # ── Resumen ──────────────────────────────────────────────────────────────
    print()
    _print_separator()
    if result.errors:
        print(f"  ⚠   Completado con {len(result.errors)} error(es)")
        for err in result.errors:
            print(f"      • {err}")
    else:
        print(f"  ✅  Completado exitosamente")
    _print_separator()
    print(f"  Documentos sincronizados : {result.synced_docs}")
    print(f"  Chunks indexados         : {result.indexed_chunks}")
    print(f"  Tiempo total             : {elapsed:.0f}s")
    _print_separator()
    print()


if __name__ == "__main__":
    main()
