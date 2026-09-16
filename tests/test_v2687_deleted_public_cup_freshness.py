from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
PAGE=(ROOT/"frontend-next/src/app/cup/[publicKey]/page.tsx").read_text()
VIEW=(ROOT/"frontend-next/src/components/PublicCupView.tsx").read_text()
WORKER=(ROOT/"frontend-next/public/sw.js").read_text()


def test_public_cup_route_never_reuses_deleted_server_snapshot():
    assert 'dynamic="force-dynamic"' in PAGE
    assert "revalidate=0" in PAGE
    assert "unstable_cache" not in PAGE


def test_deleted_cup_is_removed_from_open_clients_and_pwa_cache():
    assert "Cupen är inte längre publicerad." in VIEW
    assert "error instanceof CupNaviApiError&&error.status===404" in VIEW
    assert 'url.pathname.startsWith("/cup/")' in WORKER
